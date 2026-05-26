#!/usr/bin/env python3
from pathlib import Path
import tempfile
import cv2
import numpy as np

import auto_crawler
auto_crawler.detect_focus = lambda frame, tess=None: {"found": False, "tokens": []}
from auto_crawler import AutonomousCrawler, CrawlerConfig
from manual_teaching_recorder import ManualTeachingRecorder


def make_frame(label: str, x: int) -> np.ndarray:
    img = np.zeros((360, 640, 3), dtype=np.uint8)
    img[:] = (25, 25, 30)
    cv2.putText(img, "DISH Home", (30, 45), cv2.FONT_HERSHEY_SIMPLEX, 1, (230, 230, 230), 2)
    cv2.rectangle(img, (x, 130), (x + 160, 230), (0, 0, 255), 4)
    cv2.putText(img, label, (x + 15, 190), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (240, 240, 240), 2)
    return img


def main():
    with tempfile.TemporaryDirectory() as td:
        frames = {
            "start": make_frame("Search", 60),
            "right": make_frame("DVR", 240),
            "select": make_frame("DVR Open", 240),
        }
        state = {"frame": frames["start"].copy()}

        def capture_frame():
            return state["frame"].copy()

        def capture_status():
            return {"active": True}

        def send_key(key: str):
            if key == "right":
                state["frame"] = frames["right"].copy()
            elif key == "select":
                state["frame"] = frames["select"].copy()
            return {"ok": True, "key": key}

        crawler = AutonomousCrawler(
            data_dir=Path(td),
            capture_frame=capture_frame,
            capture_status=capture_status,
            send_key=send_key,
            config=CrawlerConfig(ocr_enabled=False, save_screenshots=True, settle_s=0.15, min_settle_s=0.05, max_settle_s=0.25, timing_poll_s=0.05),
        )
        teacher = ManualTeachingRecorder(Path(td), crawler, capture_frame, capture_status, lambda key, delay_ms=None, gap_s=0.0: send_key(key))
        st = teacher.start("demo", "synthetic")
        assert st["active"] is True
        r1 = teacher.record_button("right", gap_s=0.0)
        assert r1["ok"] and r1["recorded"]
        r2 = teacher.record_button("select", gap_s=0.0)
        assert r2["ok"] and r2["recorded"]
        done = teacher.stop()
        assert done["ok"]
        assert len(crawler.graph.nodes) >= 2
        assert len(crawler.graph.edges) >= 2
        assert crawler.brain.state_actions
        sessions = teacher.list_sessions()
        assert sessions["count"] >= 1
        print("manual teaching v13 synthetic test: OK", len(crawler.graph.nodes), "states", len(crawler.graph.edges), "edges")


if __name__ == "__main__":
    main()
