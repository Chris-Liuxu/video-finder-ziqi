from __future__ import annotations

import json
from pathlib import Path

from video_finder.config import Settings
from video_finder.models import VideoFinderState
from video_finder.services.ocr import make_ocr_engine


OCR_JSON_OUTPUT_NAME = "ocr_results.json"
OCR_TEXT_OUTPUT_NAME = "ocr_text.txt"


def ocr_frames(state: VideoFinderState) -> VideoFinderState:
    settings = Settings()
    engine = make_ocr_engine(
        str(state.get("ocr_backend", settings.ocr_backend)),
        languages=settings.ocr_languages,
    )
    results = [engine.read(frame.path) for frame in state.get("frames", [])]
    work_dir = Path(state["work_dir"])
    json_path = work_dir / OCR_JSON_OUTPUT_NAME
    text_path = work_dir / OCR_TEXT_OUTPUT_NAME

    json_path.write_text(
        json.dumps(
            [result.model_dump(mode="json") for result in results],
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    text_lines: list[str] = []
    for result in results:
        text_lines.append(f"# {result.frame_path}")
        if result.texts:
            for item in result.texts:
                text_lines.append(f"- [{item.confidence:.2f}] {item.text}")
        else:
            text_lines.append("- <no text>")
        text_lines.append("")
    text_path.write_text("\n".join(text_lines), encoding="utf-8")

    return {
        "ocr_results": results,
        "ocr_results_json_path": str(json_path),
        "ocr_text_path": str(text_path),
    }
