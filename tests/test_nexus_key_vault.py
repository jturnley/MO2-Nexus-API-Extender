"""Tests for the key vault. No Qt, no MO2, no network.

The one that matters most is `plaintext_never_hits_disk`: the whole point
of the plugin is that the key is not sitting somewhere readable, so that is
asserted against the actual bytes of the actual file rather than against
the code's intentions.
"""

from __future__ import annotations

import io
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nexus_key_vault import api, cache as cache_mod, client, dpapi, migrate, vault  # noqa: E402

KEY = "abcdefgh-1234-5678-9012-abcdefghijkl-Zm9vYmFyYmF6cXV4WQ=="
checks = 0


def check(condition, label):
    global checks
    assert condition, label
    checks += 1


class FakeOrganizer:
    """Just enough IOrganizer for the vault: settings and a data path."""

    def __init__(self, path, settings=None):
        self._path = path
        self._settings = dict(settings or {})

    def pluginDataPath(self):
        return self._path

    def pluginSetting(self, owner, setting):
        if (owner, setting) not in self._settings:
            raise RuntimeError("no such plugin setting")
        return self._settings[(owner, setting)]

    def setPluginSetting(self, owner, setting, value):
        self._settings[(owner, setting)] = value


def temp_vault(folder):
    return vault.Vault(os.path.join(folder, "nexus_key.dat"))


def test_masking():
    check(vault.masked(KEY).endswith("Q=="), "tail shown")
    check(KEY[:20] not in vault.masked(KEY), "body never shown")
    check(vault.masked("") == "", "nothing to describe")
    # A short key would be mostly revealed by a 4-character tail, so it
    # gives the tail up rather than describing itself.
    check(vault.masked("abcd1234") == "8 characters", "short key keeps quiet")


def test_dpapi_round_trip():
    if not dpapi.available():
        return
    sealed = dpapi.seal(KEY.encode("utf-8"))
    check(KEY.encode("utf-8") not in sealed, "sealed bytes are not the key")
    check(dpapi.unseal(sealed).decode("utf-8") == KEY, "round trip")
    # A blob from elsewhere, or a corrupted one, must fail rather than
    # returning something plausible.
    broken = bytearray(sealed)
    broken[len(broken) // 2] ^= 0xFF
    try:
        dpapi.unseal(bytes(broken))
        check(False, "tampered blob should not decrypt")
    except dpapi.Unavailable:
        check(True, "tampered blob refused")


def test_store_and_read():
    if not dpapi.available():
        return
    with tempfile.TemporaryDirectory() as folder:
        store = temp_vault(folder)
        check(not store.has_key, "starts empty")
        check(store.read() == "", "empty reads as empty string")
        store.store(KEY)
        check(store.has_key, "key is there")
        check(temp_vault(folder).read() == KEY, "survives a reload")
        temp_vault(folder).clear()
        check(not temp_vault(folder).has_key, "cleared")


def test_plaintext_never_hits_disk():
    if not dpapi.available():
        return
    with tempfile.TemporaryDirectory() as folder:
        store = temp_vault(folder)
        store.store(KEY)
        store.note("Some Plugin")
        for name in os.listdir(folder):
            with open(os.path.join(folder, name), "rb") as fh:
                blob = fh.read()
            check(KEY.encode("utf-8") not in blob, "no key in " + name)
            check(KEY.encode("utf-16-le") not in blob, "no wide key in " + name)
            # The tail is what a dialog is allowed to show; even that
            # should not be sitting in the file next to the rest.
            check(b"Zm9vYmFyYmF6cXV4WQ==" not in blob, "no fragment in " + name)


def test_audit_and_deny():
    if not dpapi.available():
        return
    with tempfile.TemporaryDirectory() as folder:
        store = temp_vault(folder)
        store.store(KEY)
        organizer = FakeOrganizer(folder)
        # api.storage() nests under a folder of its own, so point the
        # fake at the same file the vault above is using.
        path = api.storage(organizer)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        import shutil
        shutil.copy(os.path.join(folder, "nexus_key.dat"), path)

        check(api.key(organizer, "Plugin A") == KEY, "caller gets the key")
        again = vault.Vault(path)
        check(again.asked["Plugin A"]["count"] == 1, "request recorded")
        api.key(organizer, "Plugin A")
        check(vault.Vault(path).asked["Plugin A"]["count"] == 2, "counted up")

        denied = vault.Vault(path)
        denied.set_allowed("Plugin A", False)
        check(api.key(organizer, "Plugin A") == "", "denied caller gets none")
        check(api.key(organizer, "Plugin B") == KEY, "others unaffected")
        # A caller that gives no name still works - it is recorded
        # under a placeholder rather than being turned away, because
        # breaking such a plugin teaches its author nothing.
        check(api.key(organizer) == KEY, "an unnamed caller works")
        check("unnamed plugin" in vault.Vault(path).asked,
              "and is visible in the list as such")


def test_api_survives_a_missing_vault():
    with tempfile.TemporaryDirectory() as folder:
        organizer = FakeOrganizer(folder)
        check(api.key(organizer, "Plugin") == "", "no vault, no key, no raise")
        check(api.client(organizer, "Plugin") is None, "no client either")
        check(api.has_key(organizer) is False, "and it says so")


def test_client_needs_a_key_for_v1():
    bare = client.NexusClient("")
    check(not bare.has_key, "no key")
    try:
        bare.rest("games/skyrimspecialedition.json")
        check(False, "v1 without a key should not be attempted")
    except client.NexusError:
        check(True, "refused before the request went out")


def test_v3_needs_a_key_too():
    bare = client.NexusClient("")
    for call in (lambda: bare.v3("games/skyrimspecialedition/mods/12604"),
                 lambda: bare.mod_v3("skyrimspecialedition", 12604),
                 lambda: bare.file_dependencies(1)):
        try:
            call()
            check(False, "v3 without a key should not be attempted")
        except client.NexusError:
            check(True, "refused before the request went out")


def test_errors_never_carry_the_key():
    class Failure(Exception):
        code = 401

    message = client.explain(Failure(KEY))
    check(KEY not in message, "key not echoed from an exception")
    check("401" in message, "status explained")
    check("429" in client.explain(type("E", (Exception,), {"code": 429})()),
          "rate limit explained")


def test_cache_round_trip_and_expiry():
    with tempfile.TemporaryDirectory() as folder:
        path = os.path.join(folder, "nexus_cache.json")
        store = cache_mod.Cache(path)
        check(store.get("mod", "a") == (False, None), "cold cache misses")
        store.put("mod", "a", {"name": "x"})
        check(store.get("mod", "a") == (True, {"name": "x"}), "then hits")
        store.save()
        check(cache_mod.Cache(path).get("mod", "a")[0], "survives a reload")

        # An entry past its life is gone, not merely stale.
        store.put("mod", "b", {"name": "y"}, ttl=-1)
        check(store.get("mod", "b") == (False, None), "expired entry misses")
        store.save()
        reloaded = cache_mod.Cache(path)
        check(reloaded.get("mod", "b") == (False, None), "stays gone")
        check(reloaded.size == 1, "and is dropped from the file entirely")


def test_cache_key_never_contains_the_credential():
    with tempfile.TemporaryDirectory() as folder:
        path = os.path.join(folder, "nexus_cache.json")
        store = cache_mod.Cache(path)
        store.put("raw", "v1/games/skyrimspecialedition.json", {"ok": 1})
        store.save()
        with open(path, "rb") as fh:
            blob = fh.read()
        check(KEY.encode("utf-8") not in blob, "no key in the cache file")
        # The same request cached under one key must be readable under
        # another: the key is not part of what identifies a response.
        a = client.NexusClient(KEY, cache=store)
        b = client.NexusClient("different-key-entirely", cache=store)
        check(a._cached("raw", "same", lambda: "v") == "v", "first fetches")
        check(b._cached("raw", "same", lambda: "other") == "v",
              "second reads what the first stored")


def test_cache_stores_reads_but_never_failures():
    with tempfile.TemporaryDirectory() as folder:
        store = cache_mod.Cache(os.path.join(folder, "c.json"))
        nexus = client.NexusClient("k", cache=store)

        def blow_up(status):
            def fn():
                raise client.NexusError("failed", status)
            return fn

        # A transient failure cached would outlive the problem.
        for status in (401, 429, 500, None):
            try:
                nexus._cached("mod", "s{}".format(status), blow_up(status))
            except client.NexusError:
                pass
            check(nexus._cached("mod", "s{}".format(status),
                                lambda: "fresh") == "fresh",
                  "status {} was not cached".format(status))

        # A 404 is remembered, so a deleted page is asked about once.
        try:
            nexus._cached("mod", "gone", blow_up(404))
        except client.NexusError:
            pass
        try:
            nexus._cached("mod", "gone", lambda: "should not be called")
            check(False, "a cached 404 should still raise")
        except client.NexusError as exc:
            check(exc.status == 404, "and raises 404 without a request")


def test_mutations_are_never_cached():
    check(client.NexusClient._is_read("query($g: ID!) { game { id } }"),
          "a named query is a read")
    check(client.NexusClient._is_read("{ game(domainName: \"x\") { id } }"),
          "a bare selection is a read")
    check(not client.NexusClient._is_read("mutation { endorse(id: 1) }"),
          "a mutation is not")
    check(not client.NexusClient._is_read("  MUTATION { x }"),
          "case and padding do not smuggle one past")


def test_client_without_a_cache_still_works():
    nexus = client.NexusClient("k")
    check(nexus.cache is None, "no cache by default")
    check(nexus._cached("mod", "x", lambda: "live") == "live",
          "calls straight through")


def test_readme_documents_every_published_call():
    """The README's API tables are the contract; drift makes them a lie.

    Only the published surface is checked. Vault methods are deliberately
    undocumented as callable API, so they are not required here.
    """
    import inspect
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    text = io.open(os.path.join(root, "README.md"), encoding="utf-8").read()

    published = [n for n in dir(api)
                 if not n.startswith("_")
                 and n not in ("annotations", "os", "client")
                 and callable(getattr(api, n))]
    for name in published:
        check("api.{}".format(name) in text or "`{}`".format(name) in text,
              "README documents api." + name)

    for name, member in inspect.getmembers(client.NexusClient):
        if name.startswith("_"):
            continue
        if inspect.isfunction(member) or isinstance(member, property):
            check("`{}(".format(name) in text or "`{}`".format(name) in text,
                  "README documents NexusClient." + name)


def test_migration_finds_and_clears():
    with tempfile.TemporaryDirectory() as folder:
        organizer = FakeOrganizer(folder, {("MO2 DAG Sorter",
                                            "nexus_api_key"): KEY})
        found = migrate.found(organizer)
        check(len(found) == 1, "found the plain-text copy")
        check(found[0][2] == KEY, "and read it")
        check(migrate.clear(organizer, "MO2 DAG Sorter", "nexus_api_key"),
              "cleared it")
        check(migrate.found(organizer) == [], "nothing left behind")
        # A plugin that is not installed must not raise.
        check(migrate.found(FakeOrganizer(folder)) == [], "absent is fine")


def test_migration_touches_only_plugin_settings():
    # MO2's own credential is not a plugin setting and must never appear
    # in the sweep list; this is the guard against a regression that
    # would break downloads and endorsements.
    for owner, setting in migrate.KNOWN:
        check(owner != "Settings", "MO2's own settings are off limits")
        check("ModOrganizer" not in owner, "no core settings")


for name, fn in sorted(list(globals().items())):
    if name.startswith("test_"):
        fn()
print("all {} key vault checks passed".format(checks))
