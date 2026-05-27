#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import threading, time, logging
from typing import Optional
import cv2, numpy as np

log = logging.getLogger("nmb.capture_card")
CAPTURE_INDEX   = 0
CAPTURE_BACKEND = cv2.CAP_DSHOW
CAPTURE_WIDTH   = 1280
CAPTURE_HEIGHT  = 720
CAPTURE_FPS     = 30
PREFERRED_SIZES = [(1920,1080),(1280,720),(960,540),(640,480)]

class CaptureCardSource:
    def __init__(self):
        self._lock=threading.RLock(); self._cap=None
        self._latest_frame=None; self._latest_jpeg=None
        self._running=False; self._enabled=False
        self._status="idle"; self._last_error=""
        self._frame_count=0; self._open_count=0
        self._fail_streak=0; self._thread=None
        self._actual_size=(0,0); self._actual_backend="UNKNOWN"

    def start(self):
        with self._lock:
            if self._running:
                self._enabled=True; self._status="starting"; return
            self._running=True; self._enabled=True; self._status="starting"
            self._thread=threading.Thread(target=self._loop,daemon=True,name="CC-Loop")
            self._thread.start()

    def stop(self):
        with self._lock:
            self._enabled=False; self._status="idle"; self._release_locked()

    def get_latest_frame(self):
        with self._lock:
            f=self._latest_frame; return f.copy() if f is not None else None

    def get_latest_jpeg(self):
        with self._lock: return self._latest_jpeg

    def get_status(self):
        with self._lock:
            return {"status":self._status,"last_error":self._last_error,
                    "frame_count":self._frame_count,"open_count":self._open_count,
                    "actual_size":self._actual_size,"actual_backend":self._actual_backend,
                    "enabled":self._enabled}

    def _release_locked(self):
        if self._cap is not None:
            try: self._cap.release()
            except: pass
            self._cap=None

    def _open_locked(self):
        self._release_locked()
        for w,h in [(CAPTURE_WIDTH,CAPTURE_HEIGHT)]+[s for s in PREFERRED_SIZES if s!=(CAPTURE_WIDTH,CAPTURE_HEIGHT)]:
            cap=cv2.VideoCapture(CAPTURE_INDEX,CAPTURE_BACKEND)
            if not cap.isOpened():
                try: cap.release()
                except: pass
                continue
            cap.set(cv2.CAP_PROP_FRAME_WIDTH,w); cap.set(cv2.CAP_PROP_FRAME_HEIGHT,h)
            cap.set(cv2.CAP_PROP_FPS,CAPTURE_FPS)
            ok,frame=False,None
            for _ in range(15):
                ret,frm=cap.read()
                if ret and frm is not None and frm.size>0:
                    ok,frame=True,frm; break
                time.sleep(0.08)
            if ok and frame is not None:
                self._cap=cap; self._open_count+=1; self._fail_streak=0
                self._status="streaming"
                self._actual_size=(int(frame.shape[1]),int(frame.shape[0]))
                try: self._actual_backend=cap.getBackendName()
                except: self._actual_backend="DSHOW"
                self._store_frame_locked(frame); return True
            try: cap.release()
            except: pass
        self._status="error"
        self._last_error=f"Cannot open capture card index={CAPTURE_INDEX} DSHOW"
        return False

    def _store_frame_locked(self,frame):
        self._latest_frame=frame
        ok,buf=cv2.imencode(".jpg",frame,[int(cv2.IMWRITE_JPEG_QUALITY),85])
        if ok: self._latest_jpeg=buf.tobytes()
        self._frame_count+=1

    def _loop(self):
        while True:
            with self._lock:
                if not self._running: break
                enabled=self._enabled; has_cap=self._cap is not None
            if not enabled: time.sleep(0.15); continue
            if not has_cap:
                with self._lock: self._open_locked()
                time.sleep(0.1); continue
            with self._lock: cap=self._cap
            try: ret,frame=cap.read()
            except Exception as exc:
                with self._lock:
                    self._last_error=f"read exc: {exc}"; self._status="error"; self._cap=None
                time.sleep(0.5); continue
            if ret and frame is not None and frame.size>0:
                with self._lock:
                    self._fail_streak=0; self._status="streaming"; self._store_frame_locked(frame)
                time.sleep(0.01); continue
            with self._lock: self._fail_streak+=1; streak=self._fail_streak
            if streak<8: time.sleep(0.08); continue
            with self._lock: self._status="reconnecting"; self._release_locked()
            time.sleep(1.0)

capture_source=CaptureCardSource()
def start(): capture_source.start()
def stop(): capture_source.stop()
def get_latest_frame(): return capture_source.get_latest_frame()
def get_latest_jpeg(): return capture_source.get_latest_jpeg()
def get_status(): return capture_source.get_status()
