from pathlib import Path
import tempfile
from parental_control_agent import ParentalControlAgent

class FakeBrain:
    def expected_settle_s(self, key, cfg): return 0.01
class FakeConfig:
    channel_tune_settle_s = 0.01
class FakeCrawler:
    def __init__(self):
        self.sent=[]; self.brain=FakeBrain(); self.config=FakeConfig(); self.prompt=True
    def safe_send(self,key):
        self.sent.append(str(key)); return {'ok': True, 'key': key}
    def analyze_focus_current(self):
        if self.prompt:
            return {'ok': True, 'focus': {'pin_required': True, 'popup_type': 'parental_pin_prompt', 'human_label': 'Parental PIN Prompt'}}
        return {'ok': True, 'focus': {'human_label': 'Live TV'}}
    def plan_route(self, query=None): return {'ok': True, 'path': ['home','settings'], 'query': query}
    def navigate_to_target(self, query=None, channel=None, dry_run=False): return {'ok': True, 'query': query, 'channel': channel}


def test_pin_entry_and_memory():
    with tempfile.TemporaryDirectory() as d:
        fc=FakeCrawler(); agent=ParentalControlAgent(fc, Path(d))
        assert agent.remember_pin('1234')['ok']
        out=agent.maybe_enter_pin()
        assert out['pin_prompt'] is True
        assert fc.sent[:4] == list('1234')
        assert fc.sent[-1] == 'select'

if __name__ == '__main__':
    test_pin_entry_and_memory()
    print('test_parental_control_agent_v11: OK')
