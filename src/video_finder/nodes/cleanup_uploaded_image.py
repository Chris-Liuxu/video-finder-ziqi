from __future__ import annotations

import json
from pathlib import Path

from video_finder.config import Settings
from video_finder.models import VideoFinderState
from video_finder.services.image_hosting import make_uploader


def cleanup_uploaded_image(state: VideoFinderState) -> VideoFinderState:
    upload = state.get("uploaded_image")
    if not upload:
        return {}
    output_path = Path(state["work_dir"]) / "cleanup_upload_result.json"
    if upload.provider == "lens_json":
        output_path.write_text(
            json.dumps(upload.model_dump(mode="json"), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return {"uploaded_image": upload, "cleanup_result_path": str(output_path)}
    try:
        settings = Settings()
        uploader = make_uploader(
            settings=settings,
            name=str(state.get("uploader") or settings.uploader),
            dry_run=bool(state.get("dry_run", False)),
        )
        cleaned = uploader.cleanup(upload)
        warnings = list(state.get("warnings", []))
        if cleaned.cleanup_status in {"failed", "skipped"} and cleaned.cleanup_error:
            warnings.append(f"Image cleanup {cleaned.cleanup_status}: {cleaned.cleanup_error}")
        output_path.write_text(
            json.dumps(cleaned.model_dump(mode="json"), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return {
            "uploaded_image": cleaned,
            "cleanup_result_path": str(output_path),
            "warnings": warnings,
        }
    except Exception as exc:
        upload.cleanup_status = "failed"
        upload.cleanup_error = str(exc)
        warnings = list(state.get("warnings", []))
        warnings.append(f"Image cleanup failed: {exc}")
        output_path.write_text(
            json.dumps(upload.model_dump(mode="json"), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return {
            "uploaded_image": upload,
            "cleanup_result_path": str(output_path),
            "warnings": warnings,
        }
