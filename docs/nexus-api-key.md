# Sharing a Nexus API key between MO2 plugins

*For plugin authors. Users do not need to read this — **Tools → Nexus API
Key** is the whole interface.*

## The problem this solves

MO2 has a working Nexus connection, and will not let a plugin use it for
anything of the plugin's own choosing. Two separate limits are at work:

1. **The bridge is v1.** `IOrganizer.createNexusBridge()` returns an
   `IModRepositoryBridge` that speaks the Nexus **v1 REST API**. What comes
   back for a mod is a v1 mod record: name, category, version, endorsement
   and download counters, adult flag, timestamps. That is the whole surface.

2. **The credential is not shared.** MO2 holds its own key (or OAuth
   session) and does not expose it through `mobase`. A plugin cannot
   construct a request MO2 did not already have a method for.

So anything the v1 mod record does not carry is out of reach — even when the
user is signed in and the data is public. Requirements are the example that
motivated this: they are not in v1 at all. Per-file metadata, collections and
the rest of the v2 surface are in the same position.

## What a key changes, and what it does not

Be precise about this in your own UI, because the temptation is to
oversell it:

| | needs a key |
|---|---|
| v1 REST (`api.nexusmods.com/v1/...`) | **yes** — `apikey:` header on every request |
| v2 GraphQL (`api.nexusmods.com/v2/graphql`), public queries | **no** |
| v2 GraphQL, anything user-scoped | yes (key or OAuth) |

This sorter reads mod requirements from **v2 GraphQL with no credential at
all**, and uses the key only for v1 — fetching a game's category table, and
mod records when MO2's bridge is unavailable. A key is not a prerequisite for
"the newer API"; it is a prerequisite for *v1*, and for the parts of v2 that
are about a particular user.

The two versions also bill against **separate quotas**, which is worth
knowing when you are budgeting requests.

## The vault plugin supersedes this

`nexus_key_vault` is now the recommended way to do all of the below: it
keeps one key for every plugin, encrypted for the Windows account with
DPAPI, and hands out a ready-made client. See
[../nexus_key_vault/README.md](../nexus_key_vault/README.md).

```python
from nexus_key_vault import api
nexus = api.client(organizer, "My Plugin")
```

The rest of this page describes reading a key straight out of another
plugin's MO2 setting. That still works, and it is what the sorter did
before the vault existed, but the setting is stored in plain text in
ModOrganizer.ini - which is the problem the vault was built to fix.

## Reading the shared key

The sorter stores the user's key in its own MO2 plugin setting. MO2's
`pluginSetting` takes the owning plugin's name, so any plugin can read it:

```python
OWNER = "MO2 DAG Sorter"
SETTING = "nexus_api_key"

def shared_key(organizer) -> str:
    """The key the user entered in the sorter, or "" if there is none."""
    try:
        return str(organizer.pluginSetting(OWNER, SETTING) or "").strip()
    except Exception:
        # The sorter is not installed, or the setting has never existed.
        return ""
```

What `pluginSetting` does when the named plugin is not installed differs
between MO2 builds — some hand back an empty value, some raise — so the
`try` and the `or ""` are each doing real work. Do not drop either.

Using it:

```python
import urllib.request

req = urllib.request.Request(
    "https://api.nexusmods.com/v1/games/skyrimspecialedition.json",
    headers={"apikey": key, "User-Agent": "Your-Plugin/1.0"})
```

The header is `apikey`, not `Authorization`.

### Writing it

Don't. The user typed it into one dialog that explains where it goes; a
second plugin silently overwriting it is a surprise at best. If your plugin
wants a key and finds none stored, ask for one and store it under **your own**
plugin name. Two keys costing two entries is a smaller problem than one key
changing under the user without their knowing which plugin did it.

## Handling it

The rules the sorter holds itself to, offered as a starting point:

- **Never echo it back.** Not into a dialog, a log line, an exception
  message, or a crash report. `keys.masked()` in this plugin renders a stored
  key as `92 characters, ending WQ==` — enough to tell two keys apart and
  confirm one arrived intact, useless to anyone who reads it.
- **Build error text from the HTTP status,** not from the exception's string
  form. `urllib` puts the requested URL into some of its errors; the key
  travels in a header today, but the habit costs nothing and survives a
  refactor that moves it.
- **Mask the entry field by default,** with an explicit "show what I am
  typing" for the user who wants to check a paste.
- **Never pre-fill the field from storage.** Putting the credential back on
  screen to tell the user it exists is a poor trade; a status line saying one
  is stored does the same job.
- **Leave headroom in the rate limit.** v1 allows 100 requests/minute and a
  daily allowance. This plugin stops 50 short of the hourly limit rather than
  spending the last of it, so MO2's own Nexus features still work after a
  sort. The key belongs to the user, and so does the quota.
- **Survive its absence.** No key, no network, a 429, a hidden mod — all of
  them should end in a degraded result rather than a failed run. Here every
  one of them falls back to the cache on disk, and then to inference from the
  file tree.

## Where the sorter's own code lives

- [`keys.py`](../mo2_dag_sorter/keys.py) — `masked()` and `reason()`, kept
  Qt-free so the rules above are unit-testable
- [`key_ui.py`](../mo2_dag_sorter/key_ui.py) — the dialog
- [`nexus.py`](../mo2_dag_sorter/nexus.py) — v1 client, cache, rate reserve
- [`requirements.py`](../mo2_dag_sorter/requirements.py) — v2 GraphQL client
- [`nexus_bridge.py`](../mo2_dag_sorter/nexus_bridge.py) — borrowing MO2's
  connection, and what it costs (it is asynchronous)
