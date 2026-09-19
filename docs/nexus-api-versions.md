# Which Nexus API can do what

There is no official side-by-side comparison, so this is one — built by
reading the specs rather than from memory, and checked against the live API
on 2026-09-18.

## Official references

| API | Reference |
|---|---|
| v1 REST | [SwaggerHub: Nexus Mods Public API](https://app.swaggerhub.com/apis-docs/NexusMods/nexus-mods_public_api_params_in_form_data/1.0) |
| v2 GraphQL | [graphql.nexusmods.com](https://graphql.nexusmods.com/) — 80+ queries, with examples |
| v3 REST | [api-docs.nexusmods.com](https://api-docs.nexusmods.com/), rendered from the machine-readable [openapi.yaml](https://api.nexusmods.com/openapi.yaml) |

The v3 spec calls v1 "Legacy APIs". The v2 reference calls itself a "Work in
Progress" whose features "may change or disappear without warning" and points
at v1 as the stable alternative. Both are true at once, which is the honest
summary of the situation: **there is no single current API**, and which one
you want depends entirely on what you are asking for.

## At a glance

| | v1 REST | v2 GraphQL | v3 REST |
|---|---|---|---|
| Base | `api.nexusmods.com/v1` | `api.nexusmods.com/v2/graphql` | `api.nexusmods.com/v3` |
| Auth | `apikey` header, always | none for most queries; OAuth for the private parts | `apikey` header or Bearer JWT, always |
| Stability | stable, "legacy" | work in progress | mostly **Experimental** |
| Shape | one call per thing | one query, many things, batched | REST with batch endpoints |
| Quota | 100/min, daily cap | separate quota | separate again |

Verified: an unauthenticated v3 GET returns `401 "Please provide an
authentication method"`, and its spec declares `ApiKeyAuth` globally — so the
key the vault holds reaches v3 as well as v1.

## What each is actually for

### v1 — stable, narrow, and still the only home of some things

The mod record is name, category, version, endorsement and download counters,
adult flag, timestamps. Also: a game's **category table** (nothing else
exposes it), endorsements, tracked mods, the user's own account, and the
"latest added / updated / trending" lists.

Not in v1 at all: **requirements**, in any form.

### v2 — where the relational data is

Mods, games, users, collections, comments, moderation. The queries this
project uses:

```graphql
{ game(domainName: "skyrimspecialedition") { id } }
{ mod(gameId: $g, modId: $m) { modRequirements { nexusRequirements { nodes { modId notes } } } } }
```

Note the variable types are `ID!`, not `Int!` — a detail that cost me a
round-trip. Confirmed live: SkyUI returns 1 requirement, Navigator 5, USSEP 0.

Its limit, and the reason v3 matters: `modRequirements` holds requirements
attached to the **mod**. An author who attached them to a **file** returns an
empty list here, which is why some mod pages show three requirements and the
API shows none.

### v3 — uploads, and file-level dependencies

Thirty-two paths, most marked Experimental. Two clusters:

**Publishing** (of no use to a sorter, central if you are building an upload
tool): create/finalise uploads incl. multipart, create mod files and versions,
move versions between files, changelogs, create collections and revisions.

**Reading** — the part worth knowing about:

| endpoint | gives |
|---|---|
| `GET /mod-file-versions/{id}/dependencies` | **file-level dependencies** — the gap in v2 |
| `GET /mod-file-versions/{id}/dependencies/ranges` | version ranges for them |
| `GET /mod-file-versions/{id}/dependencies/dlc` | which DLC a file needs |
| `POST /mods/batch`, `POST /mod-file-versions/batch` | batch lookups |
| `GET /games/{domain}/mods/{id}` | a mod, by the id in the site URL |
| `GET /mods/{id}/files`, `GET /mod-files/{id}/versions` | files and versions |
| `GET /games/{domain}/dlcs`, `/trending-mods` | DLC list, trending |
| `GET /vortex/extensions` | Vortex extensions and themes |

`PUT /mods/{id}/toggle-legacy-mod-requirements` is a hint about direction:
mod-level requirements are the legacy model, and per-file dependencies are
where Nexus is heading. A tool reading requirements today should expect to
need v3 eventually.

## Choosing

- Requirements for a mod → **v2**, no key needed.
- Requirements for a *file*, or a mod whose v2 requirements come back empty →
  **v3**, key needed.
- A game's category table → **v1**, key needed. Nothing else has it.
- Anything in bulk → **v2** (aliased queries) or v3's `batch` endpoints.
- Uploading → **v3**.
- Something that must not break next month → **v1**, and accept its limits.

## Using them from a plugin

The vault's client covers all three; see
[../nexus_key_vault/README.md](../nexus_key_vault/README.md).

```python
from nexus_key_vault import api
nexus = api.client(organizer, "My Plugin")

nexus.requirements(nexus.game_id("skyrimspecialedition"), 12604)  # v2
nexus.categories("skyrimspecialedition")                          # v1
nexus.file_dependencies(file_version_id)                          # v3
```
