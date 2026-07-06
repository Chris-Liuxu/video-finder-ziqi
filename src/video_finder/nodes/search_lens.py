from __future__ import annotations

from pathlib import Path
import json
import shutil

from video_finder.config import Settings
from video_finder.models import VideoFinderState
from video_finder.services.serpapi import (
    SerpApiClient,
    load_google_lens_payload,
    parse_google_lens_payload,
)


GOOGLE_LENS_OUTPUT_NAME = "google_lens_api_return.json"


def search_lens(state: VideoFinderState) -> VideoFinderState:
    work_dir = Path(state["work_dir"])
    output_path = work_dir / GOOGLE_LENS_OUTPUT_NAME

    if state.get("lens_json_path"):
        source_path = Path(state["lens_json_path"])
        if source_path.resolve() != output_path.resolve():
            shutil.copyfile(source_path, output_path)
        payload = load_google_lens_payload(output_path)
        return {
            "lens_results": parse_google_lens_payload(payload),
            "google_lens_json_path": str(output_path),
        }

    settings = Settings()
    client = SerpApiClient(
        api_key=settings.serpapi_api_key,
        dry_run=bool(state.get("dry_run", False)),
    )
    upload = state["uploaded_image"]
    payload = client.search_google_lens_payload(upload.public_url)
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return {
        "lens_results": parse_google_lens_payload(payload),
        "google_lens_json_path": str(output_path),
    }
