from __future__ import annotations

from difflib import SequenceMatcher
from pathlib import Path

import httpx
import imagehash
from PIL import Image

from video_finder.models import FrameInfo, FrameOcrResult, RankedCandidate, YouTubeCandidate


def text_similarity(left: str, right: str) -> float:
    left = " ".join(left.lower().split())
    right = " ".join(right.lower().split())
    if not left or not right:
        return 0.0
    return SequenceMatcher(None, left, right).ratio()


def thumbnail_similarity(
    frame_path: Path,
    thumbnail_url: str | None,
    thumbnail_path: Path | None = None,
) -> float:
    if not thumbnail_url:
        return 0.0
    try:
        response = httpx.get(thumbnail_url, timeout=10, follow_redirects=True)
        response.raise_for_status()
        thumb_path = thumbnail_path or frame_path.parent / "candidate_thumb.jpg"
        thumb_path.parent.mkdir(parents=True, exist_ok=True)
        thumb_path.write_bytes(response.content)
        query_hash = imagehash.phash(Image.open(frame_path))
        thumb_hash = imagehash.phash(Image.open(thumb_path))
        distance = query_hash - thumb_hash
        return max(0.0, 1.0 - distance / 64.0)
    except Exception:
        return 0.0


def rank_candidates(
    candidates: list[YouTubeCandidate],
    selected_frame: FrameInfo,
    ocr_results: list[FrameOcrResult],
    top_k: int,
    work_dir: Path | None = None,
) -> list[RankedCandidate]:
    ocr_text = " ".join(result.joined_text for result in ocr_results if result.joined_text)
    ranked: list[RankedCandidate] = []
    for candidate in candidates:
        lens_score = max(0.0, 1.0 - ((candidate.lens_rank - 1) * 0.12))
        metadata_text = " ".join(
            [
                candidate.title,
                candidate.description,
                candidate.channel,
                candidate.duration,
                candidate.published_at,
            ]
        )
        text_score = text_similarity(
            ocr_text,
            metadata_text,
        )
        thumbnail_path = None
        if work_dir:
            thumbnail_path = (
                work_dir
                / "thumbnails"
                / f"lens_{candidate.lens_rank:02d}_{candidate.video_id}.jpg"
            )
        visual_score = thumbnail_similarity(
            selected_frame.path,
            candidate.thumbnail,
            thumbnail_path=thumbnail_path,
        )
        metadata_score = 0.15 if candidate.data_api_loaded else 0.0
        candidate.metadata_match_score = metadata_score
        candidate.metadata_match_reason = (
            "youtube_data_api=loaded" if candidate.data_api_loaded else "youtube_data_api=missing"
        )
        score = (
            (0.45 * lens_score)
            + (0.25 * text_score)
            + (0.25 * visual_score)
            + (0.05 * metadata_score)
        )
        reasons = [
            f"lens_rank={candidate.lens_rank}",
            f"text={text_score:.2f}",
            f"thumbnail={visual_score:.2f}",
            f"metadata={metadata_score:.2f}",
        ]
        if thumbnail_path and thumbnail_path.exists():
            reasons.append(f"thumb_file={thumbnail_path}")
        reasons.append(candidate.metadata_match_reason)
        ranked.append(
            RankedCandidate(
                url=candidate.url,
                video_id=candidate.video_id,
                title=candidate.title,
                lens_rank=candidate.lens_rank,
                metadata_match_score=metadata_score,
                score=round(score, 4),
                reason=", ".join(reasons),
            )
        )
    ranked.sort(key=lambda item: item.score, reverse=True)
    return ranked[:top_k]
