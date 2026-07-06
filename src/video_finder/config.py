from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    serpapi_api_key: str | None = None
    uploader: str = "imgbb"
    ocr_backend: str = "paddle"
    ocr_languages: str = "all"
    frame_interval_seconds: float = 2.0
    top_k: int = 3

    cloudinary_url: str | None = None
    imgbb_api_key: str | None = None
    imgbb_expiration_seconds: int = 86400
    youtube_api_key: str | None = None
    glm_api_key: str | None = None
    glm_model: str = "glm-4.7-flash"
    google_custom_search_api_key: str | None = None
    google_custom_search_cx: str | None = None
    public_base_url: str | None = None
