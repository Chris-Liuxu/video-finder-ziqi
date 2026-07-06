from __future__ import annotations

import base64
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Protocol

import httpx

from video_finder.config import Settings
from video_finder.models import UploadResult


class ImageUploader(Protocol):
    def upload(self, image_path: Path) -> UploadResult:
        ...

    def cleanup(self, upload: UploadResult) -> UploadResult:
        ...


class DryRunUploader:
    def upload(self, image_path: Path) -> UploadResult:
        return UploadResult(
            public_url=f"https://example.invalid/video-finder/{image_path.name}",
            provider="dry_run",
            delete_ref=image_path.name,
        )

    def cleanup(self, upload: UploadResult) -> UploadResult:
        upload.cleanup_status = "deleted"
        return upload


class ImgBbUploader:
    def __init__(self, api_key: str, expiration_seconds: int) -> None:
        self.api_key = api_key
        self.expiration_seconds = expiration_seconds

    def upload(self, image_path: Path) -> UploadResult:
        encoded = base64.b64encode(image_path.read_bytes()).decode("ascii")
        response = httpx.post(
            "https://api.imgbb.com/1/upload",
            data={
                "key": self.api_key,
                "image": encoded,
                "name": image_path.stem,
                "expiration": str(self.expiration_seconds),
            },
            timeout=60,
        )
        response.raise_for_status()
        payload = response.json()
        data = payload["data"]
        expires_at = datetime.now(UTC) + timedelta(seconds=self.expiration_seconds)
        return UploadResult(
            public_url=data["url"],
            provider="imgbb",
            delete_ref=data.get("delete_url"),
            expires_at=expires_at.isoformat(),
        )

    def cleanup(self, upload: UploadResult) -> UploadResult:
        upload.cleanup_status = "skipped"
        upload.cleanup_error = (
            "ImgBB cleanup is skipped; uploaded image should expire via IMGBB_EXPIRATION_SECONDS."
        )
        return upload


class CloudinaryUploader:
    def __init__(self) -> None:
        try:
            import cloudinary
            import cloudinary.uploader
        except ImportError as exc:
            raise RuntimeError(
                "Cloudinary uploader requires `uv sync --extra cloudinary`."
            ) from exc
        self._cloudinary = cloudinary
        self._uploader = cloudinary.uploader

    def upload(self, image_path: Path) -> UploadResult:
        result = self._uploader.upload(str(image_path), folder="video-finder-ziqi")
        return UploadResult(
            public_url=result["secure_url"],
            provider="cloudinary",
            delete_ref=result["public_id"],
        )

    def cleanup(self, upload: UploadResult) -> UploadResult:
        if not upload.delete_ref:
            upload.cleanup_status = "skipped"
            upload.cleanup_error = "Missing Cloudinary public_id."
            return upload
        result = self._uploader.destroy(upload.delete_ref, invalidate=True)
        if result.get("result") in {"ok", "not found"}:
            upload.cleanup_status = "deleted"
        else:
            upload.cleanup_status = "failed"
            upload.cleanup_error = str(result)
        return upload


def make_uploader(settings: Settings, name: str, dry_run: bool) -> ImageUploader:
    if dry_run or name == "dry_run":
        return DryRunUploader()
    if name == "imgbb":
        if not settings.imgbb_api_key:
            raise RuntimeError("IMGBB_API_KEY is required for `--uploader imgbb`.")
        return ImgBbUploader(settings.imgbb_api_key, settings.imgbb_expiration_seconds)
    if name == "cloudinary":
        if not settings.cloudinary_url:
            raise RuntimeError("CLOUDINARY_URL is required for `--uploader cloudinary`.")
        return CloudinaryUploader()
    raise ValueError(f"Unsupported uploader: {name}")
