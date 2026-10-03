# From CLI to hosted product

The foundation ships a working Typer/Rich CLI, test/build workflows and the release workflow
for PyPI, DockerHub and GHCR. FastAPI, SQLite/Postgres, vectors and production tenancy are
planned profiles, not implemented adapters in this starter.

Record each adopted profile as an OpenSpec change before building against it. The defaults
below and the project OpenSpec are the starting point.

| Capability | Local default | Initial hosted direction |
|---|---|---|
| Compute | Python CLI; optional FastAPI | Cloud Run service for HTTP, Jobs for finite CLI batches, min instances zero |
| Operational records | SQLite | Supabase Postgres through the same owned repository contracts |
| Objects | Files | GCS Standard, matched region |
| Analytics | DuckDB when needed | BigQuery with bytes caps when workload warrants it |
| Vectors | Optional sqlite-vec extension | Supabase pgvector; benchmark before selecting |
| Cache | SQLite TTL | No separate service initially; optional Upstash if shared caching is needed |
| Documents | SQLite JSON | Postgres JSONB; TinyDB/Firestore only for a dedicated NoSQL requirement |
| Presentation | Typer + Rich | Same application behavior through FastAPI |

Domain/application services depend on owned ports. Concrete drivers and configuration live
in adapters/composition. Verify each replacement with real-engine contract and migration tests;
changing a connection URL alone is not portability. Keep public core independent of optional
private hosted extensions and secrets. Qualify tenant isolation, restore, auth and
operational ownership before enterprise deployment.

## Workflow artifacts

Existing `.github/workflows/ci.yml` runs tests/builds. Existing `release.yml` calls those checks
and publishes only after version/setup gates; see RELEASING. `templates/github/cloud-run.yml`
and `pages.yml` are inactive activation examples. Do not maintain divergent copies: upgrade them
in a reviewed template PR. Third-party action tags in these examples must be resolved to
reviewed immutable SHAs before production activation.

Cloud Run requires an implemented, tested API image pinned by digest, WIF, runtime/deployment
accounts, Secret Manager, and the named variables. Its example starts an IAM-private service;
application authorization is still required. No cloud resources are created by this template.

## Secrets by execution location

Local: OS credential manager; ignored `.env` only when needed, outside builds and Git.
GitHub Actions: selected-repo or production-environment secrets; secrets do not cross owner
boundaries. Cloud Run: Secret Manager runtime references and short-lived OIDC deployment
identity. PyPI: Trusted Publisher binding. DockerHub: scoped publisher token. No credential
values are committed to the repo or baked into images.

Costs target low traffic first; account allowances, idle database costs, cross-provider egress
and backup needs must be recalculated before quoting a hosted price.
