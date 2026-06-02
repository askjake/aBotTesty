#!/usr/bin/env python3
"""Local client for the aBotTesty remote VLM shadow server.

Used by merged_app.py routes:
  /api/vlm/shadow/analyze
  /api/vlm/shadow/policy
  /api/vlm/shadow/verify

This client is intentionally non-actuating. It only sends images to the
remote VLM shadow server and prints JSON.
"""
from __future__ import annotations

import argparse
import json
import mimetypes
import sys
from pathlib import Path
from typing import Any, Dict, Optional

import requests


DEFAULT_SERVER_URL = "http://10.79.85.35:8765"


def _json_out(payload: Dict[str, Any], exit_code: int = 0) -> int:
    print(json.dumps(payload, indent=2, sort_keys=True))
    return exit_code


def health(server_url: str = DEFAULT_SERVER_URL, timeout_s: float = 10.0) -> Dict[str, Any]:
    url = server_url.rstrip("/") + "/health"
    try:
        r = requests.get(url, timeout=timeout_s)
        try:
            payload = r.json()
        except Exception:
            payload = {"raw": r.text}
        payload.setdefault("ok", r.ok)
        payload["status_code"] = r.status_code
        payload["url"] = url
        if not r.ok:
            payload.setdefault("error", f"HTTP {r.status_code}")
        return payload
    except Exception as exc:
        return {"ok": False, "url": url, "error": str(exc)}


def infer_image(
    image_path: Path,
    task: str = "perception",
    goal: str = "Explore the TV UI safely. Do not purchase or confirm anything.",
    action: str = "",
    server_url: str = DEFAULT_SERVER_URL,
    timeout_s: float = 180.0,
) -> Dict[str, Any]:
    if task == "verifier":
        task = "verify"

    if not image_path.is_file():
        return {"ok": False, "error": f"image not found: {image_path}", "image": str(image_path)}

    url = server_url.rstrip("/") + "/infer"
    mime = mimetypes.guess_type(str(image_path))[0] or "image/jpeg"

    try:
        with image_path.open("rb") as f:
            files = {"image": (image_path.name, f, mime)}
            data = {
                "task": task,
                "goal": goal,
                "action": action,
            }
            r = requests.post(url, data=data, files=files, timeout=timeout_s)

        try:
            payload: Any = r.json()
        except Exception:
            payload = {"raw": r.text}

        if isinstance(payload, dict):
            payload.setdefault("ok", r.ok)
            payload["status_code"] = r.status_code
            payload["url"] = url
            payload["task"] = task
            if not r.ok:
                payload.setdefault("error", f"HTTP {r.status_code}")
            return payload

        return {
            "ok": r.ok,
            "status_code": r.status_code,
            "url": url,
            "task": task,
            "response": payload,
        }

    except Exception as exc:
        return {"ok": False, "url": url, "task": task, "error": str(exc)}


def verify_images(
    before_path: Path,
    after_path: Path,
    action: str = "",
    goal: str = "Verify the requested action outcome.",
    server_url: str = DEFAULT_SERVER_URL,
    timeout_s: float = 180.0,
) -> Dict[str, Any]:
    if not before_path.is_file():
        return {"ok": False, "error": f"before image not found: {before_path}"}
    if not after_path.is_file():
        return {"ok": False, "error": f"after image not found: {after_path}"}

    url = server_url.rstrip("/") + "/verify"
    try:
        with before_path.open("rb") as before_f, after_path.open("rb") as after_f:
            files = {
                "before": (before_path.name, before_f, mimetypes.guess_type(str(before_path))[0] or "image/jpeg"),
                "after": (after_path.name, after_f, mimetypes.guess_type(str(after_path))[0] or "image/jpeg"),
            }
            data = {"goal": goal, "action": action}
            r = requests.post(url, data=data, files=files, timeout=timeout_s)

        try:
            payload: Any = r.json()
        except Exception:
            payload = {"raw": r.text}

        if isinstance(payload, dict):
            payload.setdefault("ok", r.ok)
            payload["status_code"] = r.status_code
            payload["url"] = url
            payload["task"] = "verify"
            if not r.ok:
                payload.setdefault("error", f"HTTP {r.status_code}")
            return payload

        return {"ok": r.ok, "status_code": r.status_code, "url": url, "task": "verify", "response": payload}

    except Exception as exc:
        return {"ok": False, "url": url, "task": "verify", "error": str(exc)}


def main() -> int:
    p = argparse.ArgumentParser(description="aBotTesty VLM shadow client")
    p.add_argument("--server-url", default=DEFAULT_SERVER_URL)
    p.add_argument("--health", action="store_true")
    p.add_argument("--image", default="")
    p.add_argument("--before", default="")
    p.add_argument("--after", default="")
    p.add_argument("--task", default="perception", choices=["perception", "policy", "verify", "verifier"])
    p.add_argument("--goal", default="Explore the TV UI safely. Do not purchase or confirm anything.")
    p.add_argument("--action", default="")
    p.add_argument("--timeout", type=float, default=180.0)
    args = p.parse_args()

    if args.health:
        payload = health(args.server_url, timeout_s=min(args.timeout, 30.0))
        return _json_out(payload, 0 if payload.get("ok") else 2)

    if args.before and args.after:
        payload = verify_images(
            Path(args.before),
            Path(args.after),
            action=args.action,
            goal=args.goal,
            server_url=args.server_url,
            timeout_s=args.timeout,
        )
        return _json_out(payload, 0 if payload.get("ok") else 2)

    if not args.image:
        return _json_out({"ok": False, "error": "--image is required unless --health or --before/--after is used"}, 2)

    payload = infer_image(
        Path(args.image),
        task=args.task,
        goal=args.goal,
        action=args.action,
        server_url=args.server_url,
        timeout_s=args.timeout,
    )
    return _json_out(payload, 0 if payload.get("ok") else 2)


if __name__ == "__main__":
    raise SystemExit(main())
