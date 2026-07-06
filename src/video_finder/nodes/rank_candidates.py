from __future__ import annotations

import json
from pathlib import Path

from video_finder.models import VideoFinderState
from video_finder.services.video_compare import rank_candidates as rank


def rank_candidates(state: VideoFinderState) -> VideoFinderState:
    work_dir = Path(state["work_dir"])
    ranked = rank(
        candidates=state.get("youtube_candidates", []),
        selected_frame=state["selected_frame"],
        ocr_results=state.get("ocr_results", []),
        top_k=int(state.get("top_k", 3)),
        work_dir=work_dir,
    )
    output_path = work_dir / "ranked_candidates.json"
    output_path.write_text(
        json.dumps(
            [candidate.model_dump(mode="json") for candidate in ranked],
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return {"ranked_candidates": ranked, "ranked_candidates_path": str(output_path)}
