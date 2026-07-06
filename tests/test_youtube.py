from video_finder.services.youtube import collect_youtube_candidates, extract_youtube_video_id
from video_finder.models import LensResult


def test_extract_youtube_video_id_variants():
    assert extract_youtube_video_id("https://www.youtube.com/watch?v=abc123") == "abc123"
    assert extract_youtube_video_id("https://youtu.be/abc123") == "abc123"
    assert extract_youtube_video_id("https://www.youtube.com/shorts/abc123") == "abc123"
    assert extract_youtube_video_id("https://example.com/watch?v=abc123") is None


def test_collect_youtube_candidates_dedupes():
    results = [
        LensResult(rank=1, title="A", link="https://www.youtube.com/watch?v=abc123"),
        LensResult(rank=2, title="A dupe", link="https://youtu.be/abc123"),
    ]

    candidates = collect_youtube_candidates(results)

    assert len(candidates) == 1
    assert candidates[0].url == "https://www.youtube.com/watch?v=abc123"
