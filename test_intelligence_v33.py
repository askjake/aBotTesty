#!/usr/bin/env python3
from pathlib import Path
import tempfile
import cv2
import numpy as np
from auto_crawler import AutonomousCrawler, CrawlerConfig

class FakeSTB:
    def __init__(self):
        self.state='s0'
        self.frames={}
        for i in range(22):
            img=np.zeros((240,426,3),dtype=np.uint8)
            img[:]=(10+i*5%200,40+i*7%200,80+i*9%150)
            cv2.putText(img,f'SCREEN {i}',(30,120),cv2.FONT_HERSHEY_SIMPLEX,1,(255,255,255),2)
            self.frames[f's{i}']=img
    def frame(self): return self.frames[self.state]
    def status(self): return {'active':True}
    def send(self,key):
        idx=int(self.state[1:])
        if key=='right': idx=(idx+1)%22
        elif key=='left': idx=(idx-1)%22
        elif key=='home': idx=0
        self.state=f's{idx}'
        return {'ok':True}

with tempfile.TemporaryDirectory() as d:
    f=FakeSTB()
    c=AutonomousCrawler(Path(d), f.frame, f.status, f.send, CrawlerConfig(max_steps=60,max_states=80,max_depth=6,settle_s=.001,reset_settle_s=.001,between_key_s=.001,ocr_enabled=False,human_observer_enabled=False,region_first_perception_enabled=False,enabled_keys=['right','left','home']))
    c.run()
    full_nodes=len(c.graph.nodes)
    m=c.visual_map(max_nodes=8,max_edges=12,include_transitions=False)
    assert m['ok'] is True
    assert m['node_count']==full_nodes
    assert m['visible_node_count']<=8, m['visible_node_count']
    assert m['visible_edge_count']<=12, m['visible_edge_count']
    assert m['transitions']==[], 'transitions must be lazy by default'
    if full_nodes > 20:
        assert m['map_slice']['truncated'] is True
    else:
        assert m['map_slice']['truncated'] is False
print('intelligence v33 map slicing: OK')
