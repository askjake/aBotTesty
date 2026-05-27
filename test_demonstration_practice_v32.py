from pathlib import Path
from tempfile import TemporaryDirectory

from auto_crawler import AutonomousCrawler, CrawlerConfig, ScreenFingerprint


def fp(sid: str, text: str) -> ScreenFingerprint:
    return ScreenFingerprint(
        state_id=sid,
        timestamp="2026-05-24T00:00:00+00:00",
        screenshot=None,
        ahash=("0" * 15) + ("1" if sid.endswith("1") else "2"),
        dhash=("0" * 15) + ("1" if sid.endswith("1") else "2"),
        phash=("0" * 15) + ("1" if sid.endswith("1") else "2"),
        brightness=50.0,
        variance=10.0,
        entropy=2.0,
        edge_density=0.1,
        color_hist=[0.0] * 24,
        ocr_text=text,
        ocr_tokens=text.lower().split(),
        focus={"found": True, "human_label": text, "screen_title": text},
        width=1280,
        height=720,
        ui_pattern="grid_menu",
    )


def test_demo_edges_bias_frontier_and_actions():
    with TemporaryDirectory() as td:
        cfg = CrawlerConfig(max_depth=10, demo_practice_enabled=True, enabled_keys=["up", "down", "select", "back"])
        crawler = AutonomousCrawler(Path(td), lambda: None, lambda: {"active": True}, lambda key: {"ok": True, "key": key}, cfg)
        s1, _, _ = crawler.graph.upsert_state(fp("s1", "On Demand Landing"), 0.1)
        s2, _, _ = crawler.graph.upsert_state(fp("s2", "Movie Details Rent"), 0.1)
        crawler.graph.root_state = s1
        edge = crawler.graph.record_edge(
            s1,
            "select",
            s2,
            changed=True,
            success=True,
            confidence=0.9,
            sample={"source": "operator_monitor_auto", "operator_auto": True, "reward_details": {"operator_customer_path_weight": 12.0}},
        )
        assert crawler.edge_is_demonstrated(edge)
        ordered = crawler.apply_pattern_action_order(s1, ["up", "down", "select", "back"])
        assert ordered[0] == "select", ordered
        frontier = list(crawler.build_frontier())
        assert frontier[0][0] in {s1, s2}, frontier[:3]
        assert crawler.demonstration_stats()["edge_count"] == 1
        # Demonstrated actions get a higher retry budget than random probes.
        assert crawler.action_budget_for_state(s1, "select") > crawler.config.max_action_attempts_per_state


if __name__ == "__main__":
    test_demo_edges_bias_frontier_and_actions()
    print("demonstration practice v32 synthetic test: OK")
