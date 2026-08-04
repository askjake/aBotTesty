# --- jamboree/stb_store.py ---
"""Thin wrapper around *base.txt* so code stays tidy.

v39 hardening (2026-08-03)
--------------------------
``save()`` used to do ``self._data = new_json`` and then dump the result, so a
caller that passed ``{"stbs": ...}`` -- which is what ``ip_recovery`` and the
settops UI both did -- silently deleted every other top-level key and any STB
field it had not bothered to copy forward.  That is how SGS pairing credentials
went missing after an IP-recovery cycle.

Writes now go through :mod:`jamboree.base_io`, which is additive, atomic and
keeps a ``.bak`` snapshot.  ``save()`` keeps its old signature for
backwards-compatibility but is now a **deep merge** rather than a replace.
Callers that genuinely need to delete an alias must say so explicitly via
:meth:`replace_stbs` or :meth:`remove`.
"""
import threading
from typing import Any, Dict, Iterable, Mapping, Optional

from . import base_io
from .paths import BASE_PATH

_lock = threading.RLock()


class STBStore:
    def __init__(self, path: object = BASE_PATH) -> None:
        self.path = path
        self._data: Dict[str, Any] = {}
        self.reload()

    # public access -------------------------------------------------------
    def all(self) -> Dict[str, Any]:
        return self._data.get("stbs", {})

    def get(self, name: str) -> Optional[Dict[str, Any]]:
        return self.all().get(name)

    def document(self) -> Dict[str, Any]:
        """The whole base.txt document, including non-``stbs`` top-level keys."""
        return dict(self._data)

    # writes --------------------------------------------------------------
    def save(self, new_json: dict) -> Dict[str, Any]:
        """Deep-merge ``new_json`` into base.txt (additive; never deletes).

        Historically this replaced the document.  Every existing caller passes a
        partial document, so merging is both safe and what they actually meant.
        """
        with _lock:
            self._data = base_io.merge_document(self.path, new_json or {})
            return self._data

    def update_stb(self, alias: str, fields: Mapping[str, Any], *, create: bool = True) -> Dict[str, Any]:
        """Update/add individual fields on one STB entry.  Preferred API."""
        with _lock:
            self._data = base_io.update_stb_fields(self.path, alias, dict(fields), create=create)
            return self._data

    def update_top(self, fields: Mapping[str, Any]) -> Dict[str, Any]:
        """Update/add top-level keys such as ``default_stb``."""
        with _lock:
            self._data = base_io.merge_document(self.path, dict(fields))
            return self._data

    def set_credentials(self, alias: str, login: str, passwd: str, **extra: Any) -> Dict[str, Any]:
        """Persist SGS pairing credentials for ``alias`` without touching anything else."""
        payload: Dict[str, Any] = {"lname": str(login), "passwd": str(passwd), "prod": True}
        payload.update(extra)
        return self.update_stb(alias, payload)

    def credentials(self, alias: str) -> Optional[tuple]:
        entry = self.get(alias) or {}
        login, passwd = entry.get("lname"), entry.get("passwd")
        return (str(login), str(passwd)) if login and passwd else None

    def replace_stbs(self, stbs: Mapping[str, Mapping[str, Any]]) -> Dict[str, Any]:
        """Replace the STB table (allows deletion) while protecting credentials.

        This is the path the settops editor uses: the browser posts the whole
        table, so removals must take effect, but the form does not render
        ``lname``/``passwd``/``com_port`` and must not blank them.
        """
        with _lock:
            self._data = base_io.replace_stb_table(self.path, stbs)
            return self._data

    def remove(self, aliases: Iterable[str]) -> Dict[str, Any]:
        with _lock:
            self._data = base_io.prune_aliases(self.path, aliases)
            return self._data

    def reload(self) -> Dict[str, Any]:
        with _lock:
            if not self.path.exists():
                raise FileNotFoundError(f"base file not found: {self.path}")
            self._data = base_io.read_document(self.path)
            return self._data


store = STBStore()
