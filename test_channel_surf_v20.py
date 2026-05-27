#!/usr/bin/env python3
import tempfile
from pathlib import Path
import numpy as np
import cv2

from channel_surf_agent import ChannelSurfAgent
from dashboard_analytics import DashboardDataset
from time_context import extract_display_clock


class Fake:
    def __init__(self):
        self.keys=[]
        self.channel=100
        self.frame=self._frame("DISH Sat 5/23 | 12:03p Live TV 100 TEST Program")
    def _frame(self,text):
        img=np.zeros((360,640,3),dtype=np.uint8)
        img[:]=(40,40,42)
        cv2.rectangle(img,(20,20),(620,340),(70,70,70),-1)
        cv2.putText(img,text[:48],(35,90),cv2.FONT_HERSHEY_SIMPLEX,0.55,(255,255,255),1)
        cv2.putText(img,text[48:96],(35,130),cv2.FONT_HERSHEY_SIMPLEX,0.55,(255,255,255),1)
        return img
    def capture_frame(self):
        return self.frame.copy()
    def status(self):
        return {"active":True,"signal_class":"active_static_ui","motion_score":0.0}
    def send(self,key):
        key=str(key); self.keys.append(key)
        if key.isdigit():
            return {"ok":True,"key":key}
        if key=="select":
            digits=''.join(k for k in self.keys[-5:] if k.isdigit())
            if digits: self.channel=int(digits[-3:])
            self.frame=self._frame(f"DISH Sat 5/23 | 12:03p Live TV {self.channel} TEST Program")
        elif key=="ch_up":
            self.channel += 2  # simulate skipped channel
            self.frame=self._frame(f"DISH Sat 5/23 | 12:03p Live TV {self.channel} TEST Program")
        elif key=="ch_down":
            self.channel -= 2
            self.frame=self._frame(f"DISH Sat 5/23 | 12:03p Live TV {self.channel} TEST Program")
        elif key=="info":
            self.frame=self._frame(f"DISH Sat 5/23 | 12:03p Info {self.channel} TEST Program")
        elif key=="guide":
            self.frame=self._frame(f"DISH Sat 5/23 | 12:03p Guide {self.channel} TEST Program")
        return {"ok":True,"key":key}


def main():
    clock=extract_display_clock("DISH Sat 5/23 | 12:03p Guide", {}, observed_at="2026-05-23T18:05:00+00:00")
    assert clock["found"] and abs(clock["drift_minutes"]) <= 3
    no_clock=extract_display_clock("12:30p 003-00 KWGN Young Sheldon", {}, observed_at="2026-05-23T18:05:00+00:00")
    assert not no_clock["found"], no_clock
    with tempfile.TemporaryDirectory() as td:
        fake=Fake()
        agent=ChannelSurfAgent(Path(td), fake.capture_frame, fake.status, fake.send)
        cfg=agent.parse_config({"start_channel":"100","max_channels":"3","surf_mode":"channel_up","collect_info":True,"collect_guide":True,"tune_timeout_s":"2","post_tune_settle_s":"0.1","info_settle_s":"0.1","guide_settle_s":"0.1","channel_step_settle_s":"0.1"})
        agent.run(cfg)
        assert len(agent.history)==3
        assert any(o.get("input_method")=="ch_up" for o in agent.history)
        assert any(o.get("skipped_channel_detected") for o in agent.history), agent.history
        ds=DashboardDataset.load(Path(td))
        rows=ds.channel_surf_rows()
        assert len(rows)==3
        assert "stb_channel_surf" in ds.superset_tables()
        assert "stb_display_time_checks" in ds.superset_tables()
    print("CHANNEL_SURF_V20_OK")

if __name__=="__main__":
    main()
