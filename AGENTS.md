# Video Finder

## 目标

输入一段被换脸或人脸篡改的视频片段，返回最可能对应的 YouTube 原视频 Top 3 链接。

## 当前工作流

1. 抽帧并保存 `frames/`、`frames_manifest.json`
2. 使用 PaddleOCR 做全语种 OCR，保存 `ocr_results.json`、`ocr_text.txt`
3. 选择查询帧，保存 `selected_frame.json`
4. 可选：基于 OCR 关键文本和选中帧环境信息构造 `text_search_context.json`
5. 可选：调用 GLM-4.7-Flash 生成一次 Google Custom Search 查询；最多重试 5 次，保存请求、响应、重试记录和查询文本
6. 可选：调用一次 Google Custom Search API，保存 `google_custom_search_api_return.json` 和 `google_custom_search_top3_links.txt`
7. 上传查询帧到 ImgBB，图片 1 天后自动过期，保存 `upload_result.json`
8. 调用 SerpAPI Google Lens，保存 `google_lens_api_return.json`
9. 合并 Google Custom Search Top 3 和 Google Lens 中的 YouTube 候选，保存 `youtube_candidates_initial.json`
10. 使用 YouTube Data API 增强候选元数据，保存 `youtube_candidates_enriched.json`
11. 下载 YouTube 缩略图到 `thumbnails/`，与输入关键帧做相似度比对
12. 排序并保存 `ranked_candidates.json`、`top3_video_links.txt`
13. 清理或记录上传图片过期状态，保存 `cleanup_upload_result.json`

## 手动运行

```bash
uv run video-finder find ./input_video/id0_id1_0005.mp4 --ocr-backend paddle --frame-interval 3 --top-k 3 --debug
```

跳过第 4/5/6 步：

```bash
uv run video-finder find ./input_video/id0_id1_0005.mp4 --skip-text-search --ocr-backend paddle --frame-interval 3 --top-k 3 --debug
```

## 必要配置

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

## 约束

- 不做人脸识别，不保存或比对人脸特征。
- API key 只从环境变量或 `.env` 读取。
- Google Custom Search 每次运行只调用一次。
- 第 4/5/6 步由 `--text-search/--skip-text-search` 控制，默认启用。
- GLM-4.7-Flash 最多重试 5 次；仍失败则跳过文字搜索。
- YouTube Data API 不提供视频文件下载流，本项目只用它获取官方元数据和缩略图。
