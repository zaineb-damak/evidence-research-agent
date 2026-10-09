"""Canonical URLs: the same page reached through different links is one source."""

from __future__ import annotations

import pytest

from src.text.urls import canonical_url


@pytest.mark.parametrize(
    "variant, original",
    [
        (
            "https://www.youtube.com/watch?v=6StwSGgt2DI&xstg=CAMSBhUDzO3xHw%3D%3D",
            "https://www.youtube.com/watch?v=6StwSGgt2DI",
        ),
        ("https://Example.com/post?utm_source=x&utm_medium=y", "https://example.com/post"),
        ("https://example.com/post#section-2", "https://example.com/post"),
        ("https://example.com/post?fbclid=abc&page=2", "https://example.com/post?page=2"),
    ],
)
def test_tracking_variants_collapse_to_one_url(variant, original):
    assert canonical_url(variant) == canonical_url(original)


def test_meaningful_query_parameters_are_kept():
    assert canonical_url("https://www.youtube.com/watch?v=A") != canonical_url(
        "https://www.youtube.com/watch?v=B"
    )


def test_path_case_is_preserved():
    assert canonical_url("https://example.com/Docs/API") == "https://example.com/Docs/API"
