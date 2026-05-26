#!/usr/bin/env python3
"""v10 smoke tests for DISH page-name and grey-box title perception."""
from __future__ import annotations

import os
import json
import cv2

from focus_detector import detect_focus


def _collected_base() -> str | None:
    for p in [
        os.environ.get("CRAWLER_DATA_DIR", ""),
        r"C:\Users\Systems1\Downloads\crawler_data",
        "/mnt/data/cdata1/crawler_data",
        "crawler_data",
    ]:
        if p and os.path.exists(os.path.join(p, "nav_graph.json")):
            return p
    return None


def _load_state(base: str, state_id: str):
    graph = json.load(open(os.path.join(base, "nav_graph.json"), "r", encoding="utf-8"))
    node = graph["nodes"][state_id]
    rel = node["representative"]["screenshot"].replace("\\", os.sep)
    img = cv2.imread(os.path.join(base, rel))
    assert img is not None, rel
    return detect_focus(img)


def test_v10_collected_snapshots():
    base = _collected_base()
    if not base:
        print("SKIP: no collected crawler_data available")
        return

    diag = _load_state(base, "screen_130c33a7f8")
    assert diag["page_name"] == "Diagnostics"
    assert diag["screen_title"] == "Diagnostics"
    assert diag["focused_item"] == "Receiver 1"

    parental = _load_state(base, "root_cc41879137")
    assert parental["page_name"] == "Parental Control Settings"
    assert parental["screen_title"] == "Parental Control Settings"

    tv = _load_state(base, "after_e395d15b85")
    assert tv["page_name"] == ""
    assert tv["block_title"] == "TV Viewing Options"
    assert tv["screen_title"] == "TV Viewing Options"
    assert tv["focused_item"] == "TV Activity"

    home = _load_state(base, "screen_aea5603ad5")
    assert home["page_name"] == "Home"
    assert home["focused_item"] == "Search"

    locked = _load_state(base, "after_e4c8bb4a1e")
    assert locked["page_name"] == "Locked Channels"
    assert locked["screen_title"] == "Locked Channels"


if __name__ == "__main__":
    test_v10_collected_snapshots()
    print("v10 focus context tests OK")
