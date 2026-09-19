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
                 timeout: float = TIMEOUT) -> None:
        self.key = (key or "").strip()
        self.user_agent = user_agent
        self.timeout = timeout
        self._last = 0.0

    @property
    def has_key(self) -> bool:
        return bool(self.key)

    def _wait(self) -> None:
        gap = time.time() - self._last
        if gap < PAUSE:
            time.sleep(PAUSE - gap)
        self._last = time.time()

    def _open(self, request: urllib.request.Request):
        self._wait()
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as fh:
                return json.load(fh)
        except urllib.error.HTTPError as exc:
            raise NexusError(explain(exc), getattr(exc, "code", None)) from None
        except (urllib.error.URLError, OSError, TimeoutError) as exc:
            raise NexusError(explain(exc)) from None
        except ValueError as exc:
            raise NexusError("Nexus sent something unreadable.") from None

    # ---- v2 ------------------------------------------------------------

    def graphql(self, query: str, variables: dict | None = None) -> dict:
        """Run a v2 GraphQL query and return its ``data`` block.

        Raises :class:`NexusError` if the server reports query errors, so
        a caller does not have to remember that GraphQL answers 200 with
        the failure inside the body.
        """
        body = {"query": query}
        if variables:
            body["variables"] = variables
        headers = {"Content-Type": "application/json",
                   "Accept": "application/json",
                   "User-Agent": self.user_agent}
        if self.key:
            # Harmless, and enough for some fields. v2's genuinely private
            # half wants an OAuth token instead, which this vault does not
            # hold - so do not assume a key unlocks all of v2.
            headers["apikey"] = self.key
        payload = self._open(urllib.request.Request(
            GRAPHQL, data=json.dumps(body).encode("utf-8"), headers=headers))
        errors = payload.get("errors")
        if errors:
            first = errors[0].get("message") if isinstance(errors[0], dict) \
                else str(errors[0])
            raise NexusError("Nexus rejected the query: {}".format(first))
        return payload.get("data") or {}

    def game_id(self, domain: str) -> int | None:
        data = self.graphql(
            "query($d: String!) { game(domainName: $d) { id } }",
            {"d": domain})
        return ((data.get("game") or {}) or {}).get("id")

    def mod(self, game_id: int, mod_id: int) -> dict:
        """One mod's v2 record."""
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
        return self._open(urllib.request.Request(
            "{}/{}".format(REST, path.lstrip("/")),
            headers={"apikey": self.key, "Accept": "application/json",
                     "User-Agent": self.user_agent}))

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
        payload = self.rest("games/{}.json".format(domain))
        out: dict[int, str] = {}
        for entry in payload.get("categories") or ():
            try:
                out[int(entry["category_id"])] = str(entry["name"])
            except (KeyError, TypeError, ValueError):
                continue
        return out
