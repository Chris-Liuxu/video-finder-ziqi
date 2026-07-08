# Video Finder

Video Finder 是一个命令行工具：输入一段被换脸或人脸篡改的视频片段，返回最可能对应的 YouTube 原视频 Top 3 链接。

项目不做人脸识别，不保存或比对人脸特征。检索依据来自画面文字、频道/节目视觉线索、Google Lens 结果、YouTube 官方元数据和缩略图相似度。

## 使用方法

### 1. 配置环境变量

在项目根目录创建 `.env`：

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

说明：

- `GLM_API_KEY` 用于调用 GLM-4.7-Flash 组织 Google Custom Search 查询词。
- `GOOGLE_CUSTOM_SEARCH_API_KEY` 和 `GOOGLE_CUSTOM_SEARCH_CX` 用于可选的文字搜索分支。
- `SERPAPI_API_KEY` 用于 Google Lens。
- `IMGBB_API_KEY` 用于临时托管查询帧，默认 1 天后过期。
- `YOUTUBE_API_KEY` 用于补全候选视频标题、缩略图等官方元数据。

### 2. 本地安装

```bash
uv sync --extra dev --extra ocr
```

### 3. 运行完整流程

```bash
uv run video-finder find ./input_video/id0_id1_0005.mp4 --ocr-backend paddle --frame-interval 3 --top-k 3 --debug
```

跳过 OCR 文本 + GLM + Google Custom Search 分支：

```bash
uv run video-finder find ./input_video/id0_id1_0005.mp4 --skip-text-search --ocr-backend paddle --frame-interval 3 --top-k 3 --debug
```

使用已保存的 Google Lens JSON 调试，避免重复调用上传和 SerpAPI：

```bash
uv run video-finder find ./input_video/id0_id1_0005.mp4 --lens-json ./tests/google_lens_api_return.json --ocr-backend paddle --frame-interval 3 --top-k 3 --debug
```

### 4. Docker 运行

构建镜像：

```bash
docker build -t video-finder-ziqi:latest .
```

运行完整流程：

```bash
mkdir -p input_video .video_finder_runs

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

如果收到已打包镜像，也可以直接加载：

```bash
docker load -i video-finder-ziqi.tar.gz
```

## 项目架构

项目主体是一个 Python CLI，使用 Typer 暴露命令，使用 LangGraph 编排工作流。

- `src/video_finder/cli.py`：命令行入口，负责解析参数、创建运行目录、打印 Top 3 结果。
- `src/video_finder/graph.py`：LangGraph 工作流定义。
- `src/video_finder/nodes/`：每个节点对应一个处理步骤，例如抽帧、OCR、上传、搜索、候选合并、排序。
- `src/video_finder/services/`：外部服务和算法封装，包括 PaddleOCR、ImgBB、SerpAPI Google Lens、GLM、Google Custom Search、YouTube Data API、缩略图比对。
- `src/video_finder/models.py`：工作流状态和结果模型。
- `.video_finder_runs/<run_id>/`：每次运行的中间产物目录，便于复盘和调试。

外部服务职责：

- PaddleOCR：识别帧内字幕、台标、下三分之一标题等文字。
- GLM-4.7-Flash：根据 OCR 与选中帧上下文组织一次 Google Custom Search 查询词。
- Google Custom Search：从文字线索中补充 YouTube 候选链接，每次运行只调用一次。
- ImgBB：临时托管查询帧，供 Google Lens 访问。
- SerpAPI Google Lens：根据查询帧做视觉搜索。
- YouTube Data API：补全视频标题、缩略图等官方元数据。

## Workflow 编排

```text
extract_frames
  -> ocr_frames
  -> select_query_frame
  -> text_search
  -> upload_image
  -> search_lens
  -> collect_youtube
  -> enrich_youtube_metadata
  -> rank_candidates
  -> cleanup_uploaded_image
```

步骤说明：

1. 从输入视频抽帧，保存 `frames/` 和 `frames_manifest.json`。
2. 使用 PaddleOCR 做全语种 OCR，保存 `ocr_results.json` 和 `ocr_text.txt`。
3. 根据 OCR 密度和清晰度选择查询帧，保存 `selected_frame.json`。
4. 默认启用文字搜索：基于 OCR 关键文本和选中帧上下文保存 `text_search_context.json`。
5. 调用 GLM-4.7-Flash 生成 Google Custom Search 查询词，最多重试 5 次，并保存请求、响应、重试记录和查询文本。
6. 调用一次 Google Custom Search API，保存 `google_custom_search_api_return.json` 和 `google_custom_search_top3_links.txt`。
7. 上传查询帧到 ImgBB，保存 `upload_result.json`。
8. 调用 SerpAPI Google Lens，保存 `google_lens_api_return.json`。
9. 合并 Google Custom Search Top 3 和 Google Lens 中的 YouTube 候选，保存 `youtube_candidates_initial.json`。
10. 使用 YouTube Data API 增强候选元数据，保存 `youtube_candidates_enriched.json`。
11. 下载候选视频缩略图到 `thumbnails/`，与输入关键帧做相似度比对。
12. 排序并保存 `ranked_candidates.json` 和 `top3_video_links.txt`。
13. 清理或记录上传图片过期状态，保存 `cleanup_upload_result.json`。

`--skip-text-search` 会跳过第 4/5/6 步，并写入跳过状态文件，便于确认本次运行路径。

## 运行产物

每次运行都会写入 `.video_finder_runs/<run_id>/`：

- `frames/`：抽取的视频帧。
- `frames_manifest.json`：帧路径、时间戳等元数据。
- `ocr_results.json`：结构化 OCR 结果。
- `ocr_text.txt`：便于人工查看的 OCR 文本摘要。
- `selected_frame.json`：被选为查询帧的帧信息。
- `text_search_context.json`：提供给大模型的 OCR 关键文本和帧上下文。
- `llm_search_request.json`、`llm_search_response.json`、`llm_search_attempts.json`：大模型请求、响应和重试记录。
- `text_search_query.txt`：最终送入 Google Custom Search 的查询词。
- `google_custom_search_api_return.json`、`google_custom_search_top3_links.txt`：文字搜索返回和 Top 3 链接。
- `upload_result.json`：查询帧上传结果。
- `google_lens_api_return.json`：Google Lens 原始返回。
- `youtube_candidates_initial.json`：合并后的候选 YouTube 链接。
- `youtube_candidates_enriched.json`：补全 YouTube 元数据后的候选。
- `thumbnails/`：下载的候选视频缩略图。
- `ranked_candidates.json`：最终候选分数、原因、缩略图相似度和元数据命中情况。
- `top3_video_links.txt`：最终 Top 3 YouTube 链接。
- `cleanup_upload_result.json`：上传图片清理或过期记录。

## 静态 Demo

下面的 demo 来自一次已保存运行：

```text
.video_finder_runs/3e95a0c17fc54c3c89d4eaaabbb890ce/
```

输入片段：`./input_video/id0_id1_0005.mp4`

### 查询帧

工作流选择了第 0 帧，时间戳 `0.00s`，清晰度分数 `73.34`。

![查询帧](docs/demo/query_frame.jpg)

### OCR 关键文本

PaddleOCR 在查询帧和相邻帧中提取到的高价值文本包括：

```text
BREAKING NEWS
BREAKINGNEWS
अलगाववािद्यों
Harnaranlaal!
16:30
```

这些文本来自画面中的新闻横幅、字幕和时间等视觉线索，而不是人脸识别结果。

### 大模型组织后的搜索关键词

GLM-4.7-Flash 根据 OCR 文本和选中帧上下文组织出的搜索关键词：

```text
BREAKING NEWS "अलगाववािद्यों" "Harnaranlaal" site:youtube.com
```

该关键词用于 Google Custom Search 分支；同时 Google Lens 分支继续基于查询帧做视觉检索。

### 原视频候选对比

| 排名 | 查询帧 | 候选原视频缩略图 | YouTube 链接 | 标题 | 分数 |
| --- | --- | --- | --- | --- | --- |
| 1 | ![查询帧](docs/demo/query_frame.jpg) | ![Top 1 缩略图](docs/demo/top1_pqXpo1epTyA.jpg) | <https://www.youtube.com/watch?v=pqXpo1epTyA> | Interview: Aamir Khan & Vijay Krishna Acharya on 'Dhoom 3' | `0.5985` |
| 2 | ![查询帧](docs/demo/query_frame.jpg) | ![Top 2 缩略图](docs/demo/top2_wRosIW6ZTT0.jpg) | <https://www.youtube.com/watch?v=wRosIW6ZTT0> | Best City Awards 2014: Mumbai is Aamir Khan's best city | `0.5457` |
| 3 | ![查询帧](docs/demo/query_frame.jpg) | ![Top 3 缩略图](docs/demo/top3_gu-fbbl_xeA.jpg) | <https://www.youtube.com/watch?v=gu-fbbl_xeA> | Seedhi Baat - Seedhi Baat - Seedhi Baat: Salman and Sohail Khan | `0.3293` |

最终写入 `top3_video_links.txt`：

```text
https://www.youtube.com/watch?v=pqXpo1epTyA
https://www.youtube.com/watch?v=wRosIW6ZTT0
https://www.youtube.com/watch?v=gu-fbbl_xeA
```

## 约束

- 不做人脸识别，不保存或比对人脸特征。
- API key 只从环境变量或 `.env` 读取。
- Google Custom Search 每次运行只调用一次。
- 第 4/5/6 步由 `--text-search/--skip-text-search` 控制，默认启用。
- GLM-4.7-Flash 最多重试 5 次；仍失败则跳过文字搜索。
- YouTube Data API 不提供视频文件下载流，本项目只用它获取官方元数据和缩略图。
