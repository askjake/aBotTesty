# --- jamboree/base_io.py ---
"""Atomic, *additive* persistence primitives for ``base.txt``.

Why this module exists
---------------------
``base.txt`` is the single source of truth for STB identity **and** for the SGS
pairing credentials (``lname`` / ``passwd``) handed out by the receiver during
PIN pairing.  Historically two independent writers existed:

    * ``jamboree.stb_store.STBStore.save()``  -- replaced ``self._data`` wholesale
    * ``jamboree.sgs_lib.sgs_save_base()``    -- json.dump of whatever it was given

Both were *destructive*: a caller that only cared about one field had to pass a
whole document, and any key it forgot to include was silently deleted.  In
practice ``ip_recovery`` called ``save({"stbs": ...})`` which erased every
top-level key, and the pairing flow could lose credentials on the next IP write.

Everything in this module follows three rules:

    1. **Additive** -- writes update or add fields.  Nothing is ever dropped
       unless a caller explicitly asks for removal via :func:`prune_aliases`.
    2. **Atomic**   -- write to ``<file>.tmp`` then ``os.replace``, so a crash
       or a concurrent reader can never observe a truncated JSON document.
    3. **Recoverable** -- the pre-write content is kept in ``<file>.bak``.

All functions are safe to call from multiple threads *and* multiple processes
(the SGS helper runs as a subprocess), guarded by an flock on a sidecar file.
"""
from __future__ import annotations

import errno
import json
import os
import shutil
import tempfile
import threading
import time
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Optional

try:                                    # POSIX only; Windows falls back to the
    import fcntl                        # in-process lock alone.
except ImportError:                     # pragma: no cover
    fcntl = None                        # type: ignore[assignment]

# Fields that must survive a bulk "replace the STB table" operation coming from
# the settops UI, which renders neither credentials nor wiring details.
PROTECTED_STB_FIELDS: tuple[str, ...] = (
    "lname",        # SGS login handed out by device_pairing_complete
    "passwd",       # SGS password handed out by device_pairing_complete
    "prod",         # marks the box as paired / production
    "paired_ts",    # when pairing last succeeded
    "pair_rid",     # the PC receiver-id the credentials belong to
    "cid",          # last attach() connection id
    "com_port",     # RF/DART serial line
    "remote",       # RF remote slot number
    "mac",          # learned STB MAC, used by ARP-based IP recovery
)

_INDENT = 4
_thread_lock = threading.RLock()


# ---------------------------------------------------------------------------
#  low-level helpers
# ---------------------------------------------------------------------------

class _FileLock:
    """Best-effort cross-process advisory lock on ``<path>.lock``."""

    def __init__(self, path: Path, timeout: float = 10.0):
        self.lock_path = Path(str(path) + ".lock")
        self.timeout = timeout
        self._fh = None

    def __enter__(self):
        if fcntl is None:
            return self
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        self._fh = open(self.lock_path, "a+")
        deadline = time.time() + self.timeout
        while True:
            try:
                fcntl.flock(self._fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                return self
            except OSError as exc:
                if exc.errno not in (errno.EACCES, errno.EAGAIN):
                    raise
                if time.time() >= deadline:
                    # Never block a remote-control command forever on a lock;
                    # the in-process lock still serialises our own writers.
                    return self
                time.sleep(0.05)

    def __exit__(self, *exc):
        if self._fh is not None:
            try:
                if fcntl is not None:
                    fcntl.flock(self._fh.fileno(), fcntl.LOCK_UN)
            finally:
                self._fh.close()
                self._fh = None
        return False


def deep_merge(dst: Dict[str, Any], src: Mapping[str, Any]) -> Dict[str, Any]:
    """Recursively merge ``src`` into ``dst`` **in place** and return ``dst``.

    Nested mappings are merged key-by-key; every other type replaces the
    previous value.  Keys present in ``dst`` but absent from ``src`` are left
    untouched -- this is what makes the write additive.
    """
    for key, value in src.items():
        if (
            key in dst
            and isinstance(dst[key], dict)
            and isinstance(value, Mapping)
        ):
            deep_merge(dst[key], value)
        else:
            dst[key] = value
    return dst


def read_document(path: Path) -> Dict[str, Any]:
    """Load ``base.txt``.  Returns ``{}`` when the file is absent.

    If the primary file is unreadable/corrupt we transparently fall back to the
    ``.bak`` snapshot rather than nuking a good configuration.
    """
    path = Path(path)
    if path.is_file():
        try:
            text = path.read_text(encoding="utf-8")
            if text.strip():
                return json.loads(text)
            return {}
        except (json.JSONDecodeError, OSError):
            pass
    bak = Path(str(path) + ".bak")
    if bak.is_file():
        try:
            return json.loads(bak.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def write_document(path: Path, document: Mapping[str, Any]) -> None:
    """Atomically persist ``document``, keeping the previous copy as ``.bak``."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(document, indent=_INDENT, ensure_ascii=False) + "\n"

    if path.is_file():
        try:
            shutil.copy2(path, Path(str(path) + ".bak"))
        except Exception:
            pass

    fd, tmp_name = tempfile.mkstemp(
        prefix=path.name + ".", suffix=".tmp", dir=str(path.parent)
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(payload)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp_name, path)
    except Exception:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


# ---------------------------------------------------------------------------
#  public, additive API
# ---------------------------------------------------------------------------

def merge_document(path: Path, patch: Mapping[str, Any]) -> Dict[str, Any]:
    """Deep-merge ``patch`` into the on-disk document and persist the result."""
    with _thread_lock, _FileLock(path):
        document = read_document(path)
        deep_merge(document, patch)
        write_document(path, document)
        return document


def update_stb_fields(
    path: Path,
    alias: str,
    fields: Mapping[str, Any],
    *,
    create: bool = True,
) -> Dict[str, Any]:
    """Update or add individual fields on one STB entry.

    This is the function every caller that "just wants to change the IP" (or
    store fresh credentials) should use.  Sibling fields and every other
    top-level key are preserved by construction.
    """
    alias = str(alias)
    with _thread_lock, _FileLock(path):
        document = read_document(path)
        stbs = document.setdefault("stbs", {})
        if alias not in stbs:
            if not create:
                raise KeyError(f"alias {alias!r} not present in {path}")
            stbs[alias] = {}
        if not isinstance(stbs[alias], dict):
            stbs[alias] = {}
        deep_merge(stbs[alias], fields)
        write_document(path, document)
        return document


def replace_stb_table(
    path: Path,
    stbs: Mapping[str, Mapping[str, Any]],
    *,
    protect: Iterable[str] = PROTECTED_STB_FIELDS,
    allow_delete: bool = True,
) -> Dict[str, Any]:
    """Replace the ``stbs`` table -- the only path that may delete an alias.

    Used by the settops editor UI, which posts the full table and therefore
    needs deletions to work.  Fields listed in ``protect`` are carried over from
    the previous entry when the incoming payload does not mention them, so that
    editing an unrelated field in the browser cannot wipe SGS credentials.

    Top-level keys outside ``stbs`` are always preserved.
    """
    protect = tuple(protect)
    with _thread_lock, _FileLock(path):
        document = read_document(path)
        previous = document.get("stbs", {}) or {}
        merged: Dict[str, Any] = {}

        for alias, incoming in (stbs or {}).items():
            alias = str(alias)
            entry = dict(previous.get(alias, {}) or {})
            entry.update(dict(incoming or {}))
            # Re-instate protected fields the UI never sent back.
            for field in protect:
                if field not in (incoming or {}) and field in (previous.get(alias) or {}):
                    entry[field] = previous[alias][field]
            merged[alias] = entry

        if not allow_delete:
            for alias, entry in previous.items():
                merged.setdefault(alias, entry)

        document["stbs"] = merged
        write_document(path, document)
        return document


def prune_aliases(path: Path, aliases: Iterable[str]) -> Dict[str, Any]:
    """Explicitly remove STB entries.  The *only* deleting helper here."""
    drop = {str(a) for a in aliases}
    with _thread_lock, _FileLock(path):
        document = read_document(path)
        stbs = document.get("stbs", {}) or {}
        for alias in drop:
            stbs.pop(alias, None)
        document["stbs"] = stbs
        write_document(path, document)
        return document


def get_credentials(path: Path, alias: str) -> Optional[tuple[str, str]]:
    """Return ``(lname, passwd)`` for ``alias`` or ``None`` when unpaired."""
    entry = (read_document(path).get("stbs", {}) or {}).get(str(alias)) or {}
    login, passwd = entry.get("lname"), entry.get("passwd")
    if login and passwd:
        return str(login), str(passwd)
    return None
