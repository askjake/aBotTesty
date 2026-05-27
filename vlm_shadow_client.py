#!/usr/bin/env python3
"""Client for aBotTesty VLM shadow server."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict

import requests


DEFAULT_URL = "http://10.79.85.35:8765"


def infer_image(
    image_bytes: bytes,
    task: str = "perception",
    goal: str = "explore the TV UI safely",
    action: str = "",
    server_url: str = DEFAULT_URL,
    timeout_s: float = 180.0,
) -> Dict[str, Any]:
    files = {"image": ("snapshot.jpg", image_bytes, "image/jpeg")}
    data = {"task": task, "goal": goal, "action": action}
    r = requests.post(f"{server_url.rstrip('/')}/infer", data=data, files=files, timeout=timeout_s)
    r.raise_for_status()
    return r.json()


def health(server_url: str = DEFAULT_URL, timeout_s: float = 10.0) -> Dict[str, Any]:
    r = requests.get(f"{server_url.rstrip('/')}/health", timeout=timeout_s)
    r.raise_for_status()
    return r.json()


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--server-url", default=DEFAULT_URL)
    p.add_argument("--image", required=False)
    p.add_argument("--task", default="perception", choices=["perception", "policy", "verify"])
    p.add_argument("--goal", default="explore the TV UI safely")
    p.add_argument("--action", default="")
    p.add_argument("--health", action="store_true")
    args = p.parse_args()

    if args.health:
        print(json.dumps(health(args.server_url), indent=2))
        return 0

    if not args.image:
        raise SystemExit("--image is required unless --health is used")

    data = Path(args.image).read_bytes()
    print(json.dumps(infer_image(data, args.task, args.goal, args.action, args.server_url), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
