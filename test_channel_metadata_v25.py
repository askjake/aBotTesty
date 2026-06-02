#!/usr/bin/env python3
"""v25 hyphenated channel and live-banner validation tests."""
import json
import tempfile
from pathlib import Path

from channel_metadata import (
    _parse_channel_line,
    _parse_channel_number_only,
    choose_best_metadata,
    validate_live_banner_metadata,
)
from dashboard_analytics import DashboardDataset


def test_hyphenated_channel_line_parsing():
    assert _parse_channel_line("CAROL 092-14", requested=92) == ("092-14", "CAROL")
    assert _parse_channel_line("092-14 CAROL", requested=92) == ("092-14", "CAROL")
    assert _parse_channel_number_only("The Carol Burnett Show CAROL 092-14 46 mins left", requested=92) == "092-14"


def test_live_banner_validation_good_and_bad():
    good = {
        "screen_type": "live_banner",
        "source": "live_banner_geometry",
        "channel_number": "092-14",
        "channel_code": "CAROL",
        "program_title": "The Carol Burnett Show",
        "displayed_datetime_text": "Sat 5/23 4:48p",
        "program_time_range": "4:26p - 5:35p",
        "raw_regions": {
            "title": "The Carol Burnett Show",
            "channel_line": "CAROL 092-14",
            "progress": "46 mins left 4:26p 5:35p",
        },
    }
    val = validate_live_banner_metadata(good, "Live TV 46 mins left")
    assert val["valid"], val
    assert val["score"] >= 0.68

    bad = dict(good)
    bad.update({"program_title": "ee panes site", "channel_number": "", "channel_code": ""})
    bad["raw_regions"] = {"title": "ee panes site", "channel_line": ""}
    val2 = validate_live_banner_metadata(bad, "Live TV")
    assert not val2["valid"], val2
    assert "banner_missing_channel_number" in val2["flags"]


def test_choose_best_keeps_hyphenated_live_banner():
    best = choose_best_metadata([
        {
            "screen_type": "live_banner",
            "source": "live_banner_geometry",
            "channel_number": "092-14",
            "channel_code": "CAROL",
            "channel_name": "CAROL",
            "program_title": "The Carol Burnett Show",
            "displayed_datetime_text": "Sat 5/23 4:48p",
            "confidence": 0.88,
            "banner_valid": True,
            "banner_validation_score": 0.9,
            "quality_flags": [],
        }
    ])
    assert best["channel_number"] == "092-14"
    assert best["channel_code"] == "CAROL"
    assert best["program_title"] == "The Carol Burnett Show"


def test_dashboard_banner_validation_fields():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "channel_surf_log.json").write_text(json.dumps({
            "schema": "channel_surf_log_v5_banner_validation",
            "observations": [
                {
                    "channel": 92,
                    "requested_channel": 92,
                    "actual_channel_guess": "092-14",
                    "actual_channel_source": "best_metadata.channel_number",
                    "ts": "2026-05-23T22:48:00+00:00",
                    "ok": True,
                    "tune_complete_s": 2.8,
                    "live_health": {"active": True, "signal_class": "active_video"},
                    "live_metadata": {
                        "screen_type": "live_banner",
                        "channel_number": "092-14",
                        "channel_code": "CAROL",
                        "channel_name": "CAROL",
                        "program_title": "The Carol Burnett Show",
                        "program_description": "",
                        "displayed_datetime_text": "Sat 5/23 4:48p",
                        "confidence": 0.88,
                        "source": "live_banner_geometry",
                        "banner_valid": True,
                        "banner_validation_score": 0.91,
                        "banner_validation_flags": [],
                    },
                    "best_metadata": {
                        "screen_type": "live_banner",
                        "channel_number": "092-14",
                        "channel_code": "CAROL",
                        "program_title": "The Carol Burnett Show",
                        "displayed_datetime_text": "Sat 5/23 4:48p",
                        "confidence": 0.9,
                        "source": "merged_channel_metadata_v25_trusted",
                    },
                    "warning_flags": [],
                }
            ],
        }), encoding="utf-8")
        (root / "crawler_brain.json").write_text("{}", encoding="utf-8")
        ds = DashboardDataset.load(root)
        rows = ds.channel_surf_rows()
        assert rows[0]["actual_channel_guess"] == "092-14"
        assert rows[0]["live_banner_valid"] is True
        catalog = ds.channel_catalog_rows()
        assert catalog[0]["channel_number"] == "092-14"
        assert catalog[0]["latest_live_banner_valid"] is True
        assert catalog[0]["banner_valid_pct"] == 100.0
        assert ds.channel_surf_summary()["banner_valid_pct"] == 100.0


if __name__ == "__main__":
    test_hyphenated_channel_line_parsing()
    test_live_banner_validation_good_and_bad()
    test_choose_best_keeps_hyphenated_live_banner()
    test_dashboard_banner_validation_fields()
    print("CHANNEL_METADATA_V25_OK")
