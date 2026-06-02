#!/usr/bin/env python3
from pathlib import Path
import tempfile
import cv2
import numpy as np
from auto_crawler import AutonomousCrawler, CrawlerConfig

class FakeSTB:
    def __init__(self):
        self.state='home'
        self.transitions={
            ('home','guide'):'guide', ('guide','back'):'home',
            ('home','right'):'apps', ('apps','select'):'app_detail', ('app_detail','back'):'apps',
            ('apps','left'):'home', ('home','down'):'settings', ('settings','select'):'audio', ('audio','back'):'settings'
        }
    def frame(self):
        names=['home','guide','apps','app_detail','settings','audio']
        idx=names.index(self.state) if self.state in names else 0
        img=np.zeros((220,380,3), dtype=np.uint8); img[:]=(20+idx*25,40+idx*13,75+idx*17)
        cv2.putText(img, self.state.upper(), (20,115), cv2.FONT_HERSHEY_SIMPLEX, 1.1, (255,255,255), 2)
        return img
    def status(self): return {'active': True}
    def send(self,k):
        if k=='home': self.state='home'
        else: self.state=self.transitions.get((self.state,k), self.state)
        return {'ok': True, 'key': k, 'state': self.state}

with tempfile.TemporaryDirectory() as td:
    fake=FakeSTB()
    crawler=AutonomousCrawler(Path(td), fake.frame, fake.status, fake.send,
        CrawlerConfig(max_steps=18, max_states=20, max_depth=4, enabled_keys=['guide','right','left','down','select','back'],
                      continuous_exploration_enabled=True, max_cycles=2, max_action_attempts_per_state=1,
                      settle_s=0.01, reset_settle_s=0.01, between_key_s=0.01, min_active_required=False,
                      ocr_enabled=False, adaptive_timing_enabled=False, state_similarity_threshold=0.985, changed_similarity_threshold=0.985))
    crawler.run()
    m=crawler.visual_map()
    cov=m['coverage']
    assert m['schema']=='jamboree_visual_flow_map_v4_focus'
    assert m['node_count'] >= 4, m
    assert m['edge_count'] >= 5, m
    assert 'remaining_state_actions' in cov
    assert all('image_url' in n and 'remaining_actions' in n for n in m['nodes'])
    assert all('action' in e and 'curve_index' in e and 'before' in e and 'after' in e for e in m['edges'])
    assert m['transitions'] and all('before' in t and 'button' in t and 'after' in t for t in m['transitions'])
    print('CONTINUOUS_FLOW_MAP_OK', m['node_count'], m['edge_count'], cov['completion_pct'])
