#!/usr/bin/env python3
import tempfile, time
from pathlib import Path
import numpy as np, cv2

from auto_crawler import AutonomousCrawler, CrawlerConfig
from manual_teaching_recorder import ManualTeachingRecorder

class FakeTV:
    def __init__(self):
        self.state = 0
        self.sent = []
    def frame(self):
        img = np.zeros((240, 426, 3), dtype=np.uint8)
        img[:] = (25,25,25)
        x = 30 + (self.state % 5) * 70
        cv2.rectangle(img, (x, 75), (x+52, 120), (0,0,255), 3)
        cv2.putText(img, f"DISH Test State {self.state}", (20, 30), cv2.FONT_HERSHEY_SIMPLEX, .55, (220,220,220), 1)
        cv2.putText(img, f"Item {self.state}", (x, 145), cv2.FONT_HERSHEY_SIMPLEX, .45, (230,230,230), 1)
        return img
    def status(self):
        return {"active": True}
    def send(self, key):
        self.sent.append((key, time.time()))
        self.state += 1
        return {"ok": True, "key": key}

def test_fast_teacher_burst():
    with tempfile.TemporaryDirectory() as td:
        tv=FakeTV()
        crawler=AutonomousCrawler(Path(td), tv.frame, tv.status, tv.send, CrawlerConfig(ocr_enabled=False, execution_mode="balanced", max_adaptive_observe_s=.35, timing_outlier_clip_s=.5))
        teacher=ManualTeachingRecorder(Path(td), crawler, tv.frame, tv.status, lambda k, d=None, g=.01: {"ok": True, "key": k, "sent": tv.send(k)})
        teacher.burst_idle_s = .12
        assert teacher.start("v14")['ok']
        t0=time.time()
        r1=teacher.record_button_fast('right', gap_s=.01)
        r2=teacher.record_button_fast('down', gap_s=.01)
        elapsed=time.time()-t0
        assert elapsed < .25, elapsed
        time.sleep(1.2)
        st=teacher.status()
        events=st['active_session']['events']
        transitions=[e for e in events if e.get('type')=='button_transition']
        assert transitions, events
        assert transitions[-1]['button'] in {'right,down','right'}
        teacher.stop()
        assert len(crawler.graph.edges) >= 1

def test_timing_clip():
    with tempfile.TemporaryDirectory() as td:
        tv=FakeTV()
        crawler=AutonomousCrawler(Path(td), tv.frame, tv.status, tv.send, CrawlerConfig(ocr_enabled=False, timing_outlier_clip_s=.7))
        crawler.brain.update_timing('home', 123.0, max_sample_s=.7)
        assert crawler.brain.timing_for('home').avg_response_s <= .7

if __name__ == '__main__':
    test_fast_teacher_burst()
    test_timing_clip()
    print('TIMING_EXECUTION_V14_OK')
