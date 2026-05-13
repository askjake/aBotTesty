from pathlib import Path
import cv2
from focus_detector import detect_focus, _ocr_image

ROOT = Path(__file__).resolve().parent
SAMPLE_DIR = Path('/mnt/data/crawler2/crawler_data/states')

def test_tesseract_whitelist_no_dash_argument_crash():
    import numpy as np
    img = np.ones((60, 240, 3), dtype=np.uint8) * 255
    cv2.putText(img, 'TV Activity - On', (8, 38), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,0,0), 2)
    txt = _ocr_image(img, psm=7, whitelist='ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789 -_&:+./')
    assert isinstance(txt, str)


def test_recall_overlay_focus_label_recovery():
    p = SAMPLE_DIR / 'after_68d33953ad_20260510_101650_332781.jpg'
    if not p.exists():
        return
    focus = detect_focus(cv2.imread(str(p)))
    assert focus['screen_title'] == 'Recall'
    assert 'TCM 132' in focus['focused_item']
    assert 'missing_screen_title' not in focus.get('quality_flags', [])


def test_trending_live_focus_prefers_real_red_outline_over_logo():
    p = SAMPLE_DIR / 'after_b880376415_20260510_104223_393740.jpg'
    if not p.exists():
        return
    focus = detect_focus(cv2.imread(str(p)))
    assert focus['focused_item'] == 'See More'
    assert focus['screen_title'] in {'Trending', 'Trending Live'}
    assert focus['bbox'][0] < 300  # not the red FOX LIVE logo in the video strip

if __name__ == '__main__':
    test_tesseract_whitelist_no_dash_argument_crash()
    test_recall_overlay_focus_label_recovery()
    test_trending_live_focus_prefers_real_red_outline_over_logo()
    print('test_focus_context_v11: OK')
