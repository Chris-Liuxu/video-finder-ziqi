from pathlib import Path

import cv2
import numpy as np

from video_finder.graph import build_graph


def _write_test_video(path: Path) -> None:
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), 5.0, (160, 90))
    for index in range(10):
        frame = np.full((90, 160, 3), 255, dtype=np.uint8)
        cv2.putText(
            frame,
            f"Frame {index}",
            (20, 48),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (0, 0, 0),
            1,
            cv2.LINE_AA,
        )
        writer.write(frame)
    writer.release()


def test_graph_dry_run_end_to_end(tmp_path: Path):
    video = tmp_path / "input.mp4"
    _write_test_video(video)

    result = build_graph().invoke(
        {
            "input_video_path": str(video),
            "work_dir": str(tmp_path / "work"),
            "frame_interval_seconds": 0.5,
            "top_k": 3,
            "ocr_backend": "noop",
            "uploader": "dry_run",
            "use_youtube_data_api": False,
            "dry_run": True,
            "debug": True,
            "warnings": [],
        }
    )

    assert len(result["frames"]) > 0
    assert result["uploaded_image"].public_url.startswith("https://example.invalid/")
    assert result["uploaded_image"].cleanup_status == "deleted"
    assert len(result["ranked_candidates"]) == 3
