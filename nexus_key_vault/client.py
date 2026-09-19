"""A Nexus client other plugins can borrow, with the key already in it.

Two APIs, and the difference matters when you are deciding which to call:

    v2 GraphQL   the current one, and where the data actually is:
                 requirements, per-file records, collections.  Public
                 queries need no credential at all.  Send the key anyway
                 when there is one - it is what makes user-scoped fields
                 answer, and it costs nothing.

    v1 REST      older and much narrower, but still the only place some
                 things live (a game's category table, endorsements).
                 Every request needs an `apikey` header, which is the
                 main reason a plugin wants a key at all.

They bill against separate quotas, so spending v2 requests does not eat
into what MO2's own Nexus features have left.

Nothing here caches.  A caller who is about to ask about nine hundred mods
wants a cache shaped like their own problem, and one built into a shared
client would be the wrong shape for everybody.
"""

from __future__ import annotations

import contextlib
import json
import time
import urllib.error
import urllib.request

GRAPHQL = "https://api.nexusmods.com/v2/graphql"
REST = "https://api.nexusmods.com/v1"
V3 = "https://api.nexusmods.com/v3"
TIMEOUT = 15.0
# Nexus allows 100 requests a minute on v1. Stay clear of it: the quota
# belongs to the user, and MO2 needs its share after the plugin is done.
PAUSE = 0.35


class NexusError(Exception):
    """A request failed. The message never contains the key."""

    def __init__(self, message: str, status: int | None = None) -> None:
        super().__init__(message)
        self.status = status


def explain(exc: Exception) -> str:
    """What went wrong, in words, without quoting the credential back.

    Some urllib errors carry the requested URL in their string form.  The
    key travels in a header rather than the URL today, but building the
    message from the status code instead means that stays true whatever a
    later refactor does with it.
    """
    status = getattr(exc, "status", None) or getattr(exc, "code", None)
    if status == 401:
        return "Nexus rejected the key (401). Check it was copied in full."
    if status == 403:
        return "Nexus refused the request (403)."
    if status == 404:
        return "Nexus has no such record (404)."
    if status == 429:
        return "Too many requests for now (429) - wait and try again."
    if status:
        return "Nexus answered {}.".format(status)
    if isinstance(exc, (urllib.error.URLError, OSError, TimeoutError)):
        return "Could not reach Nexus. Check the connection."
    return exc.__class__.__name__


class NexusClient:
    """Thin, honest, and safe to hold on to for the length of one job."""

    def __init__(self, key: str = "", user_agent: str = "MO2-Plugin/1.0",
                 timeout: float = TIMEOUT, cache=None) -> None:
        self.key = (key or "").strip()
        self.user_agent = user_agent
        self.timeout = timeout
        self.cache = cache
        # When set, cached answers are ignored and whatever comes back
        # replaces them. See refreshing().
        self.refresh = False
        # What Nexus last said is left of the user's allowance. The key is
        # shared, so the quota is too: a plugin that drains it takes MO2's
        # downloads and every other plugin down with it.
        self.rate_limit: dict[str, int] = {}
        self._last = 0.0

    @contextlib.contextmanager
    def refreshing(self, on: bool = True):
        """Ignore cached answers inside this block, and replace them.

            with nexus.refreshing():
                fresh = nexus.mod(game, mod_id)

        For when a user has asked for an answer rather than merely needing
        one - a Refresh button, or a re-check of something they just
        changed on Nexus. Stale-but-fast is the right default for a
        background sweep and the wrong one for an explicit request.

        This is a refresh, not a bypass: the result is written back, so
        the next caller gets the new answer rather than the old one. A
        plugin that wants no caching at all should ask for its client
        with ``cache=False`` instead.

        Restores the previous setting on the way out, including after an
        exception, so a client shared across a session cannot be left
        permanently refreshing by a failed run.

        Scope it as tightly as you can. Wrapping a whole modlist sweep in
        this asks Nexus for hundreds of records it already had, which is
        the cost the cache exists to avoid.
        """
        was = self.refresh
        self.refresh = bool(on)
        try:
            yield self
        finally:
            self.refresh = was

    def _cached(self, kind: str, material: str, fetch):
        """Serve from the cache, or fetch and store the result.

        Only successful reads and 404s are stored. A 401, a 429, a server
        error or a dropped connection is passed straight through: caching
        a transient failure would turn it into a lasting one.

        Under refresh the stored answer is skipped but still replaced, so
        a refresh that fails leaves the old answer in place rather than
        emptying the cache and costing the next run as well.
        """
        if self.cache is None:
            return fetch()
        hit, value = (False, None) if self.refresh else self.cache.get(
            kind, material)
        if hit:
            if value is None:
                raise NexusError("Nexus has no such record (404).", 404)
            return value
        try:
            value = fetch()
        except NexusError as exc:
            if exc.status == 404:
                self.cache.put_missing(kind, material)
            raise
        self.cache.put(kind, material, value)
        return value

    @property
    def has_key(self) -> bool:
        return bool(self.key)

    def _wait(self) -> None:
        gap = time.time() - self._last
        if gap < PAUSE:
            time.sleep(PAUSE - gap)
        self._last = time.time()

    HEADERS = {"hourly": "x-rl-hourly-remaining",
               "daily": "x-rl-daily-remaining"}

    def _note_limits(self, headers) -> None:
        for name, header in self.HEADERS.items():
            value = headers.get(header)
            if value is None:
                continue
            try:
                self.rate_limit[name] = int(value)
            except (TypeError, ValueError):
                continue

    def remaining(self, which: str = "hourly") -> int | None:
        """Requests left in the allowance, or None if Nexus has not said.

        Only v1 reports this. A caller about to make hundreds of requests
        should check it and stop short rather than spend the last of a
        quota that is not really its own.
        """
        return self.rate_limit.get(which)

    def _open(self, request: urllib.request.Request):
        self._wait()
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as fh:
                self._note_limits(fh.headers)
                return json.load(fh)
        except urllib.error.HTTPError as exc:
            if getattr(exc, "headers", None):
                self._note_limits(exc.headers)
            raise NexusError(explain(exc), getattr(exc, "code", None)) from None
        except (urllib.error.URLError, OSError, TimeoutError) as exc:
            raise NexusError(explain(exc)) from None
        except ValueError as exc:
            raise NexusError("Nexus sent something unreadable.") from None

    # ---- v2 ------------------------------------------------------------

    @staticmethod
    def _is_read(query: str) -> bool:
        """True for a query, false for anything that could write.

        Conservative on purpose: a caller passing something this cannot
        recognise gets a live request rather than a cached answer.
        """
        head = (query or "").strip().lstrip("{").strip().lower()
        return head.startswith("query") or (query or "").strip().startswith("{")

    def graphql(self, query: str, variables: dict | None = None,
                cache: bool = True) -> dict:
        """Run a v2 GraphQL query and return its ``data`` block.

        Raises :class:`NexusError` if the server reports query errors, so
        a caller does not have to remember that GraphQL answers 200 with
        the failure inside the body.
        """
        if cache and self.cache is not None and self._is_read(query):
            material = json.dumps([query, variables or {}], sort_keys=True)
            return self._cached("raw", material,
                                lambda: self._graphql(query, variables))
        return self._graphql(query, variables)

    def _graphql(self, query: str, variables: dict | None = None) -> dict:
        body = {"query": query}
        if variables:
            body["variables"] = variables
        headers = {"Content-Type": "application/json",
                   "Accept": "application/json",
                   "User-Agent": self.user_agent}
        # The key is deliberately NOT sent on v2. It was, and it was not
        # harmless: v2's public half needs no credential and bills against
        # a different allowance from v1, so attaching a key moves a free
        # request onto the metered one - and a caller sweeping a modlist
        # can then exhaust an allowance MO2 needs for downloads. v2's
        # genuinely private half wants an OAuth token, which a key is not,
        # so authenticating here buys nothing to weigh against that.
        payload = self._open(urllib.request.Request(
            GRAPHQL, data=json.dumps(body).encode("utf-8"), headers=headers))
        errors = payload.get("errors")
        if errors:
            first = errors[0].get("message") if isinstance(errors[0], dict) \
                else str(errors[0])
            raise NexusError("Nexus rejected the query: {}".format(first))
        return payload.get("data") or {}

    def game_id(self, domain: str) -> int | None:
        return self._cached("game", "game_id/" + domain,
                            lambda: self._game_id(domain))

    def _game_id(self, domain: str) -> int | None:
        data = self.graphql(
            "query($d: String!) { game(domainName: $d) { id } }",
            {"d": domain})
        return ((data.get("game") or {}) or {}).get("id")

    def mod(self, game_id: int, mod_id: int) -> dict:
        """One mod's v2 record."""
        return self._cached("mod", "mod/{}/{}".format(game_id, mod_id),
                            lambda: self._mod(game_id, mod_id))

    def _mod(self, game_id: int, mod_id: int) -> dict:
        data = self.graphql(
            "query($g: ID!, $m: ID!) {"
            " mod(gameId: $g, modId: $m) {"
            "  modId name version adult modCategory { name }"
            " } }", {"g": game_id, "m": mod_id})
        return data.get("mod") or {}

    def requirements(self, game_id: int, mod_id: int) -> list[dict]:
        """What the mod page lists under Requirements.

        Not in v1 at all, which is the best single reason to talk to v2
        directly.  Note that requirements attached to a *file* rather than
        to the mod do not appear here - a mod can list three on its page
        and return none of them.
        """
        return self._cached(
            "mod", "requirements/{}/{}".format(game_id, mod_id),
            lambda: self._requirements(game_id, mod_id))

    def _requirements(self, game_id: int, mod_id: int) -> list[dict]:
        data = self.graphql(
            "query($g: ID!, $m: ID!) {"
            " mod(gameId: $g, modId: $m) {"
            "  modRequirements { nexusRequirements {"
            "   nodes { modId notes } } }"
            " } }", {"g": game_id, "m": mod_id})
        mod = data.get("mod") or {}
        block = (mod.get("modRequirements") or {}).get(
            "nexusRequirements") or {}
        return block.get("nodes") or []

    # ---- v1 ------------------------------------------------------------

    def rest(self, path: str) -> dict:
        """A v1 GET, e.g. ``games/skyrimspecialedition.json``.

        Always needs a key; raises :class:`NexusError` rather than firing
        a request that is certain to come back 401.
        """
        if not self.key:
            raise NexusError("The v1 API needs a key and none is stored.")
        return self._cached("raw", "v1/" + path.lstrip("/"),
                            lambda: self._open(urllib.request.Request(
                                "{}/{}".format(REST, path.lstrip("/")),
                                headers={"apikey": self.key,
                                         "Accept": "application/json",
                                         "User-Agent": self.user_agent})))

    # ---- v3 ------------------------------------------------------------

    def v3(self, path: str) -> dict:
        """A v3 GET, e.g. ``games/skyrimspecialedition/mods/12604``.

        v3 is the newest REST API and authenticates with the same `apikey`
        header as v1 - its spec declares ApiKeyAuth globally, and an
        unauthenticated request comes back 401 rather than a public
        response.  Most of it is marked Experimental, so treat what comes
        back as liable to change and do not build anything load-bearing
        on the shape of it.

        Returns the ``data`` object, since v3 wraps every response in one.
        """
        if not self.key:
            raise NexusError("The v3 API needs a key and none is stored.")
        return self._cached("raw", "v3/" + path.lstrip("/"),
                            lambda: self._v3(path))

    def _v3(self, path: str) -> dict:
        payload = self._open(urllib.request.Request(
            "{}/{}".format(V3, path.lstrip("/")),
            headers={"apikey": self.key, "Accept": "application/json",
                     "User-Agent": self.user_agent}))
        return payload.get("data", payload)

    def mod_v3(self, domain: str, mod_id: int) -> dict:
        """A mod's v3 record, by the id that appears in the site URL."""
        return self.v3("games/{}/mods/{}".format(domain, mod_id))

    def file_dependencies(self, mod_file_version_id: int) -> dict:
        """Requirements attached to a *file* rather than to the mod.

        The one thing neither v1 nor v2 can answer.  v2's
        `modRequirements` returns nothing for a mod whose author listed
        requirements per file, which is why some mod pages show three
        requirements and the API shows none.
        """
        return self.v3("mod-file-versions/{}/dependencies".format(
            mod_file_version_id))

    # ---- v1, continued -------------------------------------------------

    def categories(self, domain: str) -> dict[int, str]:
        """{category id: name} for a game. v1 only, so a key is required."""
        return self._cached("game", "categories/" + domain,
                            lambda: self._categories(domain))

    def _categories(self, domain: str) -> dict[int, str]:
        payload = self.rest("games/{}.json".format(domain))
        out: dict[int, str] = {}
        for entry in payload.get("categories") or ():
            try:
                out[int(entry["category_id"])] = str(entry["name"])
            except (KeyError, TypeError, ValueError):
                continue
        return out
