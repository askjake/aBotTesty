#!/usr/bin/env python3
import tempfile, time
from pathlib import Path
import cv2
import numpy as np

from auto_crawler import AutonomousCrawler, CrawlerConfig
from manual_teaching_recorder import ManualTeachingRecorder


def frame(label, idx):
    img = np.zeros((240, 426, 3), dtype=np.uint8)
    img[:] = (20, 22, 26)
    cv2.putText(img, f"DISH {label}", (18, 32), cv2.FONT_HERSHEY_SIMPLEX, .65, (230,230,230), 1)
    x = 40 + idx * 80
    cv2.rectangle(img, (x, 85), (x+70, 135), (0,0,255), 3)
    cv2.putText(img, label, (x, 160), cv2.FONT_HERSHEY_SIMPLEX, .45, (230,230,230), 1)
    return img


def main():
    with tempfile.TemporaryDirectory() as td:
        state = {"idx": 0}
        labels = ["Home", "Guide", "Info"]
        sent = []
        def capture():
            return frame(labels[min(state["idx"], 2)], min(state["idx"], 2))
        def status():
            return {"active": True}
        def send_key(key):
            sent.append(key)
            state["idx"] = min(state["idx"] + 1, 2)
            return {"ok": True, "key": key}
        crawler = AutonomousCrawler(Path(td), capture, status, send_key, CrawlerConfig(ocr_enabled=False, save_screenshots=True, timing_poll_s=.03, max_adaptive_observe_s=.15, min_settle_s=.03, max_settle_s=.15))
        teacher = ManualTeachingRecorder(Path(td), crawler, capture, status, lambda k, d=None, g=.01: send_key(k))
        teacher.burst_idle_s = .10
        # Simulates the v26 monitor path: auto-create a session and record fast operator commands.
        assert teacher.start("Auto-learned monitor operation", operator="monitor_auto")["ok"]
        r = teacher.record_button_fast("guide", gap_s=.01, note="operator command via /monitor", operator_auto=True, source="operator_monitor_auto")
        assert r["ok"] and r["recording"] == "pending_burst"
        time.sleep(.8)
        st = teacher.status()
        events = st["active_session"]["events"]
        transitions = [e for e in events if e.get("type") == "button_transition"]
        assert transitions, events
        assert transitions[-1]["reward"] >= 12.0, transitions[-1]
        edge_samples = [e.samples[-1] for e in crawler.graph.edges.values() if e.samples]
        assert edge_samples and edge_samples[-1].get("source") == "operator_monitor_auto", edge_samples[-1]
        assert edge_samples[-1].get("operator_auto") is True, edge_samples[-1]
        print("OPERATOR_MONITOR_LEARNING_V26_OK")


if __name__ == "__main__":
    main()
