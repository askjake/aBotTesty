from pathlib import Path
from parental_control_agent import ParentalControlAgent

class FakeBrain:
    def expected_settle_s(self, action, config): return 0.01
class FakeConfig:
    between_key_s=0.0
class FakeCrawler:
    def __init__(self):
        self.brain=FakeBrain(); self.config=FakeConfig(); self.sent=[]; self.i=0
        self.labels=['Home → Search','Home → DVR','Home → On Demand','Home → Guide','Home → Settings','Settings → Parental Controls']
    def safe_send(self, key):
        self.sent.append(key)
        if key in ('right','down') and self.i < len(self.labels)-1: self.i += 1
        if key == 'home': self.i = 0
        if key == 'select' and 'Settings' in self.labels[self.i]: self.i = len(self.labels)-1
        return {'ok': True, 'key': key}
    def analyze_focus_current(self):
        lab=self.labels[self.i]
        return {'ok': True, 'focus': {'human_label': lab, 'focused_item': lab.split('→')[-1].strip()}, 'focus_label': lab}
    def plan_route(self, query=None, **kwargs): return {'ok': False, 'error': 'no_learned_route', 'query': query}
    def navigate_to_target(self, **kwargs): return {'ok': False, 'error': 'no_learned_route'}

a=ParentalControlAgent(FakeCrawler(), Path('/tmp/pcagent-v12-test'))
r=a.setup_parental_controls('1234', dry_run=False)
assert r['ok'], r
assert 'active_discovery' in r, r
assert 'home' in a.crawler.sent and 'select' in a.crawler.sent, a.crawler.sent
print('test_parental_active_v12: OK', a.crawler.sent)
