# MO2 Nexus API Extender

An MO2 plugin that keeps **one** Nexus API key — encrypted for your Windows
account — and lends it to any other plugin that asks, so each one does not
end up storing its own copy in plain text.

**Tools → Nexus API Key**

## The problem

MO2 has a working Nexus connection, and two limits sit on top of it:

1. **The bridge is v1.** `createNexusBridge()` hands a plugin a v1 mod
   record — name, category, version, counters. Requirements, per-file data
   and collections are not in it.
2. **The credential is not shared.** MO2's own key is not exposed through
   `mobase`, so a plugin cannot compose a request MO2 did not already have a
   method for. Being signed in does not help.

The usual workaround is for each plugin to ask the user for their own key and
store it in its plugin settings — which live in `ModOrganizer.ini`, in plain
text, in a file that gets copied into instance backups and pasted into
support threads.

## What this does

- Stores one key, encrypted with **Windows DPAPI** under your user account.
  The file is inert on another machine or another Windows account.
- Offers a **ready-made client** covering all three Nexus APIs, so a plugin
  borrowing the key does not have to re-derive which one answers what.
- Sweeps known plugins' plain-text key settings and offers to **take them
  over and blank them**. It touches only those plugins' own settings —
  MO2's own Nexus login is stored separately and is never modified.
- Keeps a visible **record of which plugins have asked** for the key.

### What it does not do

**It does not isolate the key from other plugins, and does not claim to.**
Every MO2 Python plugin shares one interpreter, one process and your user
account. Anything that can run can import this package and call `read()`.
There is no boundary between plugins for a vault to hide behind.

What encryption at rest buys is everything that happens to the *file* rather
than in the process: backups, synced profile folders, support archives, a
stolen drive, another account on a shared machine. Those are the common ways
a credential actually escapes, and they are closed.

The caller list is an audit and a courtesy control, not a security boundary.

## Layout

```
nexus_key_vault/      the plugin - copy this folder into MO2/plugins/
  api.py              the published surface: what other plugins import
  client.py           v1 / v2 / v3 Nexus client
  vault.py            the file, the key, the caller record
  dpapi.py            Windows encryption via ctypes (no pywin32)
  migrate.py          finding and clearing plain-text keys elsewhere
  ui.py               the one dialog
  plugin.py           MO2 wiring, deliberately thin
tests/                40 checks - no Qt, no MO2, no network
docs/                 which Nexus API can answer what
```

## For plugin authors

```python
from nexus_key_vault import api

nexus = api.client(organizer, "My Plugin")   # None if no key available
if nexus is not None:
    game = nexus.game_id("skyrimspecialedition")
    for req in nexus.requirements(game, 12604):
        print(req["modId"], req.get("notes"))
```

Never raises, never blocks. Full API and the rules for handling someone
else's credential: [nexus_key_vault/README.md](nexus_key_vault/README.md).

Which API answers what — v1 vs v2 GraphQL vs v3, with the auth and stability
of each: [docs/nexus-api-versions.md](docs/nexus-api-versions.md).

## API stability

**1.0.0. The published interface is stable.**

Everything in `nexus_key_vault/api.py` and the `NexusClient` methods listed
above will keep working: names, arguments and return shapes. New calls may be
added; existing ones will not change meaning or disappear without a major
version bump. `api.key()` and `api.client()` will keep returning `""`/`None`
rather than raising, because callers are built on that.

Not covered, and free to change: anything under `vault`, `dpapi`, `migrate`
or `ui` reached directly, the on-disk file format, and the DPAPI entropy. Go
through `api` and none of that is your problem.

Nexus itself is the moving part. v2 GraphQL describes itself as a work in
progress and v3 is mostly Experimental, so a method here can start returning
different data even while its signature holds. See
[docs/nexus-api-versions.md](docs/nexus-api-versions.md).

## Install

Copy `nexus_key_vault/` into `MO2/plugins/` and restart MO2. No dependencies.

## Tests

```bash
python tests/test_nexus_key_vault.py
```

The one that matters most asserts against the raw bytes of the stored file:
the key must not appear in it in any encoding.
