from __future__ import annotations

from pathlib import Path
from typing import Any, Literal, TypedDict

from pydantic import BaseModel, Field


class FrameInfo(BaseModel):
    path: Path
    index: int
    timestamp_seconds: float
    sharpness: float = 0.0


class OcrText(BaseModel):
    text: str
    confidence: float = 0.0
    bbox: list[list[float]] = Field(default_factory=list)


class FrameOcrResult(BaseModel):
    frame_path: Path
    texts: list[OcrText] = Field(default_factory=list)

    @property
    def joined_text(self) -> str:
        return " ".join(item.text for item in self.texts if item.text).strip()


class UploadResult(BaseModel):
    public_url: str
    provider: str
    delete_ref: str | None = None
    expires_at: str | None = None
    cleanup_status: Literal["pending", "deleted", "failed", "skipped"] = "pending"
    cleanup_error: str | None = None


class LensResult(BaseModel):
    rank: int
    title: str = ""
    link: str
    source: str = ""
    thumbnail: str | None = None
    snippet: str = ""


class YouTubeCandidate(BaseModel):
    url: str
    video_id: str
    title: str = ""
    channel: str = ""
    description: str = ""
    thumbnail: str | None = None
    lens_rank: int
    published_at: str = ""
    duration: str = ""
    view_count: int | None = None
    like_count: int | None = None
    comment_count: int | None = None
    data_api_loaded: bool = False
    metadata_match_score: float = 0.0
    metadata_match_reason: str = ""
    raw: dict[str, Any] = Field(default_factory=dict)


class RankedCandidate(BaseModel):
    url: str
    video_id: str
    score: float
    reason: str
    title: str = ""
    lens_rank: int
    metadata_match_score: float = 0.0


class VideoFinderState(TypedDict, total=False):
    input_video_path: str
    work_dir: str
    frame_interval_seconds: float
    top_k: int
    ocr_backend: str
    uploader: str
    lens_json_path: str | None
    use_text_search: bool
    use_youtube_data_api: bool
    dry_run: bool
    debug: bool
    frames: list[FrameInfo]
    frames_manifest_path: str
    ocr_results: list[FrameOcrResult]
    ocr_results_json_path: str
    ocr_text_path: str
    ocr_search_context_path: str
    llm_search_request_path: str
    llm_search_response_path: str
    llm_search_attempts_path: str
    text_search_query_path: str
    google_custom_search_json_path: str
    google_custom_search_top3_path: str
    text_search_results: list[LensResult]
    selected_frame: FrameInfo
    selected_frame_path: str
    uploaded_image: UploadResult
    upload_result_path: str
    google_lens_json_path: str
    top3_links_path: str
    lens_results: list[LensResult]
    youtube_candidates: list[YouTubeCandidate]
    youtube_candidates_path: str
    youtube_candidates_enriched_path: str
    ranked_candidates_path: str
    cleanup_result_path: str
    ranked_candidates: list[RankedCandidate]
    warnings: list[str]
