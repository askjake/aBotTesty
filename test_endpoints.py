#!/usr/bin/env python3
"""Tiny endpoint smoke check after the app is running."""
import json
import urllib.request

BASE = "http://127.0.0.1:8502"
for path in ["/api/self-test", "/api/status", "/screen", "/api/crawl/status", "/api/crawl/graph"]:
    with urllib.request.urlopen(BASE + path, timeout=5) as r:
        print(path, r.status, json.loads(r.read().decode()))
