from pathlib import Path
import tempfile

from pattern_recognition import PatternRecognizer, AdaptiveThresholdModel
from sequence_learner import SequenceLearner
from persistence_tracker import PersistenceTracker
from auto_crawler import AutonomousCrawler, CrawlerConfig, ScreenFingerprint

class Dummy:
    ocr_text = "DISH Settings Parental Control TV Viewing Options"
    ocr_tokens = ["settings", "parental", "control", "options"]
    variance = 400.0
    edge_density = 0.09
    state_id = "dummy"
    focus = {"found": True, "focused_item": "Parental Controls", "screen_title": "Settings", "focused_value": "On"}

pc = PatternRecognizer().classify_screen(Dummy(), Dummy.focus)
assert pc.confidence > 0.2, pc
assert pc.pattern.value in {"linear_menu", "form", "pin_prompt"}, pc

atm = AdaptiveThresholdModel()
assert 0.70 <= atm.get_threshold("grid_menu") <= 0.98
atm.update_state_stability("s1", 20, 100)
assert atm.get_threshold("linear_menu", "s1") > atm.get_threshold("linear_menu")

with tempfile.TemporaryDirectory() as td:
    data = Path(td)
    seq = SequenceLearner(data)
    for _ in range(3):
        seq.record_action("a", "home", "b", 3.0, 0.05)
        seq.record_action("b", "guide", "c", 4.0, 0.05)
    learned = seq.mine_sequences(min_occurrences=3, min_avg_reward=2)
    assert learned
    assert seq.suggest_next_action(["home"])[0] == "guide"

    pt = PersistenceTracker(data)
    pt.mark_navigation_failed("s9", ["home", "settings"], "test", context={"label": "Parental Settings", "depth": 6})
    assert pt.get_retry_candidates()
    pt.mark_navigation_succeeded("s9")
    assert not pt.get_retry_candidates()

    frames = []
    import numpy as np
    frames.append(np.zeros((80, 120, 3), dtype=np.uint8))
    def cap(): return frames[-1]
    def status(): return {"active": True}
    def send(k): return {"ok": True, "key": k}
    crawler = AutonomousCrawler(data, cap, status, send, CrawlerConfig(max_steps=0))
    fp = crawler.capture_fingerprint("test", perception="fast")
    assert hasattr(fp, "ui_pattern")
    st = crawler.status()
    assert "patterns" in st["learning"] and "sequences" in st["learning"] and "persistence" in st["learning"]

print("FORK_MERGE_V15_OK")
