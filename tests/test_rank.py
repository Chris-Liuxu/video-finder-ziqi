from pathlib import Path

from PIL import Image

from video_finder.models import FrameInfo, FrameOcrResult, LensResult, OcrText
from video_finder.services.video_compare import rank_candidates, text_similarity
from video_finder.services.youtube import collect_youtube_candidates


def test_text_similarity_empty_safe():
    assert text_similarity("", "hello") == 0.0
    assert text_similarity("hello world", "hello world") == 1.0


def test_rank_candidates_prefers_top_lens_and_text(tmp_path: Path):
    frame_path = tmp_path / "frame.jpg"
    Image.new("RGB", (64, 64), "white").save(frame_path)
    frame = FrameInfo(path=frame_path, index=0, timestamp_seconds=0, sharpness=10)
    ocr = [FrameOcrResult(frame_path=frame_path, texts=[OcrText(text="studio interview")])]
    candidates = collect_youtube_candidates(
        [
            LensResult(
                rank=1,
                title="studio interview original",
                link="https://www.youtube.com/watch?v=best",
            ),
            LensResult(rank=2, title="unrelated", link="https://www.youtube.com/watch?v=other"),
        ]
    )

    ranked = rank_candidates(candidates, frame, ocr, top_k=2)

    assert ranked[0].video_id == "best"
    assert ranked[0].score >= ranked[1].score
