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

from nexus_key_vault import api, cache as cache_mod, client, dpapi, migrate, portable, vault  # noqa: E402

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


def test_portable_round_trip():
    material = b"some machine material"
    sealed = portable.seal(KEY.encode("utf-8"), material,
                           portable.SCHEME_MACHINE)
    check(KEY.encode("utf-8") not in sealed, "sealed bytes are not the key")
    check(sealed.startswith(portable.MAGIC), "tagged as ours")
    check(portable.unseal(sealed, material).decode("utf-8") == KEY,
          "round trip")


def test_portable_rejects_wrong_secret_and_tampering():
    material = b"right"
    sealed = portable.seal(KEY.encode("utf-8"), material,
                           portable.SCHEME_MACHINE)
    try:
        portable.unseal(sealed, b"wrong")
        check(False, "wrong material must not open it")
    except portable.WrongSecret:
        check(True, "wrong material refused")
    # Flipping any byte must be caught by the tag rather than decrypted
    # into something that looks like a key.
    for spot in (len(portable.MAGIC) + 2, len(sealed) // 2, len(sealed) - 1):
        broken = bytearray(sealed)
        broken[spot] ^= 0x40
        try:
            portable.unseal(bytes(broken), material)
            check(False, "tampering must not pass")
        except (portable.WrongSecret, portable.Tampered):
            check(True, "tampering refused at {}".format(spot))
    try:
        portable.unseal(b"not ours at all", material)
        check(False, "foreign bytes must not pass")
    except portable.Tampered:
        check(True, "foreign bytes refused")


def test_portable_is_bound_to_its_folder():
    # The point of the machine scheme is that a copied file stops working.
    # If this ever passes, the fallback has quietly become a constant key.
    with tempfile.TemporaryDirectory() as one, tempfile.TemporaryDirectory() as two:
        here = portable.machine_material(os.path.join(one, "nexus_key.dat"))
        there = portable.machine_material(os.path.join(two, "nexus_key.dat"))
        check(here != there, "material differs between folders")
        sealed = portable.seal(KEY.encode("utf-8"), here,
                               portable.SCHEME_MACHINE)
        try:
            portable.unseal(sealed, there)
            check(False, "a copied file must not open")
        except portable.WrongSecret:
            check(True, "a copied file does not open")


def test_passphrase_vault_locks_without_it():
    with tempfile.TemporaryDirectory() as folder:
        path = os.path.join(folder, "nexus_key.dat")
        vault.Vault(path).store(KEY, "correct horse battery")
        blind = vault.Vault(path)
        check(blind.has_key, "the key is there")
        check(blind.needs_passphrase, "and it knows it needs a passphrase")
        try:
            blind.read()
            check(False, "must not open without the passphrase")
        except vault.NeedsPassphrase:
            check(True, "refused without the passphrase")
        blind.use_passphrase("wrong one")
        try:
            blind.read()
            check(False, "must not open with the wrong passphrase")
        except vault.Locked:
            check(True, "refused with the wrong passphrase")
        opened = vault.Vault(path, "correct horse battery")
        check(opened.read() == KEY, "opens with the right passphrase")
        check(opened.scheme == vault.PASSPHRASE, "recorded its scheme")


def test_a_passphrase_beats_dpapi_when_asked_for():
    # Someone who asks for a passphrase on Windows has decided they want
    # protection that survives their account being unlocked. Honour it.
    with tempfile.TemporaryDirectory() as folder:
        path = os.path.join(folder, "nexus_key.dat")
        store = vault.Vault(path)
        store.store(KEY, "a passphrase")
        check(store.scheme == vault.PASSPHRASE, "passphrase wins")
        store.store(KEY)
        check(store.scheme == vault.best_scheme(), "and is not sticky")


def test_the_file_never_claims_more_than_it_did():
    # The note in the file is what a curious user reads. It must match
    # the scheme actually used, or the plugin is lying in writing.
    with tempfile.TemporaryDirectory() as folder:
        path = os.path.join(folder, "nexus_key.dat")
        for phrase in ("", "a passphrase"):
            vault.Vault(path).store(KEY, phrase)
            raw = io.open(path, encoding="utf-8").read()
            scheme = vault.Vault(path).scheme
            check(vault.NOTES[scheme] in raw, "note matches scheme")
            if scheme == vault.MACHINE:
                check("not encrypted" in raw, "machine scheme says so")


def test_wine_is_not_trusted_for_dpapi():
    # available() is the gate the vault uses to decide whether DPAPI is
    # worth the claim. Under Wine the answer must be no, even though the
    # calls are present and would appear to work.
    check(dpapi.available() == (dpapi.present() and not dpapi.wine()),
          "real DPAPI only")
    if dpapi.wine():
        check(vault.best_scheme() == vault.MACHINE, "Wine falls back")
    else:
        check(not dpapi.present() or vault.best_scheme() == vault.DPAPI,
              "real Windows uses DPAPI")


def test_portable_plaintext_never_hits_disk():
    if dpapi.available():
        return      # covered by the DPAPI test on Windows
    with tempfile.TemporaryDirectory() as folder:
        path = os.path.join(folder, "nexus_key.dat")
        vault.Vault(path).store(KEY)
        raw = io.open(path, "rb").read()
        for encoding in ("utf-8", "utf-16-le"):
            check(KEY.encode(encoding) not in raw, "not in " + encoding)
        check(KEY[8:32].encode("utf-8") not in raw, "no fragment either")


def test_refresh_ignores_the_cache_but_replaces_it():
    with tempfile.TemporaryDirectory() as folder:
        store = cache_mod.Cache(os.path.join(folder, "c.json"))
        calls = []

        def fetch(value):
            def go():
                calls.append(value)
                return value
            return go

        nexus = client.NexusClient(cache=store)
        check(nexus._cached("mod", "m", fetch("old")) == "old", "fetched")
        check(nexus._cached("mod", "m", fetch("old")) == "old", "cached")
        check(len(calls) == 1, "served from cache the second time")
        with nexus.refreshing():
            check(nexus._cached("mod", "m", fetch("new")) == "new",
                  "refresh ignores the cached answer")
        check(len(calls) == 2, "refresh really fetched")
        # The point of refresh over bypass: everyone else gets the new one.
        check(nexus._cached("mod", "m", fetch("unused")) == "new",
              "and the new answer replaced the old")
        check(len(calls) == 2, "without another request")


def test_a_failed_refresh_leaves_the_old_answer():
    # Emptying the cache on a failed refresh would cost the next run too,
    # for no benefit: a stale answer beats no answer here.
    with tempfile.TemporaryDirectory() as folder:
        store = cache_mod.Cache(os.path.join(folder, "c.json"))
        nexus = client.NexusClient(cache=store)
        nexus._cached("mod", "m", lambda: "old")

        def boom():
            raise client.NexusError("nexus is having a day", 503)

        try:
            with nexus.refreshing():
                nexus._cached("mod", "m", boom)
            check(False, "the error must reach the caller")
        except client.NexusError:
            check(True, "error raised")
        check(nexus._cached("mod", "m", lambda: "fetched again") == "old",
              "the old answer survived a failed refresh")


def test_refreshing_restores_itself():
    nexus = client.NexusClient()
    check(nexus.refresh is False, "off by default")
    with nexus.refreshing():
        check(nexus.refresh is True, "on inside")
    check(nexus.refresh is False, "off again")
    try:
        with nexus.refreshing():
            raise RuntimeError("boom")
    except RuntimeError:
        pass
    # A client is shared for a whole session, so a failed run must not
    # leave it refreshing for everything that follows.
    check(nexus.refresh is False, "off again after an exception")
    with nexus.refreshing():
        with nexus.refreshing(False):
            check(nexus.refresh is False, "nests")
        check(nexus.refresh is True, "and unwinds")


for name, fn in sorted(list(globals().items())):
    if name.startswith("test_"):
        fn()
print("all {} key vault checks passed".format(checks))
