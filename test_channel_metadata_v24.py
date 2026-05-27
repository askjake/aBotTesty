#!/usr/bin/env python3
"""v24 channel metadata trust-gate tests."""
import json
import tempfile
from pathlib import Path

from channel_metadata import (
    choose_best_metadata,
    is_plausible_program_title,
    sanitize_program_title,
)
from dashboard_analytics import DashboardDataset


def test_noise_gate():
    assert not is_plausible_program_title("ee panes site")
    assert not is_plausible_program_title("fey § fey § y bs fey § Ps premiere movie")
    assert not sanitize_program_title("MOUSE MUTILETS")
    assert is_plausible_program_title("The Office")
    assert is_plausible_program_title("How I Met Your Mother")


def test_choose_best_rejects_noisy_high_confidence_title():
    metas = [
        {
            "screen_type": "live_banner",
            "channel_number": "107",
            "channel_code": "CMDY",
            "channel_name": "CMDY",
            "program_title": "The Office",
            "displayed_datetime_text": "Sat 5/23 | 2:37p",
            "confidence": 0.80,
            "source": "live_banner_geometry",
            "quality_flags": [],
        },
        {
            "screen_type": "info",
            "channel_number": "107",
            "channel_code": "CMDY",
            "program_title": "ee panes site",
            "confidence": 0.98,
            "source": "info_screen_geometry",
            "quality_flags": [],
        },
        {
            "screen_type": "guide",
            "channel_number": "107",
            "channel_code": "CMDY",
            "program_title": "The Office",
            "confidence": 0.75,
            "source": "guide_focus_row_and_detail_panel",
            "quality_flags": [],
        },
    ]
    best = choose_best_metadata(metas)
    assert best["channel_number"] == "107"
    assert best["channel_code"] == "CMDY"
    assert best["program_title"] == "The Office"
    assert "rejected_noisy_program_title" in best["quality_flags"]


def test_dashboard_quarantines_legacy_blob_program_guess():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "channel_surf_log.json").write_text(json.dumps({
            "schema": "channel_surf_log_v2_time_and_step",
            "observations": [{
                "channel": 107,
                "ts": "2026-05-23T18:33:46+00:00",
                "ok": True,
                "actual_channel_guess": "107",
                "program_guess": "ee panes site",
                "channel_name_guess": "Sat 23 12 33p TV The",
                "live_health": {"active": True, "signal_class": "active_video"},
                "warning_flags": [],
            }]
        }), encoding="utf-8")
        (root / "crawler_brain.json").write_text("{}", encoding="utf-8")
        ds = DashboardDataset.load(root)
        rows = ds.channel_catalog_rows()
        row = rows[0]
        assert row["channel_number"] == "107"
        assert row["latest_program_title"] == ""
        assert "dashboard_rejected_legacy_program_guess" in row["warning_flags"]


if __name__ == "__main__":
    test_noise_gate()
    test_choose_best_rejects_noisy_high_confidence_title()
    test_dashboard_quarantines_legacy_blob_program_guess()
    print("CHANNEL_METADATA_V24_OK")
