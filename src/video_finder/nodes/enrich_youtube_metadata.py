from __future__ import annotations

import json
from pathlib import Path

from video_finder.config import Settings
from video_finder.models import VideoFinderState
from video_finder.services.youtube_data_api import YouTubeDataApiClient


def enrich_youtube_metadata(state: VideoFinderState) -> VideoFinderState:
    candidates = list(state.get("youtube_candidates", []))
    output_path = Path(state["work_dir"]) / "youtube_candidates_enriched.json"
    if not state.get("use_youtube_data_api", True) or state.get("dry_run", False):
        output_path.write_text(
            json.dumps(
                [candidate.model_dump(mode="json") for candidate in candidates],
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        return {
            "youtube_candidates": candidates,
            "youtube_candidates_enriched_path": str(output_path),
        }

    settings = Settings()
    if not settings.youtube_api_key:
        warnings = list(state.get("warnings", []))
        warnings.append("YOUTUBE_API_KEY is not set; using Google Lens metadata only.")
        output_path.write_text(
            json.dumps(
                [candidate.model_dump(mode="json") for candidate in candidates],
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        return {
            "youtube_candidates": candidates,
            "youtube_candidates_enriched_path": str(output_path),
            "warnings": warnings,
        }

    try:
        enriched = YouTubeDataApiClient(settings.youtube_api_key).enrich_candidates(candidates)
        output_path.write_text(
            json.dumps(
                [candidate.model_dump(mode="json") for candidate in enriched],
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        return {
            "youtube_candidates": enriched,
            "youtube_candidates_enriched_path": str(output_path),
        }
    except Exception as exc:
        warnings = list(state.get("warnings", []))
        warnings.append(f"YouTube Data API metadata fetch failed: {exc}")
        output_path.write_text(
            json.dumps(
                [candidate.model_dump(mode="json") for candidate in candidates],
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        return {
            "youtube_candidates": candidates,
            "youtube_candidates_enriched_path": str(output_path),
            "warnings": warnings,
        }
