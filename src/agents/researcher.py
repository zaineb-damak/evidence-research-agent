"""Researcher: run each sub-question through the configured connectors, fetch
and clean content, chunk into passages, and register everything for retrieval.

Respects the per-tier source cap. Content acquisition is deduped by content
hash so re-runs are idempotent.
"""

from __future__ import annotations

from src.config import get_settings
from src.models.schemas import (
    Document,
    Passage,
    ResearchDepth,
    ResearchTask,
    Source,
)
from src.security.sanitize import sanitize_document_text
from src.sources.base import SourceConnector
from src.sources.fetcher import chunk_text, fetch_clean
from src.sources.mapping import source_from_raw_result
from src.text.hashing import content_hash


class ResearchOutput:
    def __init__(self) -> None:
        self.sources: list[Source] = []
        self.documents: list[Document] = []
        self.passages: list[Passage] = []


def run_research(
    tasks: list[ResearchTask],
    connectors: dict[object, SourceConnector],
    depth: ResearchDepth,
    per_query: int = 5,
) -> ResearchOutput:
    settings = get_settings()
    cap = settings.cap_for(depth)
    out = ResearchOutput()
    seen_hashes: set[str] = set()
    seen_urls: set[str] = set()

    for task in tasks:
        for connector in connectors.values():
            if len(out.sources) >= cap.max_sources:
                break
            try:
                raw_results = connector.search(task.sub_question, per_query)
            except Exception:
                continue

            for raw_result in raw_results:
                if len(out.sources) >= cap.max_sources:
                    break
                if not raw_result.url or raw_result.url in seen_urls:
                    continue

                # Connector-provided content is untrusted too, so sanitize it the
                # same way fetch_clean sanitizes directly-fetched pages.
                if raw_result.content:
                    document_text = sanitize_document_text(raw_result.content)
                else:
                    document_text = fetch_clean(raw_result.url, settings.crawler_user_agent)
                if not document_text:
                    continue

                document_content_hash = content_hash(document_text)
                if document_content_hash in seen_hashes:
                    continue
                seen_hashes.add(document_content_hash)
                seen_urls.add(raw_result.url)

                source = source_from_raw_result(raw_result)
                document = Document(
                    source_id=source.id,
                    text=document_text,
                    content_hash=document_content_hash,
                )
                out.sources.append(source)
                out.documents.append(document)
                task.source_ids.append(source.id)

                for ordinal, chunk in enumerate(chunk_text(document_text)):
                    out.passages.append(
                        Passage(
                            document_id=document.id,
                            source_id=source.id,
                            text=chunk,
                            ordinal=ordinal,
                        )
                    )
    return out
