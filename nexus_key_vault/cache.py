"""Responses kept on disk, so a second scan does not re-ask Nexus.

The quota belongs to the user, and several plugins now share one key, so
a plugin sweeping nine hundred mods can spend an allowance that MO2 and
everything else then has to do without.  Caching here rather than in each
plugin means two plugins asking about the same mod cost one request
between them, which is the part a private cache cannot do.

What is cached is metadata - names, categories, requirements.  Nothing
secret, and deliberately nothing about the credential: the cache key is
built from the request alone, so the same file is valid whichever key
fetched it, and a key never reaches this module at all.

Lifetimes are per kind, because the data ages at wildly different rates.
A game's category table changes about once a year; a mod's requirements
change whenever the author edits the page.  So:

    game        30 days   a game's id and category table
    mod         24 hours  names, versions, categories, requirements
    raw          1 hour   whatever a caller asked for directly

Only successful reads are stored.  A 404 is kept as a tombstone, briefly,
so a deleted mod page is not re-requested once per mod per run - but 401,
403, 429, a server error and a dropped connection are never cached,
because caching those would turn a passing problem into a lasting one.
"""

from __future__ import annotations

import hashlib
import json
import os
import time

FILENAME = "nexus_cache.json"
VERSION = 1

DAY = 86400.0
TTL = {
    "game": 30 * DAY,
    "mod": DAY,
    "raw": 3600.0,
}
MISS_TTL = 6 * 3600.0          # how long a 404 is remembered
MAX_ENTRIES = 20000            # roughly a large modlist, several times over


def _key(kind: str, material: str) -> str:
    """A stable id for one request. Never includes the API key."""
    digest = hashlib.sha256(
        "{}\x00{}".format(kind, material).encode("utf-8")).hexdigest()
    return digest[:32]


class Cache:
    """A small JSON store. Cheap to construct, safe to share."""

    def __init__(self, path: str, max_entries: int = MAX_ENTRIES) -> None:
        self.path = path
        self.max_entries = max_entries
        self.entries: dict[str, dict] = {}
        self.hits = 0
        self.misses = 0
        self._dirty = False
        self._load()

    # ---- the file ------------------------------------------------------

    def _load(self) -> None:
        try:
            with open(self.path, "r", encoding="utf-8") as fh:
                raw = json.load(fh)
        except (OSError, ValueError):
            return
        if raw.get("version") != VERSION:
            return                      # a format change starts over
        now = time.time()
        for key, entry in (raw.get("entries") or {}).items():
            if isinstance(entry, dict) and entry.get("until", 0) > now:
                self.entries[str(key)] = entry

    def save(self) -> None:
        """Write if anything changed. Callers may forget; nothing breaks."""
        if not self._dirty:
            return
        self.prune()
        folder = os.path.dirname(self.path)
        if folder:
            os.makedirs(folder, exist_ok=True)
        temp = self.path + ".new"
        try:
            with open(temp, "w", encoding="utf-8") as fh:
                json.dump({"version": VERSION, "entries": self.entries}, fh)
            os.replace(temp, self.path)
            self._dirty = False
        except OSError:
            # A cache that cannot be written is a slow cache, not a broken
            # plugin. Whatever is in memory still serves this run.
            pass

    def prune(self) -> None:
        now = time.time()
        self.entries = {k: v for k, v in self.entries.items()
                        if v.get("until", 0) > now}
        if len(self.entries) > self.max_entries:
            # Drop whatever expires soonest; it is the cheapest to refetch.
            keep = sorted(self.entries.items(),
                          key=lambda kv: kv[1].get("until", 0),
                          reverse=True)[:self.max_entries]
            self.entries = dict(keep)

    def clear(self) -> None:
        self.entries = {}
        self._dirty = True
        self.save()
        try:
            if not self.entries and os.path.exists(self.path):
                os.remove(self.path)
        except OSError:
            pass

    # ---- using it ------------------------------------------------------

    def get(self, kind: str, material: str):
        """``(hit, value)``. A cached 404 is ``(True, None)``."""
        entry = self.entries.get(_key(kind, material))
        if not entry or entry.get("until", 0) <= time.time():
            self.misses += 1
            return False, None
        self.hits += 1
        return True, entry.get("value")

    def put(self, kind: str, material: str, value, ttl: float | None = None) -> None:
        if ttl is None:
            ttl = TTL.get(kind, TTL["raw"])
        self.entries[_key(kind, material)] = {
            "until": time.time() + ttl,
            "value": value,
        }
        self._dirty = True

    def put_missing(self, kind: str, material: str) -> None:
        """Remember a 404 briefly, so it is asked once and not per run."""
        self.put(kind, material, None, MISS_TTL)

    @property
    def size(self) -> int:
        return len(self.entries)

    def summary(self) -> str:
        total = self.hits + self.misses
        if not total:
            return "{} cached responses".format(self.size)
        return "{} cached responses, {}% of lookups served from disk".format(
            self.size, int(round(100.0 * self.hits / total)))
