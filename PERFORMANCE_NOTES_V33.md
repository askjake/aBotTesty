# v33 Intelligence Console / SGS Path Cleanup

## Why the intelligence page could hang the app

The intelligence page was polling `/api/crawl/map` every few seconds and the endpoint returned the entire graph: all nodes, all edges, transition cards, screenshots, OCR/focus payloads, timing summaries, sequence stats, and persistence stats. Once the graph reached thousands of nodes, the browser and Flask worker could both get pinned rendering/serializing a giant SVG payload.

## Changes

- `/api/crawl/map` now returns a UI-friendly slice by default.
- Default slice: 240 states / 420 edges / no transition cards.
- Transition cards load only when the Before/Button/After tab is opened.
- The browser avoids overlapping `/api/crawl/map` requests.
- The map does not refresh while the tab is hidden.
- Polling cadence is relaxed to reduce app-wide pressure.
- The map payload now reports `map_slice`, `visible_node_count`, and `visible_edge_count` so the UI can explain that it is showing a representative view of the full graph.

## SGS log path cleanup

The log line showing an old v9 `.venv` path came from `sys.executable`. That means the Flask process itself was launched by that old interpreter. It was not a hard-coded v9 file path in the v32 code. v33 now prefers this bundle's local `.venv` Python for the SGS helper subprocess and logs a warning when the app interpreter is outside the current bundle.
