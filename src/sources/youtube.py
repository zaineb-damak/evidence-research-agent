"""YouTube transcript connector.

Discovery of relevant videos is delegated to the web connector (Tavily) in v1;
this connector turns a YouTube URL into a transcript passage. `search` accepts
pre-discovered video URLs via the query when prefixed with a known id, and
otherwise returns nothing (kept minimal until a search backend is wired).
"""

from __future__ import annotations

import re

from youtube_transcript_api import YouTubeTranscriptApi

from src.models.schemas import SourceType
from src.sources.base import RawResult, SourceConnector

YOUTUBE_DOMAIN = "youtube.com"
TRANSCRIPT_JOIN_SEPARATOR = " "
VIDEO_ID_PATTERN = re.compile(r"(?:v=|youtu\.be/|/shorts/)([\w-]{11})")


def extract_video_id(url: str) -> str | None:
    match = VIDEO_ID_PATTERN.search(url)
    return match.group(1) if match else None


class YouTubeConnector(SourceConnector):
    source_type = SourceType.YOUTUBE

    def transcript(self, url: str) -> RawResult | None:
        video_id = extract_video_id(url)
        if not video_id:
            return None
        try:
            transcript_parts = YouTubeTranscriptApi.get_transcript(video_id)
        except Exception:
            return None
        transcript_text = TRANSCRIPT_JOIN_SEPARATOR.join(
            part["text"] for part in transcript_parts
        )
        return RawResult(
            url=url,
            title=f"YouTube transcript {video_id}",
            content=transcript_text,
            source_type=SourceType.YOUTUBE,
            domain=YOUTUBE_DOMAIN,
        )

    def search(self, query: str, limit: int) -> list[RawResult]:
        # Video discovery is handled by the web connector in v1.
        return []
