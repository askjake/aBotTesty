#!/usr/bin/env python3
from pathlib import Path
from dashboard_analytics import DashboardDataset


def main():
    here = Path(__file__).resolve().parent
    candidates = [here / 'crawler_data', Path('/mnt/data/latest_crawler_data/crawler_data')]
    data_dir = next((p for p in candidates if (p / 'nav_graph.json').is_file()), candidates[0])
    ds = DashboardDataset.load(data_dir)
    ex = ds.executive()
    eng = ds.engineering()
    assert 'headline' in ex and 'timeline' in ex and 'known_unknowns' in ex
    assert 'headline' in eng and 'per_action_coverage' in eng and 'state_quality' in eng
    tables = ds.superset_tables()
    for name in ['stb_learning_states','stb_learning_edges','stb_learning_actions','stb_learning_coverage','stb_learning_known_unknowns','stb_learning_timeline']:
        assert name in tables
        assert isinstance(tables[name], list)
    z = ds.export_zip_bytes()
    assert z[:2] == b'PK' and len(z) > 1000
    print('dashboard v16 ok', ex['headline'])

if __name__ == '__main__':
    main()
