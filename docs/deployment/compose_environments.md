# Compose Environments

This repository currently keeps three runnable Docker Compose environments:

| Compose file | Role | Ports | Database | Can run with main stack? |
| --- | --- | --- | --- | --- |
| `docker-compose.yml` | local prod-like stack with bind mounts | 5432 / 8000 / 3001 | `postgres_data` | no |
| `docker-compose.dev.yml` | isolated development/test stack | 5433 / 8001 / 3002 | `postgres_dev_data` | yes |
| `docker-compose.staging.yml` | isolated staging stack | 5434 / 8002 / 3003 | `postgres_staging_data` | yes |
| `docker-compose.deploy.yml` | image-only deployment stack | 5432 / 8000 / 3001 | `postgres_data` | no |

`docker-compose.yml` and `docker-compose.deploy.yml` intentionally target the
same main stack names, ports, network, and volumes. Treat them as two ways to
run the same environment, not as two isolated environments.

Use `docker-compose.yml` for local source-mounted runs and image builds.
Use `docker-compose.deploy.yml` for release image deployment via
`scripts/deploy_release.sh`.

The next cleanup step should be to convert deployment to a small override file
or a generated compose file, but do that only after validating the release flow:
Compose override semantics can accidentally preserve bind mounts or merge lists
in surprising ways if not tested carefully.
