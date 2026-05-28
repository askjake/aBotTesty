#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import tempfile
import threading
from pathlib import Path
from typing import Any, Dict

_LOCKS: Dict[str, threading.RLock] = {}
_LOCKS_GUARD = threading.RLock()


def _lock_for(path: Path) -> threading.RLock:
    key = str(path.resolve())
    with _LOCKS_GUARD:
        lock = _LOCKS.get(key)
        if lock is None:
            lock = threading.RLock()
            _LOCKS[key] = lock
        return lock


def atomic_write_text(path: str | Path, text: str, encoding: str = "utf-8") -> None:
    """Thread-safe atomic write with a unique temp file per writer.

    Fixes races where two threads both use nav_graph.tmp or learned_sequences.tmp.
    """
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)

    lock = _lock_for(target)
    with lock:
        fd = None
        tmp_name = ""
        try:
            fd, tmp_name = tempfile.mkstemp(
                prefix=f".{target.name}.{os.getpid()}.{threading.get_ident()}.",
                suffix=".tmp",
                dir=str(target.parent),
                text=True,
            )
            with os.fdopen(fd, "w", encoding=encoding) as f:
                fd = None
                f.write(text)
                f.flush()
                os.fsync(f.fileno())

            os.replace(tmp_name, target)

            # Best-effort directory fsync so rename is durable on Linux.
            try:
                dfd = os.open(str(target.parent), os.O_DIRECTORY)
                try:
                    os.fsync(dfd)
                finally:
                    os.close(dfd)
            except Exception:
                pass

        finally:
            if fd is not None:
                try:
                    os.close(fd)
                except Exception:
                    pass
            if tmp_name:
                try:
                    Path(tmp_name).unlink(missing_ok=True)
                except Exception:
                    pass


def atomic_write_json(path: str | Path, payload: Any, *, compact: bool = False, indent: int = 2) -> None:
    if compact:
        text = json.dumps(payload, separators=(",", ":"))
    else:
        text = json.dumps(payload, indent=indent)
    atomic_write_text(path, text, encoding="utf-8")
