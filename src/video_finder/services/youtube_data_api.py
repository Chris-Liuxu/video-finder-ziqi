from __future__ import annotations

import httpx

from video_finder.models import YouTubeCandidate


def _best_thumbnail(thumbnails: dict) -> str | None:
    for key in ("maxres", "standard", "high", "medium", "default"):
        item = thumbnails.get(key)
        if item and item.get("url"):
            return item["url"]
    return None


class YouTubeDataApiClient:
    def __init__(self, api_key: str | None) -> None:
        self.api_key = api_key

    def enrich_candidates(self, candidates: list[YouTubeCandidate]) -> list[YouTubeCandidate]:
        if not self.api_key or not candidates:
            return candidates

        by_id = {candidate.video_id: candidate for candidate in candidates}
        response = httpx.get(
            "https://www.googleapis.com/youtube/v3/videos",
            params={
                "part": "snippet,contentDetails,statistics",
                "id": ",".join(by_id),
                "key": self.api_key,
            },
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()

        for item in payload.get("items", []):
            candidate = by_id.get(item.get("id"))
            if not candidate:
                continue
            snippet = item.get("snippet") or {}
            content_details = item.get("contentDetails") or {}
            statistics = item.get("statistics") or {}

            candidate.title = snippet.get("title") or candidate.title
            candidate.channel = snippet.get("channelTitle") or candidate.channel
            candidate.description = snippet.get("description") or candidate.description
            candidate.thumbnail = (
                _best_thumbnail(snippet.get("thumbnails") or {}) or candidate.thumbnail
            )
            candidate.published_at = snippet.get("publishedAt") or ""
            candidate.duration = content_details.get("duration") or ""
            candidate.view_count = _int_or_none(statistics.get("viewCount"))
            candidate.like_count = _int_or_none(statistics.get("likeCount"))
            candidate.comment_count = _int_or_none(statistics.get("commentCount"))
            candidate.data_api_loaded = True
            candidate.raw["youtube_data_api"] = item

        return candidates


def _int_or_none(value: object) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
