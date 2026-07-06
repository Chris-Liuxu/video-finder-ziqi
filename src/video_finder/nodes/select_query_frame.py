from __future__ import annotations

import json
from pathlib import Path

from video_finder.models import FrameInfo, FrameOcrResult, VideoFinderState


def _score_frame(frame: FrameInfo, ocr: FrameOcrResult | None) -> float:
    text_score = 0.0
    if ocr:
        text_score = sum(max(item.confidence, 0.5) * len(item.text) for item in ocr.texts)
    sharpness_score = min(frame.sharpness / 1000.0, 1.0)
    return text_score + sharpness_score


def select_query_frame(state: VideoFinderState) -> VideoFinderState:
    frames = state.get("frames", [])
    ocr_results = {result.frame_path: result for result in state.get("ocr_results", [])}
    if not frames:
        raise RuntimeError("No frames available to select.")
    selected = max(frames, key=lambda frame: _score_frame(frame, ocr_results.get(frame.path)))
    output_path = Path(state["work_dir"]) / "selected_frame.json"
    output_path.write_text(
        json.dumps(selected.model_dump(mode="json"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return {"selected_frame": selected, "selected_frame_path": str(output_path)}
