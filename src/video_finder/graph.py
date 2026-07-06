from __future__ import annotations

from langgraph.graph import END, StateGraph

from video_finder.models import VideoFinderState
from video_finder.nodes.cleanup_uploaded_image import cleanup_uploaded_image
from video_finder.nodes.collect_youtube import collect_youtube
from video_finder.nodes.extract_frames import extract_frames
from video_finder.nodes.enrich_youtube_metadata import enrich_youtube_metadata
from video_finder.nodes.ocr_frames import ocr_frames
from video_finder.nodes.rank_candidates import rank_candidates
from video_finder.nodes.search_lens import search_lens
from video_finder.nodes.select_query_frame import select_query_frame
from video_finder.nodes.text_search import text_search
from video_finder.nodes.upload_image import upload_image


def build_graph():
    graph = StateGraph(VideoFinderState)
    graph.add_node("extract_frames", extract_frames)
    graph.add_node("ocr_frames", ocr_frames)
    graph.add_node("select_query_frame", select_query_frame)
    graph.add_node("text_search", text_search)
    graph.add_node("upload_image", upload_image)
    graph.add_node("search_lens", search_lens)
    graph.add_node("collect_youtube", collect_youtube)
    graph.add_node("enrich_youtube_metadata", enrich_youtube_metadata)
    graph.add_node("rank_candidates", rank_candidates)
    graph.add_node("cleanup_uploaded_image", cleanup_uploaded_image)

    graph.set_entry_point("extract_frames")
    graph.add_edge("extract_frames", "ocr_frames")
    graph.add_edge("ocr_frames", "select_query_frame")
    graph.add_edge("select_query_frame", "text_search")
    graph.add_edge("text_search", "upload_image")
    graph.add_edge("upload_image", "search_lens")
    graph.add_edge("search_lens", "collect_youtube")
    graph.add_edge("collect_youtube", "enrich_youtube_metadata")
    graph.add_edge("enrich_youtube_metadata", "rank_candidates")
    graph.add_edge("rank_candidates", "cleanup_uploaded_image")
    graph.add_edge("cleanup_uploaded_image", END)
    return graph.compile()
