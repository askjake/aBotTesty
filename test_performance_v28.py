import tempfile
from pathlib import Path

import numpy as np

from auto_crawler import AutonomousCrawler, CrawlerConfig, FeatureExtractor, NavigationGraph, StateNode
from capture_monitor import CaptureMonitor


def test_compact_and_candidate_prefilter():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        graph = NavigationGraph(root)
        graph.compact_save = True
        graph.match_candidate_limit = 5
        ex = FeatureExtractor(root, save_screenshots=False, ocr_enabled=False, region_first_enabled=False)
        base = np.zeros((72, 128, 3), dtype=np.uint8)
        for i in range(20):
            img = base.copy()
            img[:, :, 0] = (i * 9) % 255
            img[10:30, 10+i:30+i] = 255
            fp = ex.extract(img, hint_id=f"s{i}")
            graph.nodes[fp.state_id] = StateNode(fp.state_id, fp.timestamp, fp.timestamp, 1, fp, label=f"state {i}")
        probe = ex.extract(base, hint_id="probe")
        _sid, cmp = graph.find_best(probe)
        assert cmp.get("candidate_prefilter") == 1.0
        assert cmp.get("candidate_count") == 5
        graph.save()
        raw = (root / "nav_graph.json").read_text()
        assert "\n  " not in raw[:500], "compact save should not pretty-print hot graph JSON"


def test_hot_loop_save_batching():
    with tempfile.TemporaryDirectory() as td:
        cfg = CrawlerConfig(max_steps=1, hot_loop_save_every_n_actions=99, hot_loop_save_min_interval_s=999.0)
        c = AutonomousCrawler(Path(td), lambda: np.zeros((72, 128, 3), dtype=np.uint8), lambda: {"active": True, "signal_class": "active_static_ui"}, lambda key: {"ok": True}, cfg)
        import time
        c._steps = 1
        c._last_hot_save = time.time()
        c.mark_learning_dirty()
        assert c.maybe_save_hot_loop(force=False) is False
        assert c._save_dirty is True
        assert c.maybe_save_hot_loop(force=True) is True
        assert c._save_dirty is False


def test_capture_monitor_jpeg_throttle_config():
    m = CaptureMonitor(jpeg_every_n_frames=3)
    assert m.jpeg_every_n_frames == 3


if __name__ == "__main__":
    test_compact_and_candidate_prefilter()
    test_hot_loop_save_batching()
    test_capture_monitor_jpeg_throttle_config()
    print("PERFORMANCE_V28_OK")
