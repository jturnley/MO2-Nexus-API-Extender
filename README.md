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

nexus = api.client(organizer, "My Plugin")   # None if no key is available
if nexus is not None:
    game = nexus.game_id("skyrimspecialedition")
    for req in nexus.requirements(game, 12604):
        print(req["modId"], req.get("notes"))
```

Never raises, never blocks. `None` means "no credential" - not "Nexus is
down" - and a caller that only needs public v2 queries can build
`NexusClient()` with no key and carry on.

Pass your plugin's name as `requester`. It is recorded so the user can see
who holds their credential, and it honours a deny set in the dialog. Omitting
it works, but shows up in that list as "unnamed plugin".

### The `api` module

| call | returns | notes |
|---|---|---|
| `api.client(organizer, requester="", timeout=15.0)` | `NexusClient` or `None` | `None` when no key is available, denied, or the vault is absent |
| `api.key(organizer, requester="")` | `str` | the raw key, or `""`. For callers with their own HTTP layer |
| `api.has_key(organizer)` | `bool` | is one stored, without decrypting it |
| `api.masked(key, tail=4)` | `str` | `"92 characters, ending WQ=="` - for your own UI |
| `api.explain(exc)` | `str` | an error in words, built from the status code |
| `api.storage(organizer)` | `str` | path to the vault file |
| `api.open_vault(organizer)` | `Vault` | the vault object; see the caveat below |

`NexusClient` and `NexusError` are re-exported from `api`, so you never need
to import a private module path.

None of the first three raise. A missing vault, a damaged file, or one locked
to a different Windows account all come back as `""` / `None` / `False`.

### `NexusClient`

`NexusClient(key="", user_agent="MO2-Plugin/1.0", timeout=15.0)` - built for
you by `api.client()`, or directly when you only need public v2 queries.

| call | API | key | returns |
|---|---|---|---|
| `graphql(query, variables=None)` | v2 | no | the `data` block, `dict` |
| `game_id(domain)` | v2 | no | `int` or `None` |
| `mod(game_id, mod_id)` | v2 | no | `dict` - modId, name, version, adult, category |
| `requirements(game_id, mod_id)` | v2 | no | `list[dict]` - `modId`, `notes` |
| `rest(path)` | v1 | **yes** | `dict` - raw v1 JSON |
| `categories(domain)` | v1 | **yes** | `dict[int, str]` - `{category id: name}` |
| `v3(path)` | v3 | **yes** | `dict` - the response's `data` object |
| `mod_v3(domain, mod_id)` | v3 | **yes** | `dict` - by the id in the site URL |
| `file_dependencies(file_version_id)` | v3 | **yes** | `dict` - per-file requirements |
| `has_key` | - | - | `bool` property |

Three of those are escape hatches rather than wrappers: `graphql`, `rest` and
`v3` take anything the API offers, so you are never limited to what is
wrapped here. The endpoint lists are in
[docs/nexus-api-versions.md](docs/nexus-api-versions.md).

`file_dependencies` is the one neither of the others can answer: v2's
`modRequirements` is empty for a mod whose author attached requirements to a
*file*, which is why some mod pages list three and the API returns none.

`rest` and `v3` raise `NexusError` immediately rather than firing a request
that is certain to come back 401.

**Rate limiting is built in** - 0.35s between requests, comfortably inside
v1's 100/minute. **Nothing is cached.** A caller about to ask about nine
hundred mods wants a cache shaped like its own problem, and one built into a
shared client would be the wrong shape for everybody.

### Errors

Everything network-facing raises `NexusError`, which carries `.status` (the
HTTP code, or `None`) and a message built from that code rather than from the
exception's string form - so a key cannot ride out in an error. GraphQL
answers 200 with failures inside the body; `graphql()` raises on those too,
so you do not have to remember that.

```python
try:
    cats = nexus.categories("skyrimspecialedition")
except api.NexusError as exc:
    log(str(exc))          # already safe to display
    if exc.status == 429:
        back_off()
```

### Not part of the published API

`api.open_vault()` hands back the `Vault` object, whose `read`, `store`,
`clear`, `note`, `allowed`, `set_allowed` and `forget` are how the dialog
works. They are reachable, and they are **not** covered by the 1.0.0
stability promise - `store()` and `clear()` write the user's credential.
Read through `api.key()`, and do not write at all: if your plugin needs a key
and the vault has none, ask the user and store it under your own plugin name.

### Rules for holding someone else's credential

The vault holds itself to these, and a plugin borrowing the key should too:

- **Never echo it back** - not to a dialog, log, exception or crash report.
  `api.masked()` gives you something safe to show.
- **Build error text from the HTTP status**, not from the exception's string
  form. That is what `api.explain()` is for.
- **Do not store your own copy**, and never write into the vault's file.
- **Leave rate-limit headroom.** The quota is the user's, and MO2 needs its
  share afterwards.
- **Survive its absence.** No key, no network, a 429, a locked vault - every
  one of them should degrade rather than fail.

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
