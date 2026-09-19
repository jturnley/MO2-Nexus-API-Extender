"""What other plugins import. The whole published surface is here.

    from nexus_key_vault import api

    nexus = api.client(organizer, "My Plugin")
    if nexus is None:
        return                      # no key stored, or the user said no
    reqs = nexus.requirements(nexus.game_id("skyrimspecialedition"), 266)

`client` is the one to reach for.  `key` exists for a caller with its own
HTTP layer, and should be used with the same care this plugin takes: do not
log it, do not put it in an error message, do not write it anywhere else.

Everything here is defensive on purpose.  A plugin calling this must keep
working when the vault is absent, when the file is locked to another
Windows account, and when the user has revoked it - so nothing raises, and
"no key" comes back as an empty string or None rather than an exception.
"""

from __future__ import annotations

import os

from . import cache as _cache
from . import client as _client
from . import vault as _vault

# Re-exported so callers do not import private module paths.
NexusClient = _client.NexusClient
NexusError = _client.NexusError
explain = _client.explain
masked = _vault.masked
Cache = _cache.Cache

_FOLDER = "nexus_key_vault"


def storage(organizer) -> str:
    """Where the vault file lives, under MO2's plugin data directory."""
    try:
        base = organizer.pluginDataPath()
    except Exception:
        base = os.path.join(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__))), _FOLDER)
    return os.path.join(base, _FOLDER, _vault.FILENAME)


def open_vault(organizer) -> _vault.Vault:
    return _vault.Vault(storage(organizer))


def cache_path(organizer) -> str:
    """Where cached Nexus responses live. Shared by every plugin."""
    return os.path.join(os.path.dirname(storage(organizer)), _cache.FILENAME)


def open_cache(organizer):
    """The shared response cache, or None if it cannot be opened.

    Shared on purpose: two plugins asking about the same mod should cost
    one request between them, which is the part a cache inside each
    plugin cannot do.
    """
    try:
        return _cache.Cache(cache_path(organizer))
    except Exception:
        return None


def has_key(organizer) -> bool:
    """Is a key stored at all - without decrypting it to find out."""
    try:
        return open_vault(organizer).has_key
    except Exception:
        return False


def protection(organizer) -> str:
    """How the key is held here, as a phrase you can show a user.

    Exists so a plugin reporting on the vault does not have to reach into
    `vault` directly and risk saying something stronger than the truth -
    on Wine the honest answer is "obfuscated", not "encrypted".
    """
    try:
        return open_vault(organizer).protection()
    except Exception:
        return "unavailable"


def key(organizer, requester: str = "") -> str:
    """The stored Nexus key, or "" if there is not one to give.

    `requester` should be your plugin's name.  It is recorded so the user
    can see who has asked for their credential, and honours a deny set in
    the vault's dialog.  Passing nothing still works; it just shows up in
    that list as "unnamed plugin", which is a poor look for your plugin.

    Returns "" rather than raising for every failure, including a vault
    locked to a different Windows account.
    """
    name = (requester or "").strip() or "unnamed plugin"
    try:
        store = open_vault(organizer)
        if not store.has_key:
            return ""
        if not store.allowed(name):
            return ""
        store.note(name)
        return store.read()
    except Exception:
        # A locked, missing or damaged vault is the caller's cue to carry
        # on without Nexus, not to fall over.
        return ""


def client(organizer, requester: str = "", timeout: float = _client.TIMEOUT,
           cache: bool = True, require_key: bool = True):
    """A `NexusClient` carrying the stored key, or None if there is none.

    None means "no credential available" - not "Nexus is down".  A caller
    that only needs public v2 queries can ignore it and build its own
    `NexusClient()` with no key at all, which still works.

    Responses are cached on disk by default, shared with every other
    plugin, so a second scan does not re-ask Nexus for what has not
    changed.  Pass ``cache=False`` if you keep a cache of your own: a
    caller sweeping a whole modlist usually wants one shaped like its own
    problem, and paying for two is worse than paying for one.

    Call ``nexus.cache.save()`` when your run finishes.  Forgetting only
    means the next run starts cold.

    ``require_key=False`` returns a keyless client instead of None when
    nothing is stored.  That is what a caller wanting v2's public queries
    should pass: those need no credential, and refusing to hand back a
    client would break them for every user who has not stored a key.
    Check ``nexus.has_key`` before calling anything on v1 or v3.
    """
    found = key(organizer, requester)
    if not found and require_key:
        return None
    agent = "{}/1.0".format(
        (requester or "MO2-Plugin").replace(" ", "-").replace("/", "-"))
    return _client.NexusClient(found, user_agent=agent, timeout=timeout,
                               cache=open_cache(organizer) if cache else None)
