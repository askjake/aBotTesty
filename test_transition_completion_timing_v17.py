#!/usr/bin/env python3
"""Synthetic test for v17 phased action timing.

The fake STB shows: stable before -> moving/loading -> stable after.
The crawler should learn both the first visible start and later completion.
"""
import tempfile
import time
from pathlib import Path

import cv2
import numpy as np

from auto_crawler import AutonomousCrawler, CrawlerConfig


def frame_with_text(text: str, value: int) -> np.ndarray:
    img = np.zeros((240, 426, 3), dtype=np.uint8)
    img[:] = (value, value, value)
    cv2.rectangle(img, (40, 60), (380, 190), (value + 20, value + 20, value + 20), -1)
    cv2.putText(img, text, (55, 125), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2, cv2.LINE_AA)
    return img


before = frame_with_text("BEFORE", 35)
loading = frame_with_text("LOADING", 80)
after = frame_with_text("AFTER READY", 130)

start_t = None

def capture_frame():
    global start_t
    if start_t is None:
        return before.copy()
    dt = time.time() - start_t
    if dt < 0.16:
        return before.copy()
    if dt < 0.55:
        # Vary the loading frame so visual stability does not trigger too early.
        jitter = int((dt * 1000) % 40)
        return frame_with_text("LOADING", 70 + jitter).copy()
    return after.copy()


def capture_status():
    return {"active": True}


def send_key(key: str):
    global start_t
    start_t = time.time()
    return {"ok": True, "key": key}


def main():
    global start_t
    with tempfile.TemporaryDirectory() as td:
        cfg = CrawlerConfig(
            enabled_keys=["select"],
            adaptive_timing_enabled=True,
            timing_poll_s=0.05,
            changed_similarity_threshold=0.94,
            completion_stability_threshold=0.985,
            completion_stable_observations_required=2,
            completion_min_observe_s=0.18,
            max_completion_observe_s=2.0,
            completion_extra_attempts=0,
            min_active_required=False,
            ocr_enabled=False,
        )
        crawler = AutonomousCrawler(Path(td), capture_frame, capture_status, send_key, cfg)
        before_fp = crawler.capture_fingerprint("before", perception="fast")
        send_key("select")
        after_fp, complete_s, timing = crawler.wait_after_action("select", before_fp, perception="fast")

        assert timing["mode"] == "phased_adaptive", timing
        assert timing["action_start_s"] >= 0.10, timing
        assert timing["action_complete_s"] >= 0.50, timing
        assert timing["action_complete_s"] > timing["action_start_s"], timing
        assert crawler.brain.timing_for("select").avg_complete_s > crawler.brain.timing_for("select").avg_start_s
        print("TRANSITION_COMPLETION_TIMING_V17_OK", timing)


if __name__ == "__main__":
    main()
