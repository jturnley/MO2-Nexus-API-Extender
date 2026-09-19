"""Nexus API Key Vault - one shared, encrypted Nexus key for MO2 plugins.

Other plugins want :mod:`nexus_key_vault.api` and nothing else:

    from nexus_key_vault import api
    nexus = api.client(organizer, "My Plugin")

That import must not drag in Qt or mobase, so the MO2 plugin class is only
loaded when MO2 itself asks for it - a plugin importing the API from a
worker thread, or a test importing it with no MO2 at all, should not fail
because PyQt6 happens to be missing.
"""

from __future__ import annotations


def createPlugin():
    from .plugin import createPlugin as _make
    return _make()


def createPlugins() -> list:
    from .plugin import createPlugins as _make
    return _make()
