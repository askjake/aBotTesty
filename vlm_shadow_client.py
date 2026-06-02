#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import mimetypes
from pathlib import Path

import requests


def main() -> int:
    ap = argparse.ArgumentParser(description="aBotTesty VLM shadow client")
    ap.add_argument("--server-url", default="http://10.79.85.35:8765")
    ap.add_argument("--image", required=True)
    ap.add_argument("--task", choices=["perception", "policy", "verifier"], default="perception")
    ap.add_argument("--goal", default="explore the TV UI safely")
    ap.add_argument("--action", default="")
    ap.add_argument("--timeout", type=float, default=180.0)
    args = ap.parse_args()

    image = Path(args.image)
    if not image.is_file():
        raise SystemExit(f"image not found: {image}")

    url = args.server_url.rstrip("/") + "/infer"
    mime = mimetypes.guess_type(str(image))[0] or "image/jpeg"

    with image.open("rb") as f:
        files = {"image": (image.name, f, mime)}
        data = {
            "task": args.task,
            "goal": args.goal,
            "action": args.action,
        }
        resp = requests.post(url, data=data, files=files, timeout=args.timeout)

    try:
        payload = resp.json()
    except Exception:
        print(resp.text)
        resp.raise_for_status()
        return 1

    print(json.dumps(payload, indent=2))
    resp.raise_for_status()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
