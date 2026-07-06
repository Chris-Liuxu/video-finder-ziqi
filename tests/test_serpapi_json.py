from pathlib import Path

from video_finder.services.serpapi import load_google_lens_json
from video_finder.services.youtube import collect_youtube_candidates


def test_load_saved_google_lens_json():
    results = load_google_lens_json(Path("tests/google_lens_api_return.json"))
    candidates = collect_youtube_candidates(results)

    assert len(results) > 0
    assert len(candidates) > 0
    assert candidates[0].url == "https://www.youtube.com/watch?v=pqXpo1epTyA"
