#!/usr/bin/env python3
from flask import Flask, request, jsonify, send_file
import io, time, logging, urllib.request

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger(__name__)
app = Flask(__name__)

_state = {"input": 6, "channel": 206, "resolution": "1080i", "signal": True, "audio": True}

def _apply_key(key):
    if key == "CH_UP":
        _state["channel"] += 1
    elif key == "CH_DOWN":
        _state["channel"] = max(1, _state["channel"] - 1)
    elif key.startswith("CH_") and key[3:].isdigit():
        _state["channel"] = int(key[3:])
    log.info("key=%s channel=%s", key, _state["channel"])

@app.route("/screen")
def screen():
    return jsonify(dict(_state))

@app.route("/key", methods=["POST"])
def send_key():
    d = request.get_json(force=True)
    k = d.get("key", "")
    _state["input"] = d.get("input", _state["input"])
    _apply_key(k)
    return jsonify({"status": "ok", "key": k, "channel": _state["channel"]})

@app.route("/screenshot")
def screenshot():
    # Pillow PNG: channel-encoded, NO timestamp (zero noise floor)
    # Color background encodes channel: hue shifts with channel number
    from PIL import Image, ImageDraw
    ch   = _state["channel"]
    inp  = _state["input"]
    # Background color unique per channel (hue cycle)
    hue  = (ch * 37) % 256
    bg   = (hue, 30, 80 - hue % 40)
    img  = Image.new("RGB", (1280, 720), bg)
    draw = ImageDraw.Draw(img)
    # Large channel number fills header
    draw.rectangle([0, 0, 1280, 120], fill=(0, 60 + ch % 60, 120 + ch % 80))
    # Draw channel prominently (repeated for pixel density)
    label = f"CHANNEL {ch}  INPUT {inp}"
    for x in range(0, 1280, 200):
        draw.text((x, 40), label, fill=(255, 255, 255))
    # Center large channel number
    draw.text((400, 300), f"CH {ch}", fill=(200 + ch % 55, 200, 200))
    buf  = io.BytesIO()
    img.save(buf, "PNG")
    buf.seek(0)
    log.info("screenshot CH %s (no timestamp)", ch)
    return send_file(buf, mimetype="image/png")

if __name__ == "__main__":
    log.info("SGS on 0.0.0.0:8080")
    app.run(host="0.0.0.0", port=8080, debug=False)
