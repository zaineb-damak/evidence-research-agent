"""URL canonicalization for source dedup.

Search APIs return the same page under different links — a tracking parameter
appended, a fragment, a differently-cased host. Content hashing can't catch
these because each query returns a different snippet of the page, so the
researcher also compares canonical URLs.

Deliberately conservative: only parameters that never change the page are
dropped. An unknown parameter is assumed meaningful (`?v=` on YouTube, `?page=`).
"""

from __future__ import annotations

from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

TRACKING_PARAMETER_PREFIXES = ("utm_",)
TRACKING_PARAMETERS = frozenset(
    {"fbclid", "gclid", "dclid", "msclkid", "mc_cid", "mc_eid", "xstg", "si", "ref_src"}
)
NO_FRAGMENT = ""


def _is_tracking_parameter(name: str) -> bool:
    lowered = name.lower()
    return lowered in TRACKING_PARAMETERS or lowered.startswith(TRACKING_PARAMETER_PREFIXES)


def canonical_url(url: str) -> str:
    parts = urlsplit(url.strip())
    kept_parameters = [
        (name, value)
        for name, value in parse_qsl(parts.query, keep_blank_values=True)
        if not _is_tracking_parameter(name)
    ]
    return urlunsplit(
        (
            parts.scheme.lower(),
            parts.netloc.lower(),
            parts.path,
            urlencode(kept_parameters),
            NO_FRAGMENT,
        )
    )
