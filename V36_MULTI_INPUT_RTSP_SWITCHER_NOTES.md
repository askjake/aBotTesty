# v36 Multi-Input RTSP Switcher

This feature branch is reserved for the v36 multi-input/RTSP capture switcher integration generated from the latest app bundle.

## Intended changed files

- `capture_monitor.py`
- `merged_app.py`
- `config.json`
- `VERSION.txt`
- `test_capture_inputs_v36.py`
- `V36_MULTI_INPUT_RTSP_SWITCHER_NOTES.md`
- `V36_VALIDATION_REPORT.md`

## Feature summary

v36 adds runtime switching between local capture devices and RTSP/HTTP stream inputs, including Hi3520D-style RTSP probing when only a base encoder URL is provided.

The GUI Video Input selector is designed for these app areas:

- `/monitor`
- `/intelligence` / `/crawl`
- `/teach`
- `/channel_surf`
- `/ppv`
- `/human`

New API routes:

- `GET /api/capture/inputs`
- `POST /api/capture/select`
- `GET|POST /api/capture/scan`

Config/env additions:

- `MERGED_CAPTURE_DEVICE` now accepts either a numeric device index or a stream URL.
- `MERGED_RTSP_URL`
- `MERGED_CAPTURE_BACKEND`

## Validation previously run on the generated v36 bundle

```text
python3 -m py_compile merged_app.py capture_monitor.py auto_crawler.py channel_metadata.py channel_surf_agent.py sequence_learner.py dashboard_analytics.py
python3 test_capture_inputs_v36.py
python3 test_guide_self_correction_v34.py
python3 test_dashboards_v35_effectiveness.py
python3 test_performance_v28.py
python3 test_demonstration_practice_v32.py
python3 test_channel_metadata_v25.py
python3 test_dashboards_v16.py
python3 test_dashboards_v22.py
python3 test_dashboards_v27_banner_ppv_links.py
```

Pass markers included:

```text
CAPTURE_INPUTS_V36_OK
guide self-correction v34: OK
dashboard v35 effectiveness ok
PERFORMANCE_V28_OK
demonstration practice v32 synthetic test: OK
CHANNEL_METADATA_V25_OK
v27 banner/PPV dashboard tests passed
```
