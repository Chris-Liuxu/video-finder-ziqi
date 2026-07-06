from __future__ import annotations

import json
from pathlib import Path

from PIL import Image

from video_finder.config import Settings
from video_finder.models import VideoFinderState
from video_finder.services.google_custom_search import (
    GoogleCustomSearchClient,
    parse_top_youtube_results,
)
from video_finder.services.llm_search import GlmSearchPlanner


def _write_json(path: Path, payload: dict | list) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _artifact_paths(state: VideoFinderState) -> dict:
    work_dir = Path(state["work_dir"])
    return {
        "ocr_search_context_path": str(work_dir / "text_search_context.json"),
        "llm_search_request_path": str(work_dir / "llm_search_request.json"),
        "llm_search_response_path": str(work_dir / "llm_search_response.json"),
        "llm_search_attempts_path": str(work_dir / "llm_search_attempts.json"),
        "text_search_query_path": str(work_dir / "text_search_query.txt"),
        "google_custom_search_json_path": str(work_dir / "google_custom_search_api_return.json"),
        "google_custom_search_top3_path": str(work_dir / "google_custom_search_top3_links.txt"),
    }


def _extract_key_texts(state: VideoFinderState) -> list[dict]:
    rows: list[dict] = []
    for result in state.get("ocr_results", []):
        for item in result.texts:
            text = item.text.strip()
            if not text:
                continue
            rows.append(
                {
                    "frame_path": str(result.frame_path),
                    "text": text,
                    "confidence": item.confidence,
                    "score": item.confidence * max(len(text), 1),
                }
            )
    rows.sort(key=lambda row: row["score"], reverse=True)
    return rows[:30]


def _selected_frame_environment(state: VideoFinderState) -> dict | None:
    selected = state.get("selected_frame")
    if not selected:
        return None
    environment = selected.model_dump(mode="json")
    try:
        with Image.open(selected.path) as image:
            environment["image_width"] = image.width
            environment["image_height"] = image.height
    except Exception as exc:
        environment["image_probe_error"] = str(exc)
    return environment


def text_search(state: VideoFinderState) -> VideoFinderState:
    settings = Settings()
    work_dir = Path(state["work_dir"])
    warnings = list(state.get("warnings", []))

    context_path = work_dir / "text_search_context.json"
    llm_request_path = work_dir / "llm_search_request.json"
    llm_response_path = work_dir / "llm_search_response.json"
    llm_attempts_path = work_dir / "llm_search_attempts.json"
    query_path = work_dir / "text_search_query.txt"
    cse_json_path = work_dir / "google_custom_search_api_return.json"
    top3_path = work_dir / "google_custom_search_top3_links.txt"
    artifact_paths = _artifact_paths(state)

    if not state.get("use_text_search", True):
        skipped_path = work_dir / "text_search_skipped.json"
        payload = {
            "skipped": True,
            "reason": "disabled by --skip-text-search",
            "disabled_steps": [
                "text_search_context",
                "glm_search_planning",
                "google_custom_search",
            ],
        }
        _write_json(skipped_path, payload)
        _write_json(context_path, payload)
        _write_json(llm_request_path, payload)
        _write_json(llm_response_path, payload)
        _write_json(llm_attempts_path, [])
        query_path.write_text("", encoding="utf-8")
        _write_json(cse_json_path, payload)
        top3_path.write_text("", encoding="utf-8")
        return {
            "text_search_results": [],
            **artifact_paths,
            "warnings": warnings,
        }

    context = {
        "objective": "Find original YouTube video for this tampered clip.",
        "key_ocr_texts": _extract_key_texts(state),
        "selected_frame_environment": _selected_frame_environment(state),
        "frame_count": len(state.get("frames", [])),
        "notes": [
            "Do not use face identity.",
            "Prefer visible subtitles, logos, program titles, scene text, and distinctive context.",
            "Return JSON with a single field: query.",
        ],
    }
    _write_json(context_path, context)

    if state.get("dry_run", False):
        query = "site:youtube.com/watch original video interview subtitles"
    elif not settings.glm_api_key:
        warnings.append("GLM_API_KEY is not set; skipping LLM text search planning.")
        _write_json(llm_request_path, {"skipped": True, "reason": "missing GLM_API_KEY"})
        _write_json(llm_response_path, {"skipped": True, "reason": "missing GLM_API_KEY"})
        _write_json(llm_attempts_path, [])
        _write_json(cse_json_path, {"skipped": True, "reason": "missing GLM_API_KEY"})
        query_path.write_text("", encoding="utf-8")
        top3_path.write_text("", encoding="utf-8")
        return {
            "text_search_results": [],
            **artifact_paths,
            "warnings": warnings,
        }
    else:
        query = GlmSearchPlanner(settings.glm_api_key, settings.glm_model).plan_query(
            context=context,
            request_path=llm_request_path,
            response_path=llm_response_path,
            attempts_path=llm_attempts_path,
            max_attempts=5,
        )

    if not query:
        warnings.append("LLM did not produce a text search query; skipping Google Custom Search.")
        _write_json(cse_json_path, {"skipped": True, "reason": "empty LLM query"})
        query_path.write_text("", encoding="utf-8")
        top3_path.write_text("", encoding="utf-8")
        return {
            "text_search_results": [],
            **artifact_paths,
            "warnings": warnings,
        }

    if "youtube" not in query.lower():
        query = f"{query} site:youtube.com/watch"
    query_path.write_text(query, encoding="utf-8")

    if state.get("dry_run", False):
        payload = {"items": []}
        _write_json(llm_request_path, {"dry_run": True})
        _write_json(llm_response_path, {"dry_run": True, "query": query})
        _write_json(llm_attempts_path, [{"attempt": 1, "status": "dry_run", "query": query}])
        _write_json(cse_json_path, payload)
    elif not settings.google_custom_search_api_key or not settings.google_custom_search_cx:
        warnings.append(
            "GOOGLE_CUSTOM_SEARCH_API_KEY or GOOGLE_CUSTOM_SEARCH_CX is not set; "
            "skipping Google Custom Search."
        )
        _write_json(
            cse_json_path,
            {"skipped": True, "reason": "missing Google Custom Search API key or CX"},
        )
        top3_path.write_text("", encoding="utf-8")
        return {
            "text_search_results": [],
            **artifact_paths,
            "warnings": warnings,
        }
    else:
        payload = GoogleCustomSearchClient(
            settings.google_custom_search_api_key,
            settings.google_custom_search_cx,
        ).search_once(query, cse_json_path)

    results = parse_top_youtube_results(payload, top_k=3)
    top3_path.write_text("\n".join(result.link for result in results), encoding="utf-8")
    return {
        "text_search_results": results,
        **artifact_paths,
        "warnings": warnings,
    }
