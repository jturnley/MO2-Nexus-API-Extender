"""The key on disk, and the record of who has asked for it.

One file, ``nexus_key.dat``, next to the plugin's other data.  The key
inside it is sealed with DPAPI (see :mod:`dpapi`); everything else in the
file is plain, because it is not secret and a user opening the file to see
what this plugin has been doing should be able to read it.

The ``asked`` section is an audit, not a permission system.  A caller that
wanted the key without being listed could simply not call this module, so
treating the list as enforcement would be a lie told in a dialog box.  What
it honestly gives is a user who can see that four plugins have asked for
their credential and when - and a deny entry that stops the well-behaved
majority, which is every plugin that uses the published API.
"""

from __future__ import annotations

import base64
import json
import os
import time

from . import dpapi

FILENAME = "nexus_key.dat"
VERSION = 1


def masked(key: str, tail: int = 4) -> str:
    """A key described rather than shown.

    Enough to tell two apart and to confirm one arrived intact; not enough
    to use.  Short keys give up the tail too, so nothing is "described" by
    handing back most of itself.
    """
    key = (key or "").strip()
    if not key:
        return ""
    if len(key) <= tail * 2:
        return "{} characters".format(len(key))
    return "{} characters, ending {}".format(len(key), key[-tail:])


class Locked(Exception):
    """There is a key on disk and this account cannot open it."""


class Vault:
    """Read and write the one file. Cheap to construct, never cached."""

    def __init__(self, path: str) -> None:
        self.path = path
        self.asked: dict[str, dict] = {}
        self._sealed: bytes = b""
        self._load()

    # ---- the file ------------------------------------------------------

    def _load(self) -> None:
        try:
            with open(self.path, "r", encoding="utf-8") as fh:
                raw = json.load(fh)
        except (OSError, ValueError):
            return
        try:
            self._sealed = base64.b64decode(raw.get("key") or "")
        except (ValueError, TypeError):
            self._sealed = b""
        for name, entry in (raw.get("asked") or {}).items():
            if isinstance(entry, dict):
                self.asked[str(name)] = {
                    "first": float(entry.get("first") or 0),
                    "last": float(entry.get("last") or 0),
                    "count": int(entry.get("count") or 0),
                    "allowed": bool(entry.get("allowed", True)),
                }

    def _save(self) -> None:
        payload = {
            "version": VERSION,
            "note": "The key is encrypted for this Windows user account. "
                    "Copying this file to another account or machine will "
                    "not carry the key with it.",
            "key": base64.b64encode(self._sealed).decode("ascii"),
            "asked": self.asked,
        }
        folder = os.path.dirname(self.path)
        if folder:
            os.makedirs(folder, exist_ok=True)
        # Write beside and rename, so an interrupted save cannot leave a
        # half-written file where the key used to be.
        temp = self.path + ".new"
        with open(temp, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=1)
        os.replace(temp, self.path)

    # ---- the key -------------------------------------------------------

    @property
    def has_key(self) -> bool:
        return bool(self._sealed)

    def read(self) -> str:
        """The key in plain, or "" if there is none stored.

        Raises :class:`Locked` when a key is present but this account
        cannot decrypt it - a different Windows user, or a file carried
        over from another machine.  That is worth telling apart from
        "no key", because the fix is different.
        """
        if not self._sealed:
            return ""
        try:
            return dpapi.unseal(self._sealed).decode("utf-8").strip()
        except dpapi.Unavailable as exc:
            raise Locked(str(exc)) from exc
        except UnicodeDecodeError as exc:
            raise Locked("The stored key is not readable.") from exc

    def store(self, key: str) -> None:
        key = (key or "").strip()
        if not key:
            raise ValueError("no key given")
        self._sealed = dpapi.seal(key.encode("utf-8"))
        self._save()

    def clear(self) -> None:
        self._sealed = b""
        self._save()

    # ---- who asked -----------------------------------------------------

    def allowed(self, requester: str) -> bool:
        return bool(self.asked.get(requester, {}).get("allowed", True))

    def note(self, requester: str) -> None:
        """Record a request. Called on every read, so it stays cheap."""
        requester = (requester or "unnamed plugin").strip()
        now = time.time()
        entry = self.asked.setdefault(
            requester, {"first": now, "last": now, "count": 0,
                        "allowed": True})
        entry["last"] = now
        entry["count"] = int(entry.get("count") or 0) + 1
        self._save()

    def set_allowed(self, requester: str, allowed: bool) -> None:
        entry = self.asked.get(requester)
        if entry is None:
            now = time.time()
            entry = self.asked[requester] = {
                "first": now, "last": now, "count": 0, "allowed": True}
        entry["allowed"] = bool(allowed)
        self._save()

    def forget(self, requester: str) -> None:
        self.asked.pop(requester, None)
        self._save()
