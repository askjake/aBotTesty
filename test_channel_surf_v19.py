#!/usr/bin/env python3
import tempfile
import numpy as np
import cv2
from pathlib import Path
from channel_surf_agent import ChannelSurfAgent

class Fake:
    def __init__(self):
        self.keys=[]
        self.frame=self._frame("Live TV 206 ESPN Planet Earth")
    def _frame(self,text):
        img=np.zeros((360,640,3),dtype=np.uint8)
        img[:]=(35,35,35)
        cv2.rectangle(img,(20,20),(620,340),(70,70,70),-1)
        cv2.putText(img,text,(40,120),cv2.FONT_HERSHEY_SIMPLEX,0.8,(255,255,255),2)
        return img
    def capture_frame(self):
        return self.frame.copy()
    def status(self):
        return {"active":True,"signal_class":"active_static_ui","motion_score":0.0}
    def send(self,key):
        self.keys.append(str(key))
        if key=="info":
            self.frame=self._frame("Info 206 ESPN Planet Earth II")
        elif key=="guide":
            self.frame=self._frame("Guide 206 ESPN Planet Earth II 8:00 PM")
        return {"ok":True,"key":key}

def main():
    f=Fake()
    with tempfile.TemporaryDirectory() as td:
        agent=ChannelSurfAgent(Path(td), f.capture_frame, f.status, f.send)
        cfg=agent.parse_config({"channels":"206","collect_info":True,"collect_guide":True,"max_channels":1})
        obs=agent.scan_channel(206,cfg)
        assert obs.channel==206
        assert obs.live_health["active"]
        assert "2" in f.keys and "0" in f.keys and "6" in f.keys
        assert "info" in f.keys and "guide" in f.keys
        assert obs.ok or "guide_channel_mismatch" in obs.warning_flags
        agent.history.append(obs.__dict__)
        agent.save()
        assert (Path(td)/"channel_surf_log.json").exists()
    print("CHANNEL_SURF_V19_OK")

if __name__=="__main__":
    main()
