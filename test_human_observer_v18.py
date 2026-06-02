#!/usr/bin/env python3
from pathlib import Path
import tempfile

import cv2
import numpy as np

from auto_crawler import AutonomousCrawler, CrawlerConfig, FeatureExtractor, SimilarityModel
from human_observer import observe_human_cues


def make_loader_frame():
    img = np.zeros((720, 1280, 3), dtype=np.uint8)
    # dark grey background + black top bar
    img[:] = (32, 32, 32)
    cv2.rectangle(img, (0, 0), (1280, 90), (0, 0, 0), -1)
    cv2.putText(img, "d:sh", (35, 55), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 255), 3)
    # top-right thumbnail
    cv2.rectangle(img, (1010, 14), (1240, 88), (70, 70, 70), 2)
    cv2.rectangle(img, (1020, 22), (1230, 80), (110, 80, 55), -1)
    # central progress dots, some active teal
    x0 = 560
    for i in range(9):
        color = (20, 20, 20) if i not in (4, 5, 6) else (180, 210, 25)
        cv2.rectangle(img, (x0 + i * 20, 350), (x0 + i * 20 + 11, 361), color, -1)
    return img


def make_passive_video(seed=0):
    rng = np.random.default_rng(seed)
    img = rng.integers(20, 220, (720, 1280, 3), dtype=np.uint8)
    # Add a broadcast-ish lower third but no UI focus.
    cv2.rectangle(img, (0, 600), (1280, 720), (25, 25, 25), -1)
    cv2.putText(img, "LIVE TV 206  ESPN", (35, 670), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (240, 240, 240), 3)
    return img


def test_loading_interstitial_detection_and_completion_gate():
    img = make_loader_frame()
    human = observe_human_cues(img, focus={"found": False}, ocr_text="")
    assert human["screen_kind"] == "loading_interstitial", human
    assert human["is_transient"] is True
    with tempfile.TemporaryDirectory() as td:
        crawler = AutonomousCrawler(
            data_dir=Path(td),
            capture_frame=lambda: img.copy(),
            capture_status=lambda: {"active": True},
            send_key=lambda key: {"ok": True, "key": key},
            config=CrawlerConfig(ocr_enabled=False, save_screenshots=False),
        )
        fp = crawler.extractor.extract(img, "loader")
        incomplete, reasons = crawler.fingerprint_looks_incomplete(fp, "guide")
        assert incomplete, reasons
        assert "human_loading_interstitial" in reasons, reasons


def test_passive_video_frames_collapse_as_same_ui_state():
    with tempfile.TemporaryDirectory() as td:
        extractor = FeatureExtractor(Path(td), save_screenshots=False, ocr_enabled=False)
        a = extractor.extract(make_passive_video(1), "vid_a")
        b = extractor.extract(make_passive_video(2), "vid_b")
        assert a.focus.get("human_cues", {}).get("screen_kind") == "passive_video", a.focus.get("human_cues")
        assert b.focus.get("human_cues", {}).get("screen_kind") == "passive_video", b.focus.get("human_cues")
        cmp = SimilarityModel.compare(a, b)
        assert cmp["score"] >= 0.90, cmp


def test_ppv_and_timer_goal_detection():
    img = np.zeros((720, 1280, 3), dtype=np.uint8)
    ppv = observe_human_cues(img, focus={"found": True, "confidence": 0.9, "focused_item": "Order"}, ocr_text="Pay-Per-View Event Price $19.99 Purchase now")
    assert ppv["screen_kind"] == "purchase_or_ppv", ppv
    assert "purchase_flow" in ppv["risk_flags"], ppv
    assert any(g["goal"] == "inspect_ppv_availability" for g in ppv["test_goals"]), ppv
    timer = observe_human_cues(img, focus={"found": True, "confidence": 0.9, "focused_item": "Set Timer"}, ocr_text="Set timer for this event Record series Reminder")
    assert timer["screen_kind"] == "timer_or_recording_flow", timer
    assert any(g["goal"] == "set_or_verify_timer" for g in timer["test_goals"]), timer


if __name__ == "__main__":
    test_loading_interstitial_detection_and_completion_gate()
    test_passive_video_frames_collapse_as_same_ui_state()
    test_ppv_and_timer_goal_detection()
    print("v18 human observer tests passed")
