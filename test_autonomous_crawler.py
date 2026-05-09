#!/usr/bin/env python3
"""Synthetic smoke test for the autonomous crawler.

This does not need a capture card or STB. It fakes a few screens and verifies that
the crawler learns states/edges and writes nav_graph.json.
"""
from __future__ import annotations

import tempfile
from pathlib import Path

import cv2
import numpy as np

from auto_crawler import AutonomousCrawler, CrawlerConfig


class FakeSTB:
    def __init__(self) -> None:
        self.state = "home"
        self.frames = {}
        for name, text, color in [
            ("home", "HOME GUIDE DVR APPS", (20, 50, 90)),
            ("guide", "GUIDE ESPN 206 HISTORY 120", (40, 80, 30)),
            ("info", "INFO DETAILS PROGRAM OPTIONS", (70, 40, 40)),
            ("row2", "HOME MOVIES SPORTS SEARCH", (20, 80, 100)),
        ]:
            img = np.zeros((360, 640, 3), dtype=np.uint8)
            img[:] = color
            cv2.rectangle(img, (30, 40), (610, 320), (255, 255, 255), 2)
            cv2.putText(img, text, (50, 180), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
            self.frames[name] = img

    def frame(self):
        return self.frames[self.state]

    def status(self):
        return {"active": True, "width": 640, "height": 360}

    def send(self, key: str):
        if key == "home":
            self.state = "home"
        elif key == "guide":
            self.state = "guide"
        elif key == "info":
            self.state = "info"
        elif key == "down" and self.state == "home":
            self.state = "row2"
        elif key == "back":
            self.state = "home"
        return {"ok": True, "key": key, "state": self.state}


def main() -> int:
    fake = FakeSTB()
    with tempfile.TemporaryDirectory() as d:
        crawler = AutonomousCrawler(
            Path(d),
            fake.frame,
            fake.status,
            fake.send,
            CrawlerConfig(
                max_steps=10,
                max_states=10,
                max_depth=2,
                settle_s=0.01,
                reset_settle_s=0.01,
                between_key_s=0.01,
                ocr_enabled=False,
            ),
        )
        crawler.run()
        status = crawler.status()
        print("nodes:", status["node_count"])
        print("edges:", status["edge_count"])
        print("steps:", status["steps"])
        print("graph:", crawler.graph.graph_path)
        assert status["node_count"] >= 3, status
        assert status["edge_count"] >= 4, status
        assert crawler.graph.graph_path.is_file(), crawler.graph.graph_path
    print("AUTO_CRAWLER_SYNTHETIC_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
