#!/usr/bin/env python3
import json
import tempfile
from pathlib import Path
import cv2
import numpy as np

from auto_crawler import AutonomousCrawler, CrawlerConfig
from dashboard_analytics import DashboardDataset
from ppv_pricing import extract_purchase_pricing, check_purchase_limits
from ppv_purchase_agent import PPVPurchaseAgent


def frame():
    img = np.zeros((240, 426, 3), dtype=np.uint8)
    cv2.putText(img, "The Super Mario Galaxy Movie", (20, 60), cv2.FONT_HERSHEY_SIMPLEX, .45, (230,230,230), 1)
    cv2.putText(img, "HD $24.99 Rent", (20, 110), cv2.FONT_HERSHEY_SIMPLEX, .5, (230,230,230), 1)
    return img


def make_agent(td: str, text: str):
    sent=[]
    def capture(): return frame()
    def status(): return {"active": True}
    def send(k): sent.append(k); return {"ok": True, "key": k}
    crawler = AutonomousCrawler(Path(td), capture, status, send, CrawlerConfig(ocr_enabled=False, save_screenshots=True))
    orig = crawler.capture_fingerprint
    def fake_fp(*a, **kw):
        fp = orig(*a, **kw)
        fp.ocr_text = text
        fp.focus = {"page_name":"Select Your Option", "screen_title":"The Super Mario Galaxy Movie", "focused_item":"Rent", "recovery_text":text, "human_cues":{"screen_kind":"purchase_or_ppv", "risk_flags":["purchase_flow"]}}
        return fp
    crawler.capture_fingerprint = fake_fp
    return PPVPurchaseAgent(Path(td), crawler, capture, lambda k,d=None,g=.01: send(k)), sent


def test_price_parser():
    p = extract_purchase_pricing("HD $24.99 Rent")
    assert p["amount"] == 24.99 and p["category"] == "paid", p
    f = extract_purchase_pricing("FREE On Demand until 6/17")
    assert f["amount"] == 0.0 and f["category"] == "free", f
    ok, reason, _ = check_purchase_limits(24.99, 25.00, 50.00, 10.00)
    assert ok and reason == "within_limits"
    ok, reason, _ = check_purchase_limits(24.99, 10.00, 50.00, 0)
    assert not ok and reason == "price_exceeds_individual_limit"


def test_agent_limits_and_dashboard():
    with tempfile.TemporaryDirectory() as td:
        text = "dish Select Your Option The Super Mario Galaxy Movie Rent Available for 48 hours HD $24.99 Rent On Demand Purchase Confirmation Is this correct? Yes No"
        agent, sent = make_agent(td, text)
        a = agent.analyze_current()
        assert a["purchase_price"] == 24.99, a
        dry_unlimited = agent.run_current_purchase_test(dry_run=True)
        assert dry_unlimited["price_authorization"]["allowed"] is True, dry_unlimited
        agent.set_limits(individual_limit="0", session_limit="0")
        dry = agent.run_current_purchase_test(dry_run=True)
        assert dry["price_authorization"]["allowed"] is False, dry
        assert dry["price_authorization"]["reason"] == "price_exceeds_individual_limit", dry
        agent.set_limits(individual_limit="25", session_limit="30")
        dry2 = agent.run_current_purchase_test(dry_run=True)
        assert dry2["price_authorization"]["allowed"] is True, dry2
        agent.arm(ttl_s=60)
        live = agent.run_current_purchase_test(dry_run=False, confirm_purchase=True, final_confirm=True)
        assert live["ok"] and sent, live
        assert agent.limits_status()["session_spent"] == 24.99, agent.limits_status()
        # Minimal dashboard files.
        root=Path(td)
        for name, obj in {
            "nav_graph.json":{"nodes":{},"edges":{}},
            "crawler_brain.json":{},
            "learned_sequences.json":{},
            "unreachable_states.json":{},
            "channel_surf_log.json":{"observations":[]},
            "sysdiag_bootstrap_history.json":[],
        }.items():
            (root/name).write_text(json.dumps(obj), encoding="utf-8")
        ds=DashboardDataset.load(root)
        rows=ds.ppv_purchase_rows()
        assert any(r["event_type"]=="purchase_recorded" and float(r["price_amount"])==24.99 for r in rows), rows
        assert "stb_ppv_purchases" in ds.superset_tables()


def main():
    test_price_parser()
    test_agent_limits_and_dashboard()
    print("PPV_PRICING_LIMITS_V30_OK")

if __name__ == "__main__":
    main()
