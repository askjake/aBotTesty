#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import logging, threading, time
from typing import Optional
import requests

log = logging.getLogger("nmb.jam_controller")
JAM_HOST       = "http://127.0.0.1:5003"
DEFAULT_STB   = "stb1"
DEFAULT_REMOTE= "sgs"
DEFAULT_DELAY = 100
COMMAND_TIMEOUT=3.0

class JAMController:
    def __init__(self,host=JAM_HOST,stb=DEFAULT_STB,remote=DEFAULT_REMOTE):
        self.host=host.rstrip("/"); self.stb=stb; self.remote=remote
        self._queue=[]; self._lock=threading.Lock()
        self._running=True; self._last_result={}; self._last_error=""
        self._worker=threading.Thread(target=self._dispatch_loop,daemon=True,name="JAM-Dispatch")
        self._worker.start()

    def send(self,button,delay_ms=DEFAULT_DELAY):
        with self._lock: self._queue.append((button.lower(),max(delay_ms,80)))

    def send_input(self,delay_ms=DEFAULT_DELAY): self.send("input",delay_ms)

    def send_sequence(self,buttons,delay_ms=DEFAULT_DELAY):
        for b in buttons: self.send(b,delay_ms)

    def ping(self):
        try: return requests.get(f"{self.host}/hostname",timeout=2.0).status_code==200
        except: return False

    def get_stb_list(self):
        try: return requests.get(f"{self.host}/get-stb-list",timeout=2.0).json()
        except Exception as exc: log.error("get_stb_list: %s",exc); return {}

    def get_last_result(self):
        with self._lock: return dict(self._last_result)

    def get_last_error(self):
        with self._lock: return self._last_error

    def shutdown(self): self._running=False

    def _dispatch_loop(self):
        while self._running:
            item=None
            with self._lock:
                if self._queue: item=self._queue.pop(0)
            if item is None: time.sleep(0.02); continue
            self._fire(*item)

    def _fire(self,button,delay_ms):
        url=f"{self.host}/auto/{self.remote}/{self.stb}/{button}/{delay_ms}"
        try:
            r=requests.get(url,timeout=COMMAND_TIMEOUT)
            ct=r.headers.get("content-type","")
            result=r.json() if "json" in ct else {"raw":r.text}
            with self._lock: self._last_result=result; self._last_error=""
        except requests.exceptions.ConnectionError:
            err=f"JAMboreeLite unreachable at {self.host}"
            with self._lock: self._last_error=err
        except Exception as exc:
            with self._lock: self._last_error=str(exc)

_default=None
def get_controller(host=JAM_HOST,stb=DEFAULT_STB,remote=DEFAULT_REMOTE):
    global _default
    if _default is None: _default=JAMController(host=host,stb=stb,remote=remote)
    return _default
