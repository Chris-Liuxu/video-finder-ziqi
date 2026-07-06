from video_finder.services.youtube_data_api import _best_thumbnail


def test_best_thumbnail_prefers_highest_quality():
    thumbnails = {
        "default": {"url": "default.jpg"},
        "high": {"url": "high.jpg"},
        "maxres": {"url": "maxres.jpg"},
    }

    assert _best_thumbnail(thumbnails) == "maxres.jpg"
