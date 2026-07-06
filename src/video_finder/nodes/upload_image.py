from __future__ import annotations

import json
from pathlib import Path

from video_finder.config import Settings
from video_finder.models import UploadResult, VideoFinderState
from video_finder.services.image_hosting import make_uploader


def upload_image(state: VideoFinderState) -> VideoFinderState:
    output_path = Path(state["work_dir"]) / "upload_result.json"
    if state.get("lens_json_path"):
        upload = UploadResult(
            public_url=str(state["lens_json_path"]),
            provider="lens_json",
            cleanup_status="skipped",
        )
        output_path.write_text(
            json.dumps(upload.model_dump(mode="json"), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return {"uploaded_image": upload, "upload_result_path": str(output_path)}

    settings = Settings()
    uploader = make_uploader(
        settings=settings,
        name=str(state.get("uploader") or settings.uploader),
        dry_run=bool(state.get("dry_run", False)),
    )
    selected = state["selected_frame"]
    upload = uploader.upload(selected.path)
    output_path.write_text(
        json.dumps(upload.model_dump(mode="json"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return {"uploaded_image": upload, "upload_result_path": str(output_path)}
