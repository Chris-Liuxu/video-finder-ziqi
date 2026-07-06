# Video Finder

CLI tool for finding likely original YouTube videos from a face-tampered clip.

## Architecture

Video Finder is a small Python CLI built around a LangGraph workflow. Each node performs one step and writes its intermediate artifacts to `.video_finder_runs/<run_id>/` when possible, so debug runs can be inspected after completion.

Main components:

- `cli.py`: Typer CLI entrypoint.
- `graph.py`: LangGraph workflow definition.
- `nodes/`: workflow steps such as frame extraction, OCR, text search, image search, candidate collection, metadata enrichment, ranking, and cleanup.
- `services/`: integrations for PaddleOCR, ImgBB, SerpAPI Google Lens, GLM, Google Custom Search, YouTube Data API, and image comparison.
- `models.py`: shared Pydantic state and result models.

External services:

- ImgBB hosts the selected query frame for Google Lens and auto-expires it after 1 day.
- SerpAPI Google Lens finds visually similar web and YouTube results.
- GLM-4.7-Flash optionally turns OCR/context into one text-search query.
- Google Custom Search optionally finds extra YouTube candidates from OCR-derived text.
- YouTube Data API enriches candidate metadata and official thumbnails.

## Workflow

1. Extract frames from the input video.
2. Run PaddleOCR across extracted frames.
3. Select the best query frame using OCR density and image sharpness.
4. Optionally build an OCR/context search prompt and call GLM-4.7-Flash.
5. Optionally call Google Custom Search once and extract Top 3 YouTube links.
6. Upload the selected query frame to ImgBB, unless `--lens-json` is used.
7. Call SerpAPI Google Lens, or replay a saved Lens JSON file.
8. Merge YouTube candidates from Google Custom Search and Google Lens.
9. Enrich candidates with YouTube Data API metadata and thumbnails.
10. Compare the selected input frame with candidate thumbnails.
11. Rank candidates and write `top3_video_links.txt`.
12. Record upload cleanup/expiration status.

Use `--skip-text-search` to disable steps 4-5.

## Install With Docker

Install Docker Desktop or another Docker runtime first.

If you received a packaged Docker image archive, load it:

```bash
docker load -i video-finder-ziqi.tar.gz
```

If you are building from this repository instead:

```bash
docker build -t video-finder-ziqi:latest .
```

Create a `.env` file in the project root before running the container. Docker loads these values with `--env-file .env`; API keys are not baked into the image.

```env
SERPAPI_API_KEY=
IMGBB_API_KEY=
YOUTUBE_API_KEY=
GLM_API_KEY=
GOOGLE_CUSTOM_SEARCH_API_KEY=
GOOGLE_CUSTOM_SEARCH_CX=
IMGBB_EXPIRATION_SECONDS=86400
OCR_BACKEND=paddle
OCR_LANGUAGES=all
```

Prepare local input and output directories:

```bash
mkdir -p input_video .video_finder_runs
```

Run the full workflow:

```bash
docker run --rm \
  --env-file .env \
  -v "$(pwd)/input_video:/data/input_video:ro" \
  -v "$(pwd)/.video_finder_runs:/app/.video_finder_runs" \
  video-finder-ziqi:latest \
  find /data/input_video/id0_id1_0005.mp4 \
  --ocr-backend paddle \
  --frame-interval 3 \
  --top-k 3 \
  --debug
```

Disable the optional OCR-text + GLM + Google Custom Search workflow:

```bash
docker run --rm \
  --env-file .env \
  -v "$(pwd)/input_video:/data/input_video:ro" \
  -v "$(pwd)/.video_finder_runs:/app/.video_finder_runs" \
  video-finder-ziqi:latest \
  find /data/input_video/id0_id1_0005.mp4 \
  --skip-text-search \
  --ocr-backend paddle \
  --frame-interval 3 \
  --top-k 3 \
  --debug
```

Run with a saved Google Lens JSON file:

```bash
docker run --rm \
  --env-file .env \
  -v "$(pwd)/input_video:/data/input_video:ro" \
  -v "$(pwd)/tests:/data/tests:ro" \
  -v "$(pwd)/.video_finder_runs:/app/.video_finder_runs" \
  video-finder-ziqi:latest \
  find /data/input_video/id0_id1_0005.mp4 \
  --lens-json /data/tests/google_lens_api_return.json \
  --ocr-backend paddle \
  --frame-interval 3 \
  --top-k 3 \
  --debug
```

Run the uploader smoke test:

```bash
docker run --rm \
  --env-file .env \
  -v "$(pwd)/frames:/data/frames:ro" \
  video-finder-ziqi:latest \
  test-uploader /data/frames/query.jpg --uploader imgbb
```

The container writes run artifacts to `/app/.video_finder_runs`. The examples above mount that path to local `.video_finder_runs/`, so outputs remain available after the container exits.

## Install Locally

```bash
uv sync --extra dev --extra ocr
```

## Required `.env`

```env
SERPAPI_API_KEY=
IMGBB_API_KEY=
YOUTUBE_API_KEY=
GLM_API_KEY=
GOOGLE_CUSTOM_SEARCH_API_KEY=
GOOGLE_CUSTOM_SEARCH_CX=
IMGBB_EXPIRATION_SECONDS=86400
OCR_BACKEND=paddle
OCR_LANGUAGES=all
```

## Run

```bash
uv run video-finder find ./input_video/id0_id1_0005.mp4 --ocr-backend paddle --frame-interval 3 --top-k 3 --debug
```

Disable the optional OCR-text + GLM + Google Custom Search workflow:

```bash
uv run video-finder find ./input_video/id0_id1_0005.mp4 --skip-text-search --ocr-backend paddle --frame-interval 3 --top-k 3 --debug
```

<!-- ## Run With Saved Google Lens JSON

This skips image upload and SerpAPI Lens calls, but still runs OCR, optional GLM text-search planning, optional Google Custom Search, YouTube Data API metadata, thumbnail comparison, and ranking.

```bash
uv run video-finder find ./input_video/id0_id1_0005.mp4 --lens-json ./tests/google_lens_api_return.json --ocr-backend paddle --frame-interval 3 --top-k 3 --debug
``` -->

## Run Artifacts

Each run writes artifacts under `.video_finder_runs/<run_id>/`:

- `frames/`: extracted input frames
- `frames_manifest.json`: extracted frame metadata
- `ocr_results.json`: structured PaddleOCR results
- `ocr_text.txt`: readable OCR text summary
- `selected_frame.json`: selected query frame metadata
- `text_search_context.json`: OCR key text and selected-frame context for LLM
- `llm_search_request.json`: GLM request payload
- `llm_search_response.json`: GLM successful response, if any
- `llm_search_attempts.json`: GLM retry log
- `text_search_query.txt`: final query sent to Google Custom Search
- `google_custom_search_api_return.json`: raw Google Custom Search response
- `google_custom_search_top3_links.txt`: YouTube links extracted from text search
- `upload_result.json`: ImgBB upload result
- `google_lens_api_return.json`: raw Google Lens API response
- `youtube_candidates_initial.json`: merged YouTube candidates from Lens and text search
- `youtube_candidates_enriched.json`: candidates after YouTube Data API enrichment
- `thumbnails/`: downloaded YouTube thumbnails used for comparison
- `ranked_candidates.json`: final scored candidate details
- `top3_video_links.txt`: final Top 3 YouTube links
- `cleanup_upload_result.json`: uploaded image cleanup/expiration status

`Reason` in CLI output includes `thumbnail=` for input-frame vs YouTube-thumbnail similarity and `metadata=` for YouTube Data API metadata availability.
