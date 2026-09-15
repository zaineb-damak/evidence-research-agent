"""Citations are attached to claims, not paragraphs (§11).

Builds a stable citation index over the sources actually cited by verified
claims, and renders per-claim citation markers plus a Sources section.
"""

from __future__ import annotations

from src.models.schemas import Claim, Evidence, Source


class CitationIndex:
    def __init__(self) -> None:
        self._order: list[str] = []  # source_ids in citation order
        self._by_source: dict[str, int] = {}

    def cite(self, source_id: str) -> int:
        if source_id not in self._by_source:
            self._order.append(source_id)
            self._by_source[source_id] = len(self._order)
        return self._by_source[source_id]

    def markers_for_claim(
        self, claim: Claim, evidence: list[Evidence]
    ) -> list[int]:
        ev_by_id = {e.id: e for e in evidence}
        numbers = sorted(
            {
                self.cite(ev_by_id[eid].source_id)
                for eid in claim.evidence_ids
                if eid in ev_by_id
            }
        )
        return numbers

    def render_sources(self, sources: list[Source]) -> str:
        by_id = {s.id: s for s in sources}
        lines = []
        for idx, source_id in enumerate(self._order, start=1):
            s = by_id.get(source_id)
            if not s:
                continue
            title = s.title or s.url
            meta = f" ({s.source_type})" if s.source_type else ""
            lines.append(f"[{idx}] {title}{meta} — {s.url}")
        return "\n".join(lines)
