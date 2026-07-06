from __future__ import annotations

import json
from pathlib import Path

import httpx

from video_finder.models import LensResult
from video_finder.services.youtube import extract_youtube_video_id


class GoogleCustomSearchClient:
    def __init__(self, api_key: str, cx: str) -> None:
        self.api_key = api_key
        self.cx = cx

    def search_once(self, query: str, output_path: Path) -> dict:
        response = httpx.get(
            "https://www.googleapis.com/customsearch/v1",
            params={
                "key": self.api_key,
                "cx": self.cx,
                "q": query,
                "num": 10,
            },
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()
        output_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return payload


def parse_top_youtube_results(payload: dict, top_k: int = 3) -> list[LensResult]:
    results: list[LensResult] = []
    for item in payload.get("items", []):
        link = item.get("link") or ""
        if not extract_youtube_video_id(link):
            continue
        pagemap = item.get("pagemap") or {}
        thumbnails = pagemap.get("cse_thumbnail") or []
        thumbnail = thumbnails[0].get("src") if thumbnails else None
        results.append(
            LensResult(
                rank=len(results) + 1,
                title=item.get("title") or "",
                link=link,
                source="Google Custom Search",
                thumbnail=thumbnail,
                snippet=item.get("snippet") or "",
            )
        )
        if len(results) >= top_k:
            break
    return results
