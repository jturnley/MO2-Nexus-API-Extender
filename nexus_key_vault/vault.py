"""The key on disk, and the record of who has asked for it.

One file, ``nexus_key.dat``, next to the plugin's other data.  Everything
in it except the key itself is plain, because none of it is secret and a
user opening the file to see what this plugin has been doing should be
able to read it.

How the key is sealed depends on what the platform can honestly support,
and the file records which was used so the dialog never overstates it:

    dpapi                real Windows.  The OS holds the secret.
    portable-passphrase  the user's passphrase, stretched with scrypt.
    portable-machine     obfuscation tied to this machine and folder.
                         Called that everywhere, because it is not
                         encryption in any sense worth the word.

The last one is the Wine default.  See :mod:`portable` for why Wine's own
DPAPI is refused rather than trusted.

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

from . import dpapi, portable

FILENAME = "nexus_key.dat"
VERSION = 2

DPAPI = "dpapi"
MACHINE = portable.NAMES[portable.SCHEME_MACHINE]
PASSPHRASE = portable.NAMES[portable.SCHEME_PASSPHRASE]

# What the file says about itself, matched to how it was actually sealed.
NOTES = {
    DPAPI: "The key is encrypted by Windows for this user account. "
           "Copying this file to another account or machine will not "
           "carry the key with it.",
    PASSPHRASE: "The key is encrypted with a passphrase only the user "
                "knows. Without it this file cannot be opened, here or "
                "anywhere else.",
    MACHINE: "The key is obfuscated, not encrypted: it is tied to this "
             "machine, account and folder, so moving this file elsewhere "
             "makes it useless - but anyone who reads the plugin's source "
             "can open it in place. Use a passphrase if that matters.",
}

# How the same thing reads in a sentence to the user.
PROTECTION = {
    DPAPI: "encrypted by Windows for this user account",
    PASSPHRASE: "encrypted with your passphrase",
    MACHINE: "obfuscated for this machine and folder - not encryption",
}


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
    """There is a key on disk and it cannot be opened here."""


class NeedsPassphrase(Locked):
    """Sealed with a passphrase, and none was given."""


def best_scheme() -> str:
    """What this platform can support without claiming too much."""
    return DPAPI if dpapi.available() else MACHINE


def can_store() -> bool:
    """Is there any way to store a key here that is not plain text."""
    return True     # portable always works; it is the claim that varies


class Vault:
    """Read and write the one file. Cheap to construct, never cached."""

    def __init__(self, path: str, passphrase: str = "") -> None:
        self.path = path
        self.asked: dict[str, dict] = {}
        self._sealed: bytes = b""
        self._scheme: str = best_scheme()
        self._passphrase = passphrase or ""
        # Set when a key stored by an older version under Wine had to be
        # re-wrapped; the dialog tells the user, because it means their
        # key was weaker on disk than the old version claimed.
        self.rewrapped = False
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
        # Version 1 predates portable sealing, so it can only be DPAPI.
        scheme = raw.get("scheme") or DPAPI
        self._scheme = scheme if scheme in PROTECTION else DPAPI
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
            "scheme": self._scheme,
            "note": NOTES[self._scheme],
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

    # ---- describing itself ---------------------------------------------

    @property
    def scheme(self) -> str:
        return self._scheme

    def protection(self) -> str:
        """One phrase for the dialog. Never stronger than the truth."""
        return PROTECTION.get(self._scheme, "stored")

    @property
    def needs_passphrase(self) -> bool:
        return self._scheme == PASSPHRASE and not self._passphrase

    def use_passphrase(self, passphrase: str) -> None:
        """Hand over the passphrase for this session only."""
        self._passphrase = passphrase or ""

    # ---- the key -------------------------------------------------------

    @property
    def has_key(self) -> bool:
        return bool(self._sealed)

    def _material(self) -> bytes:
        if self._scheme == PASSPHRASE:
            return self._passphrase.encode("utf-8")
        return portable.machine_material(self.path)

    def read(self) -> str:
        """The key in plain, or "" if there is none stored.

        Raises :class:`Locked` when a key is present but cannot be opened
        here - a different Windows user, a file carried over from another
        machine, or a missing passphrase.  That is worth telling apart
        from "no key", because the fix is different.
        """
        if not self._sealed:
            return ""
        try:
            return self._open().decode("utf-8").strip()
        except UnicodeDecodeError as exc:
            raise Locked("The stored key is not readable.") from exc

    def _open(self) -> bytes:
        if self._scheme == DPAPI:
            return self._open_dpapi()
        if self.needs_passphrase:
            raise NeedsPassphrase(
                "This vault is protected with a passphrase. Enter it to "
                "unlock the key.")
        try:
            return portable.unseal(self._sealed, self._material())
        except (portable.Tampered, portable.WrongSecret) as exc:
            raise Locked(str(exc)) from exc

    def _open_dpapi(self) -> bytes:
        """Open a DPAPI blob, rescuing one written by an older Wine run.

        Under Wine the blob is readable but was never really protected,
        so it is re-wrapped immediately rather than left as it is.
        """
        if dpapi.available():
            try:
                return dpapi.unseal(self._sealed)
            except dpapi.Unavailable as exc:
                raise Locked(str(exc)) from exc
        if not dpapi.present():
            raise Locked(
                "This key was stored by Windows on another system and "
                "cannot be opened here. Remove it and enter the key again.")
        # Wine: readable, but only because it was never properly sealed.
        try:
            secret = dpapi.unseal_regardless(self._sealed)
        except dpapi.Unavailable as exc:
            raise Locked(str(exc)) from exc
        self._scheme = MACHINE if not self._passphrase else PASSPHRASE
        self._sealed = self._seal(secret)
        self._save()
        self.rewrapped = True
        return secret

    def _seal(self, secret: bytes) -> bytes:
        if self._scheme == DPAPI:
            return dpapi.seal(secret)
        scheme = (portable.SCHEME_PASSPHRASE if self._scheme == PASSPHRASE
                  else portable.SCHEME_MACHINE)
        return portable.seal(secret, self._material(), scheme)

    def store(self, key: str, passphrase: str = "") -> None:
        """Store a key, choosing the strongest scheme available.

        A passphrase always wins, on Windows too: someone who asks for one
        has decided they want protection that survives their account being
        opened, and that is theirs to decide.
        """
        key = (key or "").strip()
        if not key:
            raise ValueError("no key given")
        if passphrase:
            self._passphrase = passphrase
            self._scheme = PASSPHRASE
        else:
            self._scheme = best_scheme()
        self._sealed = self._seal(key.encode("utf-8"))
        self._save()

    def clear(self) -> None:
        self._sealed = b""
        self._scheme = best_scheme()
        self._passphrase = ""
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
