#!/usr/bin/env python3
from pathlib import Path
import tempfile
import cv2
import numpy as np
from auto_crawler import AutonomousCrawler, CrawlerConfig

class FakeSTB:
    def __init__(self):
        self.state='home'
        self.map={('home','guide'):'guide',('guide','back'):'home',('home','down'):'settings',('settings','select'):'audio'}
    def frame(self):
        idx={'home':0,'guide':1,'settings':2,'audio':3}.get(self.state,0)
        img=np.zeros((240,420,3), dtype=np.uint8)
        img[:]=(25+idx*45,40+idx*25,80+idx*18)
        cv2.putText(img, self.state.upper(), (28,128), cv2.FONT_HERSHEY_SIMPLEX, 1.15, (255,255,255), 2)
        return img
    def status(self): return {'active': True}
    def send(self,k):
        if k=='home': self.state='home'
        else: self.state=self.map.get((self.state,k), self.state)
        return {'ok':True,'key':k,'state':self.state}

with tempfile.TemporaryDirectory() as td:
    f=FakeSTB()
    c=AutonomousCrawler(Path(td), f.frame, f.status, f.send, CrawlerConfig(
        max_steps=5, max_states=10, max_depth=3, enabled_keys=['guide','down','select','back'],
        min_active_required=False, ocr_enabled=False, adaptive_timing_enabled=False,
        settle_s=0.01, between_key_s=0.01, reset_settle_s=0.01,
        state_similarity_threshold=0.985, changed_similarity_threshold=0.985,
        max_action_attempts_per_state=1))
    c.run()
    m=c.visual_map()
    assert m['schema']=='jamboree_visual_flow_map_v4_focus'
    assert m['layout']['mode']=='vertical_lanes'
    assert m['transitions'], m
    t=m['transitions'][0]
    assert 'before' in t and 'button' in t and 'after' in t
    assert isinstance(t['button_sequence'], list) and t['button_sequence']
    assert 'before' in m['edges'][0] and 'after' in m['edges'][0]
    cards=c.transition_cards()
    assert cards and cards[0]['before']['image_url'] and cards[0]['after']['image_url']
    print('TRANSITION_JOURNAL_V6_OK', m['node_count'], m['edge_count'], len(m['transitions']))
