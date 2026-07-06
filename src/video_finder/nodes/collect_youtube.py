from __future__ import annotations

import json
from pathlib import Path

from video_finder.models import VideoFinderState
from video_finder.services.youtube import collect_youtube_candidates


def collect_youtube(state: VideoFinderState) -> VideoFinderState:
    results = list(state.get("lens_results", [])) + list(state.get("text_search_results", []))
    candidates = collect_youtube_candidates(results)
    output_path = Path(state["work_dir"]) / "youtube_candidates_initial.json"
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
        "youtube_candidates_path": str(output_path),
    }
