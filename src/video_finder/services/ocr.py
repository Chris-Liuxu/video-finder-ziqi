from __future__ import annotations

from pathlib import Path
from typing import Protocol

from video_finder.models import FrameOcrResult, OcrText


PADDLE_GLOBAL_LANGUAGES = [
    "ch",
    "en",
    "japan",
    "korean",
    "fr",
    "german",
    "es",
    "pt",
    "ru",
    "ar",
    "hi",
    "ta",
    "te",
    "ka",
    "ug",
    "fa",
    "ur",
    "rs_latin",
    "rs_cyrillic",
    "bg",
    "uk",
    "be",
]


class OcrEngine(Protocol):
    def read(self, image_path: Path) -> FrameOcrResult:
        ...


class NoopOcrEngine:
    def read(self, image_path: Path) -> FrameOcrResult:
        return FrameOcrResult(frame_path=image_path, texts=[])


class EasyOcrEngine:
    def __init__(self, languages: str = "ch_sim,en") -> None:
        try:
            import easyocr
        except ImportError as exc:
            raise RuntimeError(
                "EasyOCR is not installed. Run `uv sync --extra ocr` or use "
                "`--ocr-backend noop` for dry-run tests."
            ) from exc
        language_list = [item.strip() for item in languages.split(",") if item.strip()]
        self._reader = easyocr.Reader(language_list or ["ch_sim", "en"], gpu=False)

    def read(self, image_path: Path) -> FrameOcrResult:
        raw = self._reader.readtext(str(image_path))
        texts: list[OcrText] = []
        for bbox, text, confidence in raw or []:
            texts.append(
                OcrText(
                    text=str(text),
                    confidence=float(confidence),
                    bbox=[[float(x), float(y)] for x, y in bbox],
                )
            )
        return FrameOcrResult(frame_path=image_path, texts=texts)


class PaddleOcrEngine:
    def __init__(self, languages: str = "all") -> None:
        try:
            from paddleocr import PaddleOCR
        except ImportError as exc:
            raise RuntimeError(
                "PaddleOCR is not installed. Run `uv sync --extra paddle` or use "
                "`--ocr-backend noop` for dry-run tests."
            ) from exc
        configured = [item.strip() for item in languages.split(",") if item.strip()]
        self._languages = (
            PADDLE_GLOBAL_LANGUAGES if configured == ["all"] else configured or ["ch", "en"]
        )
        self._ocr_by_language = {
            language: PaddleOCR(use_angle_cls=True, lang=language) for language in self._languages
        }

    def read(self, image_path: Path) -> FrameOcrResult:
        texts: list[OcrText] = []
        seen: set[tuple[str, str]] = set()
        for language, ocr in self._ocr_by_language.items():
            try:
                raw = ocr.ocr(str(image_path), cls=True)
            except Exception:
                continue
            for page in raw or []:
                for item in page or []:
                    if len(item) < 2:
                        continue
                    bbox = item[0] or []
                    text, confidence = item[1]
                    key = (str(text).strip(), str(bbox))
                    if not key[0] or key in seen:
                        continue
                    seen.add(key)
                    texts.append(
                        OcrText(text=str(text), confidence=float(confidence), bbox=bbox)
                    )
        return FrameOcrResult(frame_path=image_path, texts=texts)


def make_ocr_engine(name: str, languages: str = "ch_sim,en") -> OcrEngine:
    normalized = name.lower()
    if normalized == "noop":
        return NoopOcrEngine()
    if normalized == "easyocr":
        return EasyOcrEngine(languages=languages)
    if normalized == "paddle":
        return PaddleOcrEngine(languages=languages)
    raise ValueError(f"Unsupported OCR backend: {name}")
