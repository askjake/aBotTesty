"""tune_verify.py — STB tune verification using pixel diff"""
import urllib.request, json, io, hashlib

SGS       = "http://127.0.0.1:8080"
THRESHOLD = 1000  # px: noise=0, signal=8000+ (Pillow no-timestamp mode)

def get_screen():
    r = urllib.request.urlopen(SGS + "/screen", timeout=5)
    return json.loads(r.read().decode())

def get_screenshot_bytes():
    r = urllib.request.urlopen(SGS + "/screenshot", timeout=8)
    return r.read()

def pixel_diff(img_a, img_b):
    from PIL import Image
    a = list(Image.open(io.BytesIO(img_a)).convert("RGB").getdata())
    b = list(Image.open(io.BytesIO(img_b)).convert("RGB").getdata())
    return sum(1 for x, y in zip(a, b) if x != y)

def send_key(key, input_id=6):
    payload = json.dumps({"key": key, "input": input_id}).encode()
    req = urllib.request.Request(
        SGS + "/key", data=payload,
        headers={"Content-Type": "application/json"}, method="POST")
    return json.loads(urllib.request.urlopen(req, timeout=5).read().decode())

def verified_tune(key, expected_channel=None, wait=1.5):
    """
    Send key, wait, verify tune via pixel diff.
    Returns dict: key, before_ch, after_ch, diff_px,
                  tune_confirmed, channel_correct, pass
    """
    before_img = get_screenshot_bytes()
    before_ch  = get_screen()["channel"]
    send_key(key)
    import time; time.sleep(wait)
    after_img  = get_screenshot_bytes()
    after_ch   = get_screen()["channel"]
    diff       = pixel_diff(before_img, after_img)
    tune_ok    = diff > THRESHOLD
    ch_ok      = (after_ch == expected_channel) if expected_channel else True
    return {
        "key":             key,
        "before_ch":       before_ch,
        "after_ch":        after_ch,
        "diff_px":         diff,
        "tune_confirmed":  tune_ok,
        "channel_correct": ch_ok,
        "pass":            tune_ok and ch_ok,
    }

if __name__ == "__main__":
    import sys
    print("tune_verify self-test")
    s = get_screen()
    start_ch = s["channel"]
    print(f"  Starting: input={s[chr(105)+chr(110)+chr(112)+chr(117)+chr(116)]} channel={start_ch}")
    r1 = verified_tune("CH_UP", expected_channel=start_ch+1)
    status1 = "PASS" if r1["pass"] else "FAIL"
    print(f"  CH_UP:   {start_ch}->{r1[chr(97)+chr(102)+chr(116)+chr(101)+chr(114)+chr(95)+chr(99)+chr(104)]}  diff={r1[chr(100)+chr(105)+chr(102)+chr(102)+chr(95)+chr(112)+chr(120)]}px  {status1}")
    r2 = verified_tune("CH_DOWN", expected_channel=start_ch)
    status2 = "PASS" if r2["pass"] else "FAIL"
    print(f"  CH_DOWN: {r1[chr(97)+chr(102)+chr(116)+chr(101)+chr(114)+chr(95)+chr(99)+chr(104)]}->{r2[chr(97)+chr(102)+chr(116)+chr(101)+chr(114)+chr(95)+chr(99)+chr(104)]}  diff={r2[chr(100)+chr(105)+chr(102)+chr(102)+chr(95)+chr(112)+chr(120)]}px  {status2}")
    all_ok = r1["pass"] and r2["pass"]
    print(f"  Result: {chr(80)+chr(65)+chr(83)+chr(83) if all_ok else chr(70)+chr(65)+chr(73)+chr(76)}")
    sys.exit(0 if all_ok else 1)
