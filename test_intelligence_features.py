import tempfile
from pathlib import Path
import numpy as np
from auto_crawler import AutonomousCrawler, CrawlerConfig

class FakeSTB:
    def __init__(self):
        self.state='home'
        self.map={
            ('home','guide'):'guide', ('guide','back'):'home', ('home','info'):'info', ('info','back'):'home',
            ('home','right'):'settings', ('settings','left'):'home', ('settings','select'):'audio_settings', ('audio_settings','back'):'settings'
        }
    def frame(self):
        # visually different frames by state index
        idx=['home','guide','info','settings','audio_settings'].index(self.state) if self.state in ['home','guide','info','settings','audio_settings'] else 0
        rng=np.random.default_rng(idx+1)
        img=(rng.integers(0,255,(180,320,3))).astype(np.uint8)
        img[0:30,:,:]=20+idx*35
        return img
    def status(self): return {'active': True}
    def send(self,k):
        if str(k).startswith('CH_'):
            self.state='ch'+str(k).split('_',1)[1]
        else:
            self.state=self.map.get((self.state,k), self.state)
        return {'ok':True,'key':k,'state':self.state}

with tempfile.TemporaryDirectory() as td:
    stb=FakeSTB()
    c=AutonomousCrawler(Path(td), stb.frame, stb.status, stb.send, CrawlerConfig(max_steps=8, max_states=10, enabled_keys=['guide','back','right','left','select'], min_active_required=False, ocr_enabled=False, adaptive_timing_enabled=False, settle_s=0.01, between_key_s=0.01, reset_settle_s=0.01))
    # avoid HOME context reset changing fake state; override with no-op context
    c.restore_start_context=lambda: None
    root=c.capture_fingerprint('root')
    root.ocr_text='Home Menu Guide Settings'
    root.ocr_tokens=['home','menu','guide','settings']
    sid,_,_=c.graph.upsert_state(root, c.config.state_similarity_threshold); c.graph.root_state=sid
    c.try_action(sid,'guide')
    c.try_action(sid,'right')
    c.graph.save(); c.brain.save()
    m=c.visual_map()
    assert m['node_count'] >= 2
    assert 'guide' in c.action_confidence_report()
    candidates=c.find_state_candidates('settings')
    assert candidates
    plan=c.plan_route(query='settings')
    assert 'ok' in plan
    goal=c.run_goal('settings', dry_run=True)
    assert goal['candidates']
    print('INTELLIGENCE_FEATURES_OK', m['node_count'], m['edge_count'])
