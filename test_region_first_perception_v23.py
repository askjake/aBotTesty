#!/usr/bin/env python3
from pathlib import Path
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

from region_first_perception import RegionFirstPerceiver, RegionRead, pattern_from_region_family


class FakePerceiver(RegionFirstPerceiver):
    def __init__(self, region_texts):
        super().__init__(pytesseract_mod=False)
        self.region_texts = dict(region_texts)

    def read_region(self, frame, name, box, psm=6, stage="targeted"):
        text = self.region_texts.get(name, "")
        return RegionRead(name=name, box=box, text=text, confidence=0.8 if text else 0.0, stage=stage)

    def quick_visual(self, frame):
        return {"progress_dot_count": 0, "progress_dots_likely": False, "mid_edge_density": 0.12, "black_fraction": 0.0}

    def detect_red_focus_bbox(self, frame):
        return None


def test_classify_text_context():
    family, score, reasons = RegionFirstPerceiver.classify_from_text(
        "dish Guide Showing: All Subscribed TODAY 12:30p How I Met Your Mother", {}
    )
    assert family == "guide", (family, score, reasons)
    assert score >= 0.5
    assert pattern_from_region_family(family) == "grid_menu"

    family, score, _ = RegionFirstPerceiver.classify_from_text(
        "dish TV Show Summary Episodes Cast Record This Record Series Schitt's Creek POP 117", {}
    )
    assert family == "info", family
    assert pattern_from_region_family(family) == "info_card"

    family, score, _ = RegionFirstPerceiver.classify_from_text(
        "Live TV Beachfront Bargain Hunt MAGN 111 Sat 5/23 12:36p 23 mins left", {}
    )
    assert family == "live_banner", family
    assert pattern_from_region_family(family) == "video_player"


def test_region_first_expected_regions_and_actions():
    frame = np.zeros((720, 1280, 3), dtype=np.uint8)
    p = FakePerceiver({
        "top_left_title": "dish Guide",
        "top_right_clock": "Sat 5/23 12:39p",
        "top_banner": "dish Guide Showing: All Subscribed TODAY 12:30p 1:00p",
        "left_channel_strip": "114 E! HD 113 COOK HD 112 HGTV HD 111 MAGN HD",
        "center_grid": "How I Met Your Mother Property Brothers Beachfront Bargain Hunt",
        "right_detail_panel": "How I Met Your Mother Best Prom Ever 12:30 - 1:00p",
    })
    ctx = p.perceive(frame)
    assert ctx["screen_family"] == "guide", ctx
    assert ctx["stage"] in {"targeted", "common"}, ctx
    assert "right_detail_panel" in ctx["satisfied_regions"], ctx
    assert "up" in ctx["suggested_actions"] and "right" in ctx["suggested_actions"], ctx
    assert ctx["displayed_datetime_text"], ctx
    assert ctx["channel_number"] == "114", ctx


def test_region_first_broadens_when_expectations_missing():
    frame = np.zeros((720, 1280, 3), dtype=np.uint8)
    p = FakePerceiver({
        "top_left_title": "dish",
        "top_right_clock": "Sat 5/23 12:39p",
        # Not enough targeted text; common regions add info screen evidence.
        "info_title_area": "Schitt's Creek",
        "info_channel_area": "POP 117 On Now 12:30 - 1:00p",
        "info_description_area": "TV Show Summary Episodes Cast Parental Guide Record This",
    })
    ctx = p.perceive(frame)
    assert ctx["screen_family"] in {"info", "menu"}, ctx
    assert ctx["stage"] in {"common", "targeted"}, ctx
    assert ctx["quality_flags"], ctx


if __name__ == "__main__":
    test_classify_text_context()
    test_region_first_expected_regions_and_actions()
    test_region_first_broadens_when_expectations_missing()
    print("REGION_FIRST_PERCEPTION_V23_OK")
