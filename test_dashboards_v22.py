#!/usr/bin/env python3
import json
import tempfile
import zipfile
from pathlib import Path

from dashboard_analytics import DashboardDataset


def main():
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        obs = {
            "schema": "channel_surf_log_v3_channel_metadata",
            "observations": [
                {
                    "channel": 111,
                    "requested_channel": 111,
                    "actual_channel_guess": "111",
                    "ts": "2026-05-23T18:36:00+00:00",
                    "ok": True,
                    "tune_complete_s": 2.1,
                    "live_health": {"active": True, "signal_class": "active_video"},
                    "live_time_context": {"found": True, "displayed": "Sat 5/23 12:36p", "actual_iso": "2026-05-23T18:36:00+00:00", "drift_minutes": 0, "source": "live_header", "confidence": 0.95, "flags": []},
                    "live_metadata": {"screen_type": "live_banner", "channel_number": "111", "channel_code": "MAGN", "channel_name": "MAGN", "program_title": "Beachfront Bargain Hunt", "program_description": "Renovations on First Home", "displayed_datetime_text": "Sat 5/23 12:36p", "confidence": 0.9, "source": "live_banner_geometry"},
                    "best_metadata": {"screen_type": "live_banner", "channel_number": "111", "channel_code": "MAGN", "channel_name": "MAGN", "program_title": "Beachfront Bargain Hunt", "program_description": "Renovations on First Home", "displayed_datetime_text": "Sat 5/23 12:36p", "confidence": 0.9, "source": "merged_channel_metadata"},
                },
                {
                    "channel": 114,
                    "requested_channel": 114,
                    "actual_channel_guess": "114",
                    "ts": "2026-05-23T18:39:00+00:00",
                    "ok": True,
                    "tune_complete_s": 1.9,
                    "live_health": {"active": True, "signal_class": "active_static_ui"},
                    "guide_time_context": {"found": True, "displayed": "Sat 5/23 12:39p", "actual_iso": "2026-05-23T18:39:00+00:00", "drift_minutes": 0, "source": "guide_header", "confidence": 0.92, "flags": []},
                    "guide_metadata": {"screen_type": "guide", "channel_number": "114", "channel_code": "E!", "channel_name": "E!", "program_title": "How I Met Your Mother", "program_description": "Best Prom Ever", "displayed_datetime_text": "Sat 5/23 12:39p", "confidence": 0.88, "source": "guide_focus_row_and_detail_panel"},
                    "best_metadata": {"screen_type": "guide", "channel_number": "114", "channel_code": "E!", "channel_name": "E!", "program_title": "How I Met Your Mother", "program_description": "Best Prom Ever", "displayed_datetime_text": "Sat 5/23 12:39p", "confidence": 0.88, "source": "merged_channel_metadata"},
                },
            ],
        }
        (d / "channel_surf_log.json").write_text(json.dumps(obs), encoding="utf-8")
        (d / "crawler_brain.json").write_text(json.dumps({"channels": {"111": {"name_guess": "MAGN", "symbols": ["Magnolia"], "confidence": 0.8}}}), encoding="utf-8")
        ds = DashboardDataset.load(d)
        rows = ds.channel_surf_rows()
        assert rows and rows[0]["best_displayed_datetime"]
        catalog = ds.channel_catalog_rows()
        assert len(catalog) == 2, catalog
        c111 = next(r for r in catalog if r["channel_number"] == "111")
        assert c111["observed_channel_label"] == "111 MAGN"
        assert c111["latest_program_title"] == "Beachfront Bargain Hunt"
        assert c111["latest_displayed_time"] == "Sat 5/23 12:36p"
        assert c111["learned_channel_name"] == "MAGN"
        times = ds.observed_stb_time_rows()
        assert len(times) == 2
        ex = ds.executive()
        eng = ds.engineering()
        assert ex["headline"]["observed_channels"] == 2
        assert ex["headline"]["observed_stb_time_reads"] == 2
        assert ex["channel_catalog"] and eng["observed_stb_times"]
        tables = ds.superset_tables()
        assert "stb_observed_channel_catalog" in tables
        assert "stb_observed_stb_times" in tables
        z = ds.export_zip_bytes()
        with zipfile.ZipFile(Path(td) / "out.zip", "w") as _:
            pass
        assert z[:2] == b"PK"
        with zipfile.ZipFile(__import__('io').BytesIO(z)) as zf:
            names = set(zf.namelist())
            assert "datasets/stb_observed_channel_catalog.csv" in names
            assert "datasets/stb_observed_stb_times.csv" in names
            sql = zf.read("superset_sql_views.sql").decode()
            assert "v_stb_observed_channel_latest" in sql
    print("dashboard v22 channel catalog ok")


if __name__ == "__main__":
    main()
