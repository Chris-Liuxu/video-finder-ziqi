from __future__ import annotations

from urllib.parse import parse_qs, urlparse

from video_finder.models import LensResult, YouTubeCandidate


def extract_youtube_video_id(url: str) -> str | None:
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    if "youtu.be" in host:
        return parsed.path.strip("/") or None
    if "youtube.com" in host:
        if parsed.path == "/watch":
            return parse_qs(parsed.query).get("v", [None])[0]
        if parsed.path.startswith("/shorts/") or parsed.path.startswith("/embed/"):
            parts = parsed.path.strip("/").split("/")
            return parts[1] if len(parts) > 1 else None
    return None


def canonical_youtube_url(video_id: str) -> str:
    return f"https://www.youtube.com/watch?v={video_id}"


def collect_youtube_candidates(results: list[LensResult]) -> list[YouTubeCandidate]:
    by_id: dict[str, YouTubeCandidate] = {}
    for result in results:
        video_id = extract_youtube_video_id(result.link)
        if not video_id:
            continue
        existing = by_id.get(video_id)
        if existing:
            existing.lens_rank = min(existing.lens_rank, result.rank)
            existing.raw.setdefault("sources", []).append(result.model_dump())
            if not existing.title and result.title:
                existing.title = result.title
            if not existing.description and result.snippet:
                existing.description = result.snippet
            if not existing.thumbnail and result.thumbnail:
                existing.thumbnail = result.thumbnail
            continue
        by_id[video_id] = YouTubeCandidate(
            url=canonical_youtube_url(video_id),
            video_id=video_id,
            title=result.title,
            description=result.snippet,
            thumbnail=result.thumbnail,
            lens_rank=result.rank,
            raw={"sources": [result.model_dump()]},
        )
    return sorted(by_id.values(), key=lambda candidate: candidate.lens_rank)
