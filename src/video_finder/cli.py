from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from video_finder.config import Settings
from video_finder.graph import build_graph
from video_finder.services.image_hosting import make_uploader
from video_finder.utils.files import ensure_work_dir

app = typer.Typer(no_args_is_help=True)
console = Console()


@app.callback()
def main() -> None:
    """Find original YouTube candidates for tampered video clips."""


@app.command()
def find(
    video: Path = typer.Argument(..., exists=True, file_okay=True, dir_okay=False),
    top_k: int = typer.Option(None, "--top-k", help="Number of candidate links to return."),
    frame_interval: float = typer.Option(
        None, "--frame-interval", help="Seconds between extracted frames."
    ),
    ocr_backend: str = typer.Option(None, "--ocr-backend", help="paddle, easyocr, or noop."),
    uploader: str = typer.Option(None, "--uploader", help="imgbb, cloudinary, or dry_run."),
    lens_json: Path | None = typer.Option(
        None,
        "--lens-json",
        exists=True,
        file_okay=True,
        dir_okay=False,
        help="Use a saved SerpAPI Google Lens JSON response instead of calling SerpAPI.",
    ),
    use_youtube_data_api: bool = typer.Option(
        True,
        "--youtube-data-api/--skip-youtube-data-api",
        help="Use YouTube Data API to enrich candidate metadata when YOUTUBE_API_KEY is set.",
    ),
    use_text_search: bool = typer.Option(
        True,
        "--text-search/--skip-text-search",
        help="Use optional OCR + GLM + Google Custom Search text-search workflow.",
    ),
    dry_run: bool = typer.Option(False, "--dry-run", help="Use mock uploader and Lens results."),
    debug: bool = typer.Option(False, "--debug", help="Print intermediate details."),
) -> None:
    settings = Settings()
    work_dir = ensure_work_dir()
    initial_state = {
        "input_video_path": str(video.resolve()),
        "work_dir": str(work_dir),
        "frame_interval_seconds": frame_interval or settings.frame_interval_seconds,
        "top_k": top_k or settings.top_k,
        "ocr_backend": ocr_backend or ("noop" if dry_run else settings.ocr_backend),
        "uploader": uploader or ("dry_run" if dry_run else settings.uploader),
        "lens_json_path": str(lens_json.resolve()) if lens_json else None,
        "use_text_search": use_text_search,
        "use_youtube_data_api": use_youtube_data_api,
        "dry_run": dry_run,
        "debug": debug,
        "warnings": [],
    }

    result = build_graph().invoke(initial_state)
    upload = result.get("uploaded_image")
    ranked = result.get("ranked_candidates", [])
    top3_links_path = work_dir / "top3_video_links.txt"
    top3_links_path.write_text(
        "\n".join(candidate.url for candidate in ranked) + ("\n" if ranked else ""),
        encoding="utf-8",
    )

    if debug and upload:
        console.print("Lens input:")
        console.print(f"  provider: {upload.provider}")
        console.print(f"  source: {upload.public_url}")
        console.print(f"  cleanup: {upload.cleanup_status}")
        if upload.cleanup_error:
            console.print(f"  cleanup_error: {upload.cleanup_error}")
        console.print(f"Work dir: {work_dir}")
        if result.get("frames_manifest_path"):
            console.print(f"Frames manifest: {result['frames_manifest_path']}")
        if result.get("ocr_results_json_path"):
            console.print(f"OCR JSON: {result['ocr_results_json_path']}")
        if result.get("ocr_text_path"):
            console.print(f"OCR text: {result['ocr_text_path']}")
        if result.get("ocr_search_context_path"):
            console.print(f"Text search context: {result['ocr_search_context_path']}")
        if result.get("llm_search_request_path"):
            console.print(f"LLM search request: {result['llm_search_request_path']}")
        if result.get("llm_search_response_path"):
            console.print(f"LLM search response: {result['llm_search_response_path']}")
        if result.get("llm_search_attempts_path"):
            console.print(f"LLM search attempts: {result['llm_search_attempts_path']}")
        if result.get("text_search_query_path"):
            console.print(f"Text search query: {result['text_search_query_path']}")
        if result.get("google_custom_search_json_path"):
            console.print(f"Google Custom Search JSON: {result['google_custom_search_json_path']}")
        if result.get("google_custom_search_top3_path"):
            console.print(f"Google Custom Search Top 3: {result['google_custom_search_top3_path']}")
        if result.get("upload_result_path"):
            console.print(f"Upload result: {result['upload_result_path']}")
        if result.get("google_lens_json_path"):
            console.print(f"Google Lens JSON: {result['google_lens_json_path']}")
        if result.get("youtube_candidates_path"):
            console.print(f"YouTube candidates: {result['youtube_candidates_path']}")
        if result.get("youtube_candidates_enriched_path"):
            console.print(
                f"YouTube candidates enriched: {result['youtube_candidates_enriched_path']}"
            )
        if result.get("ranked_candidates_path"):
            console.print(f"Ranked candidates: {result['ranked_candidates_path']}")
        if result.get("cleanup_result_path"):
            console.print(f"Cleanup result: {result['cleanup_result_path']}")
        console.print(f"Top 3 links file: {top3_links_path}")

    table = Table(title=f"Top {len(ranked)} candidate original videos")
    table.add_column("#", justify="right")
    table.add_column("Score", justify="right")
    table.add_column("URL", overflow="fold")
    table.add_column("Reason")
    for index, candidate in enumerate(ranked, start=1):
        table.add_row(str(index), f"{candidate.score:.2f}", candidate.url, candidate.reason)
    console.print(table)

    for warning in result.get("warnings", []):
        console.print(f"[yellow]Warning:[/yellow] {warning}")

    if not ranked:
        raise typer.Exit(code=2)


@app.command("test-uploader")
def test_uploader(
    image: Path = typer.Argument(..., exists=True, file_okay=True, dir_okay=False),
    uploader: str = typer.Option("imgbb", "--uploader", help="imgbb or cloudinary."),
    keep: bool = typer.Option(
        False,
        "--keep/--cleanup",
        help="Keep the uploaded image so the returned URL remains visible.",
    ),
) -> None:
    settings = Settings()
    try:
        service = make_uploader(settings=settings, name=uploader, dry_run=False)
        upload = service.upload(image)
    except RuntimeError as exc:
        console.print(f"[red]Uploader error:[/red] {exc}")
        raise typer.Exit(code=1) from exc
    console.print(f"provider: {upload.provider}")
    console.print(f"url: {upload.public_url}")
    if keep:
        console.print("cleanup: skipped by --keep")
        return
    cleaned = service.cleanup(upload)
    console.print(f"cleanup: {cleaned.cleanup_status}")
    if cleaned.cleanup_error:
        console.print(f"cleanup_error: {cleaned.cleanup_error}")


if __name__ == "__main__":
    app()
