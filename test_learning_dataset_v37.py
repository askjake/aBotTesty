#!/usr/bin/env python3
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from PIL import Image

from learning_dataset_writer import LearningDatasetWriter


def _write_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def test_export_from_nav_graph_and_channel_surf():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        crawler = root / "crawler_data"
        states = crawler / "states"
        states.mkdir(parents=True)
        img1 = states / "before.jpg"
        img2 = states / "after.jpg"
        Image.new("RGB", (320, 180), (20, 30, 40)).save(img1)
        Image.new("RGB", (320, 180), (60, 70, 80)).save(img2)
        _write_json(crawler / "nav_graph.json", {
            "nodes": [
                {"id": "s1", "label": "Live TV", "screenshot": "states/before.jpg", "ocr_text": "Live TV"},
                {"id": "s2", "label": "Guide", "screenshot": "states/after.jpg", "ocr_text": "Guide ION Hawaii Five-0"},
            ],
            "transitions": [
                {"from": "s1", "to": "s2", "action": "guide", "reward": 5.0, "confidence": 0.9, "changed": True}
            ],
        })
        _write_json(root / "channel_surf_log.json", {"observations": [{"channel": 250, "ok": True, "live_health": {"active": True}}]})
        writer = LearningDatasetWriter(root_dir=root, crawler_dir=crawler, out_dir=root / "learning_datasets")
        stats = writer.stats()
        assert stats["artifact_counts"]["nav_graph"] == 1
        result = writer.export(run_id="unit", max_records=10)
        assert result["ok"] is True
        out = Path(result["dataset_dir"])
        assert (out / "manifest.json").is_file()
        episodes = (out / "episodes.jsonl").read_text(encoding="utf-8").strip().splitlines()
        assert len(episodes) >= 2
        assert (out / "sft" / "screen_perception.jsonl").is_file()
        assert (out / "sft" / "action_policy.jsonl").is_file()
        assert (out / "sft" / "outcome_verifier.jsonl").is_file()
        assert len(list((out / "images").glob("*.jpg"))) >= 2
        manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
        assert manifest["schema"] == "abot_learning_dataset_v37_phase1"
        assert manifest["episode_count"] >= 2


if __name__ == "__main__":
    test_export_from_nav_graph_and_channel_surf()
    print("LEARNING_DATASET_V37_OK")
