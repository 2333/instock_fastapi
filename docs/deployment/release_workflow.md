# Release Workflow

This project uses a lightweight release workflow suitable for a solo-maintained
full-stack application.

## Environment Model

- `dev`: long-lived environment for daily front/back-end collaboration
- `prod`: long-lived production environment
- `staging`: temporary environment, started only for higher-risk verification

Do not keep staging running by default.

## Version Source Of Truth

Repository versioning is driven by the root `VERSION` file and synced to:

- `pyproject.toml`
- `web/package.json`
- `web/package-lock.json`

Use these commands:

```bash
make version-show
make version-check
make version-bump-patch
make version-bump-minor
make version-bump-major
```

## Version Bump Convention

Run the version bump when the branch is ready to merge back to the mainline, not
for every local commit.

- `patch`: bug fixes, small improvements, refactors, crawler/data-source fixes
- `minor`: backward-compatible features, new pages, new APIs, new tasks/capabilities
- `major`: breaking API/config/data-contract changes

If uncertain, choose `patch`.

## Pre-Merge Checklist

Before merging a branch:

1. Stop temporary staging if it was only used for verification.
2. Run `make merge-check`.
3. Choose and run one version bump command.
4. Review the diff for environment or deployment changes carefully.
5. Merge to the mainline branch.

## Production Release

After the merge lands:

```bash
make prod-build-version VERSION=x.y.z
make prod-deploy-version VERSION=x.y.z
make prod-smoke
```

If the release changes data shape, scheduler behavior, or backfill logic, bring
up staging before production deployment and validate there first.
