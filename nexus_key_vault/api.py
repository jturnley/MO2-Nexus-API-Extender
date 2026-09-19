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

from . import client as _client
from . import vault as _vault

# Re-exported so callers do not import private module paths.
NexusClient = _client.NexusClient
NexusError = _client.NexusError
explain = _client.explain
masked = _vault.masked

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


def has_key(organizer) -> bool:
    """Is a key stored at all - without decrypting it to find out."""
    try:
        return open_vault(organizer).has_key
    except Exception:
        return False


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


def client(organizer, requester: str = "", timeout: float = _client.TIMEOUT):
    """A `NexusClient` carrying the stored key, or None if there is none.

    None means "no credential available" - not "Nexus is down".  A caller
    that only needs public v2 queries can ignore it and build its own
    `NexusClient()` with no key at all, which still works.
    """
    found = key(organizer, requester)
    if not found:
        return None
    agent = "{}/1.0".format(
        (requester or "MO2-Plugin").replace(" ", "-").replace("/", "-"))
    return _client.NexusClient(found, user_agent=agent, timeout=timeout)
