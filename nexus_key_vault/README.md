# Nexus API Key Vault

An MO2 tool plugin that keeps **one** Nexus API key, encrypted for your
Windows account, and lends it to any plugin that asks — so each plugin does
not end up storing its own plain-text copy.

**Tools → Nexus API Key.**

## Why a plugin needs a key at all

MO2 has a working Nexus connection and two limits sit on top of it:

- **It speaks the v1 API.** `createNexusBridge()` hands a plugin a v1 mod
  record: name, category, version, counters. Requirements, per-file data and
  collections are simply not in it.
- **It will not share the credential.** MO2's own key is not exposed through
  `mobase`, so a plugin cannot compose a request MO2 did not already have a
  method for. Being signed in does not help.

A key of your own removes both limits. There are three APIs, not two, and
none of them is simply "the latest" - see
[../docs/nexus-api-versions.md](../docs/nexus-api-versions.md) for what each
one can answer:

| | auth | stability |
|---|---|---|
| **v1 REST** | `apikey`, always | stable, called "legacy" by v3's own spec |
| **v2 GraphQL** | none for most queries; OAuth for the private parts | work in progress |
| **v3 REST** | `apikey` or Bearer JWT, always | mostly Experimental |

The stored key reaches v1 and v3. v2's public queries need no credential,
and its genuinely private half wants an OAuth token, which this vault does
not hold.

## Where the key is kept

`<MO2 plugin data>/nexus_key_vault/nexus_key.dat`, encrypted with **Windows
DPAPI** against your user account. Copy that file to another machine or
another Windows account and the key does not go with it — the OS refuses to
decrypt it. Nothing is written to `ModOrganizer.ini`, which stores plugin
settings in plain text.

### What this does not protect against

Say it plainly, because it is the difference between a useful feature and a
false sense of security:

**Any plugin running in MO2 can read the key.** Every Python plugin shares
one interpreter, one process, and your user account. A plugin that wanted the
key without asking could `import nexus_key_vault.vault` and call `read()`, or
read this source to find the DPAPI entropy. There is no isolation between
plugins for the vault to hide behind, and anything claiming otherwise would
be claiming something Windows does not offer here.

What encryption at rest genuinely buys you is everything that happens to the
*file* rather than in the process: instance backups, cloud-synced profile
folders, a support archive pasted into a Discord thread, a stolen drive,
another account on a shared machine. Those are real, common ways a credential
escapes, and this closes all of them.

The **"Plugins that have asked for it"** list is an audit and a courtesy
control, not a security boundary. Denying a plugin stops any caller using the
published API; it cannot stop one that declines to use it.

## For plugin authors

```python
from nexus_key_vault import api

nexus = api.client(organizer, "My Plugin")   # None if no key is available
if nexus is not None:
    game = nexus.game_id("skyrimspecialedition")
    for req in nexus.requirements(game, 266):
        print(req["modId"], req.get("notes"))
```

Never raises and never blocks. `None` means "no credential" — not "Nexus is
down" — and a caller that only needs public v2 queries can build
`NexusClient()` with no key and carry on.

### The whole API

| call | does |
|---|---|
| `api.client(organizer, requester)` | a `NexusClient` carrying the key, or `None` |
| `api.key(organizer, requester)` | the raw key, or `""` — for callers with their own HTTP layer |
| `api.has_key(organizer)` | is one stored, without decrypting it |
| `api.masked(key)` | a key described, not shown, for your own UI |
| `api.explain(exc)` | an error in words, built from the status code |

On `NexusClient`:

| call | API | needs key |
|---|---|---|
| `graphql(query, variables)` | v2 | no |
| `game_id(domain)` | v2 | no |
| `mod(game_id, mod_id)` | v2 | no |
| `requirements(game_id, mod_id)` | v2 | no |
| `rest(path)` | v1 | **yes** |
| `categories(domain)` | v1 | **yes** |
| `v3(path)` | v3 | **yes** |
| `mod_v3(domain, mod_id)` | v3 | **yes** |
| `file_dependencies(file_version_id)` | v3 | **yes** |

`file_dependencies` is the one neither of the others can answer: v2's
`modRequirements` is empty for a mod whose author attached requirements to a
*file*, which is why some mod pages list three and the API returns none.

Pass your plugin's name as `requester`. It is recorded so the user can see
who has their credential, and it honours a deny set in the dialog. Omitting
it works, but shows up in that list as "unnamed plugin".

### Rules for holding someone else's credential

The vault holds itself to these, and a plugin borrowing the key should too:

- **Never echo it back** — not to a dialog, log, exception or crash report.
  `api.masked()` renders one as `92 characters, ending WQ==`: enough to tell
  two apart, useless to a reader.
- **Build error text from the HTTP status**, not from the exception's string
  form. That is what `api.explain()` is for.
- **Do not store your own copy.** If you need one and the vault has none, ask
  the user and store it under your own plugin name — never write into the
  vault's file, and never overwrite another plugin's setting.
- **Leave rate-limit headroom.** v1 allows 100 requests a minute and a daily
  allowance; the quota is the user's, and MO2 needs its share afterwards.
- **Survive its absence.** No key, no network, a 429, a locked vault — every
  one of them should degrade rather than fail.

## Install

Copy the `nexus_key_vault` folder into `MO2/plugins/` and restart MO2. No
dependencies: DPAPI is reached through `ctypes`, not pywin32.
