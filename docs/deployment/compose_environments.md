# Compose Environments

This repository uses three supported runtime environments:

| Compose file | Role | Ports | Database | Can run alongside prod? |
| --- | --- | --- | --- | --- |
| `docker-compose.dev.yml` | long-lived development stack | 5433 / 8001 / 3002 | `postgres_dev_data` | yes |
| `docker-compose.staging.yml` | temporary staging stack for high-risk verification | 5434 / 8002 / 3003 | `postgres_staging_data` | yes |
| `docker-compose.deploy.yml` | image-only production app stack | 8000 / 3001 | external `instock_postgres` on `instock_network` | yes |

The repository no longer supports a default `docker-compose.yml` main stack.
All environment operations should be explicit:

- `make dev-*` for day-to-day development and front/back-end collaboration
- `make prod-*` for production inspection and release tasks
- `make staging-*` only when you need a short-lived verification environment

`docker-compose.deploy.yml` intentionally does not manage the production
TimescaleDB container. The deploy stack joins the existing external
`instock_network` and connects to `instock_postgres` so that rebuilding the app
or frontend does not recreate the database container or switch it to a new
named volume by accident.

Release images are built directly from the Dockerfiles by
`scripts/build_release_images.sh`, so image builds no longer depend on a hidden
default Compose file.
