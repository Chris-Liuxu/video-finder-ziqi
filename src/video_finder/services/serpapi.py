from __future__ import annotations

import json
from pathlib import Path

import httpx

from video_finder.models import LensResult


DRY_RUN_LENS_RESULTS = [
    LensResult(
        rank=1,
        title="Original interview segment on YouTube",
        link="https://www.youtube.com/watch?v=ZiQiOriginal01",
        source="YouTube",
        thumbnail="https://i.ytimg.com/vi/ZiQiOriginal01/hqdefault.jpg",
        snippet="matching subtitle text and studio background",
    ),
    LensResult(
        rank=2,
        title="Reuploaded short clip",
        link="https://youtu.be/ZiQiReupload02",
        source="YouTube",
        thumbnail="https://i.ytimg.com/vi/ZiQiReupload02/hqdefault.jpg",
        snippet="similar frame but short clip",
    ),
    LensResult(
        rank=3,
        title="Related discussion video",
        link="https://www.youtube.com/watch?v=ZiQiRelated003",
        source="YouTube",
        thumbnail="https://i.ytimg.com/vi/ZiQiRelated003/hqdefault.jpg",
        snippet="same topic, weaker visual match",
    ),
]


class SerpApiClient:
    def __init__(self, api_key: str | None, dry_run: bool = False) -> None:
        self.api_key = api_key
        self.dry_run = dry_run

    def search_google_lens(self, image_url: str) -> list[LensResult]:
        return parse_google_lens_payload(self.search_google_lens_payload(image_url))

    def search_google_lens_payload(self, image_url: str) -> dict:
        if self.dry_run:
            return {"visual_matches": [result.model_dump() for result in DRY_RUN_LENS_RESULTS]}
        if not self.api_key:
            raise RuntimeError("SERPAPI_API_KEY is required unless --dry-run is used.")

        response = httpx.get(
            "https://serpapi.com/search.json",
            params={
                "engine": "google_lens",
                "url": image_url,
                "api_key": self.api_key,
                "type": "all",
            },
            timeout=60,
        )
        response.raise_for_status()
        return response.json()


def load_google_lens_json(path: Path) -> list[LensResult]:
    return parse_google_lens_payload(load_google_lens_payload(path))


def load_google_lens_payload(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def parse_google_lens_payload(payload: dict) -> list[LensResult]:
    results = payload.get("visual_matches") or payload.get("organic_results") or []
    lens_results: list[LensResult] = []
    for index, item in enumerate(results, start=1):
        link = item.get("link") or item.get("source") or ""
        if not link:
            continue
        lens_results.append(
            LensResult(
                rank=int(item.get("position") or index),
                title=item.get("title") or "",
                link=link,
                source=item.get("source") or "",
                thumbnail=item.get("thumbnail"),
                snippet=item.get("snippet") or "",
            )
        )
    return lens_results
