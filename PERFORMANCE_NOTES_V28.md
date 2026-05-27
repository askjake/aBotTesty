# v28 UI-Friendly Crawler Performance Notes

## Problem investigated

When autonomous crawl starts, the `/monitor` UI can become laggy because several expensive tasks happen synchronously in the crawler hot path:

1. Every state match scanned the full graph with rich OCR/focus/text similarity.
2. Large `nav_graph.json` and `crawler_brain.json` files were written repeatedly during the crawl loop.
3. Pretty-printed JSON made those writes much larger and slower.
4. Sequence mining ran often while the crawler was actively pressing buttons.
5. Capture JPEG encoding ran very frequently for the MJPEG monitor stream.
6. Deep OCR/focus perception still happened at checkpoints, which is necessary, but it should not also force excessive disk and graph work.

## v28 fixes

- Added compact JSON saves for graph/brain files.
- Batched hot-loop graph/brain saves with configurable action/time thresholds.
- Added graph candidate prefiltering so large graphs compare a shortlist with the expensive similarity model.
- Increased default deep OCR spacing in balanced mode.
- Made sequence mining less frequent by default.
- Reduced default MJPEG stream frame rate to 10 FPS.
- Added capture JPEG encode throttling while preserving raw latest-frame access for the crawler.
- Added crawler performance fields to `/api/crawl/status`.

## New config knobs

```json
{
  "capture_jpeg_every_n_frames": 2,
  "video_stream_fps": 10,
  "crawler_ui_friendly_mode": true,
  "crawler_compact_json_saves": true,
  "crawler_hot_loop_save_every_n_actions": 6,
  "crawler_hot_loop_save_min_interval_s": 8.0,
  "crawler_sequence_mining_every_n_steps": 24,
  "crawler_graph_match_candidate_limit": 240,
  "crawler_timing_poll_s": 0.28,
  "crawler_deep_ocr_every_n_steps": 10
}
```

## Expected effect

The crawler still learns before/action/after transitions and still performs deep OCR checkpoints, but it stops doing the most expensive disk and full-graph work on every tiny step. The monitor stream should remain more responsive during crawl runs.
