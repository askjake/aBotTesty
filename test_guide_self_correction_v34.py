#!/usr/bin/env python3
"""v34 regression tests: guide-grid intelligence and raw channel self-correction."""
from pathlib import Path
from tempfile import TemporaryDirectory

import cv2

from auto_crawler import CrawlerBrain
from channel_metadata import extract_guide_grid
from jamboree.commands import get_sgs_codes


def load_key_helpers():
    src = Path("merged_app.py").read_text(encoding="utf-8")
    start = src.index("KEY_ALIASES =")
    end = src.index("\ndef press_button")
    ns = {"List": list}
    exec(src[start:end], ns)
    return ns["key_sequence_for"]


def test_raw_numeric_channel_expands_to_digit_sequence():
    key_sequence_for = load_key_helpers()
    assert key_sequence_for("250") == ["2", "5", "0", "select"]
    assert key_sequence_for("CH_206") == ["2", "0", "6", "select"]
    assert key_sequence_for("7") == ["7"]
    # The SGS bridge knows single digit buttons, not synthetic multi-digit button IDs.
    assert get_sgs_codes("2", 120)
    assert get_sgs_codes("5", 120)
    assert get_sgs_codes("0", 120)
    assert get_sgs_codes("250", 120) is None


def test_guide_grid_extracts_rows_selected_program_and_icons():
    img = cv2.imread("docs/v34_guide_reference.png")
    assert img is not None, "reference guide image missing"
    guide = extract_guide_grid(img, max_rows=8)
    assert guide["detected"] is True
    assert guide["counts"]["channels"] >= 5, guide["counts"]
    assert guide["counts"]["programs"] >= 12, guide["counts"]
    selected = guide["selected"]
    assert selected["channel_number"] == "250", selected
    assert "Hawaii" in selected["title"], selected
    assert selected["button_sequence"] == ["select"], selected
    assert any(r.get("icon_signature") for r in guide["rows"]), "channel icon signatures were not captured"


def test_crawler_brain_learns_guide_channels_programs_and_icons():
    # Synthetic grid keeps the learner test deterministic and avoids a second
    # Tesseract pass in the same process on Windows/WSL. OCR behavior is covered
    # by test_guide_grid_extracts_rows_selected_program_and_icons above.
    guide = {
        "confidence": 0.99,
        "selected": {"title": "Hawaii Five-O", "channel_number": "250"},
        "counts": {"rows": 2, "channels": 2, "programs": 3, "program_options": 4},
        "rows": [
            {
                "row_index": 0,
                "channel_number": "250",
                "channel_code": "ION",
                "channel_name": "ION",
                "channel_logo_text": "250 ION",
                "icon_signature": "ah16:iontest",
                "programs": [
                    {"row_index": 0, "col_index": 0, "title": "Hawaii Five-O", "raw_text": "Hawaii Five-O", "time_label": "7:30a", "selected": True, "button_sequence": ["select"]},
                    {"row_index": 0, "col_index": 1, "title": "Chicago P.D.", "raw_text": "Chicago P.D.", "time_label": "9:00a", "selected": False, "button_sequence": ["right", "select"]},
                ],
            },
            {
                "row_index": 1,
                "channel_number": "249",
                "channel_code": "CI",
                "channel_name": "CI",
                "channel_logo_text": "249 CI HD",
                "icon_signature": "ah16:citest",
                "programs": [
                    {"row_index": 1, "col_index": 0, "title": "I Survived", "raw_text": "I Survived", "time_label": "7:30a", "selected": False, "button_sequence": ["down", "select"]},
                ],
            },
        ],
    }
    with TemporaryDirectory() as td:
        brain = CrawlerBrain(Path(td))
        learned = brain.learn_guide_grid(guide, state_id="guide_state", screenshot="states/guide.jpg")
        assert learned["known_channels"] == 2, learned
        assert learned["updated_programs"] == 3, learned
        rec = brain.channels.get("250")
        assert rec is not None
        assert rec.channel_code == "ION"
        assert rec.icon_signatures, rec
        assert any("Hawaii" in p.get("title", "") for p in rec.programs), rec.programs
        assert brain.find_program_candidates("Hawaii Five", channel=250, limit=3), "program search returned nothing"


if __name__ == "__main__":
    test_raw_numeric_channel_expands_to_digit_sequence()
    test_guide_grid_extracts_rows_selected_program_and_icons()
    test_crawler_brain_learns_guide_channels_programs_and_icons()
    print("guide self-correction v34: OK")
