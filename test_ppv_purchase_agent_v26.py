#!/usr/bin/env python3
import tempfile
from pathlib import Path
import cv2
import numpy as np

from auto_crawler import AutonomousCrawler, CrawlerConfig
from ppv_purchase_agent import PPVPurchaseAgent


def ppv_frame():
    img = np.zeros((240, 426, 3), dtype=np.uint8)
    img[:] = (25,25,25)
    cv2.putText(img, "DISH PPV", (20, 32), cv2.FONT_HERSHEY_SIMPLEX, .65, (230,230,230), 1)
    cv2.putText(img, "Order Movie Night $6.99", (20, 92), cv2.FONT_HERSHEY_SIMPLEX, .55, (230,230,230), 1)
    cv2.putText(img, "Confirm Purchase", (20, 132), cv2.FONT_HERSHEY_SIMPLEX, .55, (230,230,230), 1)
    return img


def main():
    with tempfile.TemporaryDirectory() as td:
        sent=[]
        def capture(): return ppv_frame()
        def status(): return {"active": True}
        def send(k): sent.append(k); return {"ok": True, "key": k}
        crawler = AutonomousCrawler(Path(td), capture, status, send, CrawlerConfig(ocr_enabled=False, save_screenshots=True))
        # Monkeypatch capture_fingerprint to include OCR/focus text without relying on Tesseract.
        orig = crawler.capture_fingerprint
        def fake_fp(*a, **kw):
            fp = orig(*a, **kw)
            fp.ocr_text = "DISH PPV Order Movie Night $6.99 Confirm Purchase"
            fp.focus = {"screen_title":"PPV", "focused_item":"Order Movie Night", "recovery_text":"Order Movie Night $6.99 Confirm Purchase", "human_cues":{"screen_kind":"purchase_or_ppv", "risk_flags":["purchase_flow"]}}
            return fp
        crawler.capture_fingerprint = fake_fp
        agent = PPVPurchaseAgent(Path(td), crawler, capture, lambda k,d=None,g=.01: send(k))
        a = agent.analyze_current()
        assert a["is_ppv_context"], a
        dry = agent.run_current_purchase_test(dry_run=True)
        assert dry["ok"] and dry["dry_run"], dry
        blocked = agent.run_current_purchase_test(dry_run=False, confirm_purchase=True)
        assert not blocked["ok"] and "armed" in blocked["error"].lower(), blocked
        agent.arm(ttl_s=60)
        live = agent.run_current_purchase_test(dry_run=False, confirm_purchase=True, final_confirm=False)
        assert live["ok"] and sent, live
        print("PPV_PURCHASE_AGENT_V26_OK")

if __name__ == "__main__":
    main()
