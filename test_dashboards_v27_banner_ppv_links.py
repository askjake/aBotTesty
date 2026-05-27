#!/usr/bin/env python3
"""v27 smoke tests: PPV nav links and live-banner dashboard capture."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from dashboard_analytics import DashboardDataset


def test_ppv_links_present_in_main_pages() -> None:
    html_source = Path("merged_app.py").read_text(encoding="utf-8")
    # The app has multiple lightweight HTML pages; PPV should be discoverable from the major tabs/pages.
    assert "window.location='/ppv'" in html_source
    assert "<a href='/ppv'>PPV Lab</a>" in html_source
    assert "<a href=\"/ppv\"" in html_source or "href='/ppv'" in html_source
    assert html_source.count("/ppv") >= 10


def test_banner_capture_flows_to_channel_rows_catalog_and_superset() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "nav_graph.json").write_text(json.dumps({"nodes": {}, "edges": {}}), encoding="utf-8")
        (root / "crawler_brain.json").write_text(json.dumps({"channels": {"092-14": {"name_guess": "CAROL", "confidence": 0.9}}}), encoding="utf-8")
        (root / "learned_sequences.json").write_text(json.dumps({}), encoding="utf-8")
        (root / "unreachable_states.json").write_text(json.dumps({}), encoding="utf-8")
        (root / "sysdiag_bootstrap_history.json").write_text(json.dumps([]), encoding="utf-8")
        (root / "channel_surf_log.json").write_text(json.dumps({
            "schema": "channel_surf_log_v5_banner_validation",
            "observations": [{
                "ts": "2026-05-23T22:48:00+00:00",
                "channel": "092-14",
                "requested_channel": "092-14",
                "actual_channel_guess": "092-14",
                "ok": True,
                "tune_complete_s": 4.2,
                "live_health": {"active": True, "signal_class": "active_video"},
                "live_metadata": {
                    "screen_type": "live_banner",
                    "channel_number": "092-14",
                    "channel_code": "CAROL",
                    "channel_name": "CAROL",
                    "program_title": "The Carol Burnett Show",
                    "program_description": "Classic comedy variety episode.",
                    "program_time_range": "4:26p-5:35p",
                    "displayed_datetime_text": "Sat 5/23 4:48p",
                    "channel_logo_text": "CAROL",
                    "source": "live_banner_geometry",
                    "confidence": 0.94,
                    "banner_valid": True,
                    "banner_validation_score": 0.96,
                    "banner_validation_flags": [],
                },
                "best_metadata": {
                    "screen_type": "live_banner",
                    "channel_number": "092-14",
                    "channel_code": "CAROL",
                    "program_title": "The Carol Burnett Show",
                    "program_description": "Classic comedy variety episode.",
                    "displayed_datetime_text": "Sat 5/23 4:48p",
                    "source": "live_banner_geometry",
                    "confidence": 0.94,
                },
            }]
        }), encoding="utf-8")
        ds = DashboardDataset.load(root)
        rows = ds.channel_surf_rows()
        assert rows[0]["live_banner_valid"] is True
        assert rows[0]["live_banner_program_title"] == "The Carol Burnett Show"
        assert rows[0]["live_banner_channel_number"] == "092-14"
        assert rows[0]["live_banner_channel_code"] == "CAROL"
        catalog = ds.channel_catalog_rows()
        assert catalog[0]["channel_number"] == "092-14"
        assert catalog[0]["latest_live_banner_valid"] is True
        assert catalog[0]["latest_live_banner_program_title"] == "The Carol Burnett Show"
        assert catalog[0]["latest_live_banner_channel_number"] == "092-14"
        assert catalog[0]["latest_live_banner_channel_code"] == "CAROL"
        tables = ds.superset_tables()
        assert "live_banner_program_title" in tables["stb_channel_surf"][0]
        assert "latest_live_banner_program_title" in tables["stb_observed_channel_catalog"][0]


if __name__ == "__main__":
    test_ppv_links_present_in_main_pages()
    test_banner_capture_flows_to_channel_rows_catalog_and_superset()
    print("v27 banner/PPV dashboard tests passed")
