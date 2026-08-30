# ADR-0023 — Package release and CI

**Status:** Active

## Context

fastshaql ships as a Python library with optional extras, published to public PyPI. A release must build reproducibly from a tag, validate the artifacts before they reach the index, publish without long-lived credentials, and show consumers the same reviewed text on PyPI and on the GitHub Release. GitHub Packages does not host Python packages (no PEP 503 Simple API).

## Decision

**Single-phase tag release.** Pushing a `v*.*.*` tag runs the Release workflow: build (`just build`) → smoke (`just smoke-dist`, wheel and sdist) → extract the tag's CHANGELOG.md section (fails the release before publish when absent) → publish → GitHub Release. Pull requests into `main` run the same build + smoke in CI's `build` job, so a broken release path cannot merge.

- **Publishing** uses OIDC trusted publishing: the `pypi` GitHub Environment mints a short-lived token (`id-token: write`, job-scoped) — no API token exists to rotate or leak. PEP 740 attestations are generated with `astral-sh/attest-action` immediately before `uv publish`; uv uploads attestations but never generates them
- **The GitHub Release** carries the dist assets, and its body is the tag's section extracted from CHANGELOG.md (`just release-notes <tag>`) — the changelog is the single source of truth for release notes
- **Safety without a gate variable:** the repository's tag-protection rule (`v*`) controls who can start a release, and go-public ordering (pending trusted publisher configured before the first tag, repository public before the first consumer) replaces the retired two-phase switch

**Versioning SSOT.** Static `version` in `pyproject.toml`, bumped with `uv version`; `fastshaql.__version__` is derived from installed metadata, so `pyproject.toml` is the single source of truth.

CI job layout, check commands, and release mechanics are documented in [CONTRIBUTING](../../CONTRIBUTING.md) — the justfile and the workflow files are the source of truth.

## Rejected

- **GitHub Packages** — no PEP 503 / Python support
- **API tokens** — OIDC trusted publishing is tokenless; nothing to rotate, leak, or scope
- **TestPyPI** — a separate database from PyPI, so test installs resolve dependencies unreliably; the wheel + sdist smoke test is the artifact validation
- **Two-phase `PUBLIC_RELEASE` variable** — the private install-from-tag era is over; tag protection plus go-public ordering make an unconditional tag → publish safe, with one less moving part
- **git-cliff in CI for release notes** — CHANGELOG.md is the single source of truth; the extracted body equals the reviewed changelog, and CI has fewer moving parts
- **Private registry** (CodeArtifact / Gemfury / devpi) — unjustified overhead for a public package

## Consequences

- Every pushed `v*.*.*` tag publishes; the tag-protection rule is the only gate
- Two repository-level rules complete it (neither lives in the workflow files): tag protection (`v*`, maintainers only) and the protected `pypi` environment (deployment restricted to `v*` tags) — re-apply both after any repo migration
- The GitHub Release body is always the reviewed CHANGELOG.md text, never a separately generated artifact
- Consumers install from PyPI: `uv add "fastshaql[extra]"` / `pip install fastshaql[extra]`
- Published files carry PEP 740 attestations, visible on PyPI
