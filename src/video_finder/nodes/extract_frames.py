from __future__ import annotations

import json
from pathlib import Path

import cv2

from video_finder.models import FrameInfo, VideoFinderState
from video_finder.utils.images import image_sharpness


def extract_frames(state: VideoFinderState) -> VideoFinderState:
    video_path = Path(state["input_video_path"])
    work_dir = Path(state["work_dir"])
    frames_dir = work_dir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)

    capture = cv2.VideoCapture(str(video_path))
    if not capture.isOpened():
        raise RuntimeError(f"Could not open video: {video_path}")

    fps = capture.get(cv2.CAP_PROP_FPS) or 25.0
    frame_interval = max(float(state.get("frame_interval_seconds", 2.0)), 0.1)
    step = max(int(fps * frame_interval), 1)

    frames: list[FrameInfo] = []
    frame_index = 0
    saved_index = 0
    while True:
        ok, frame = capture.read()
        if not ok:
            break
        if frame_index % step == 0:
            timestamp = frame_index / fps
            frame_path = frames_dir / f"frame_{saved_index:04d}_{timestamp:.2f}s.jpg"
            cv2.imwrite(str(frame_path), frame)
            frames.append(
                FrameInfo(
                    path=frame_path,
                    index=saved_index,
                    timestamp_seconds=timestamp,
                    sharpness=image_sharpness(frame_path),
                )
            )
            saved_index += 1
        frame_index += 1

    capture.release()
    if not frames:
        raise RuntimeError(f"No frames extracted from video: {video_path}")
    manifest_path = work_dir / "frames_manifest.json"
    manifest_path.write_text(
        json.dumps(
            [frame.model_dump(mode="json") for frame in frames],
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return {"frames": frames, "frames_manifest_path": str(manifest_path)}
