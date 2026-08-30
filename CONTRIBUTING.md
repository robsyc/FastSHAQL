# Contributing

This document is a **reference** for anyone (human or agent) setting up a working environment and shipping a change.

## Development setup

Requires a Python version within the bounds declared in [pyproject.toml](pyproject.toml) (the CI matrix lists what is actually tested), [uv](https://docs.astral.sh/uv/) and [just](https://github.com/casey/just). Python is pinned in [.python-version](.python-version); the uv and just versions in [.tool-versions](.tool-versions).

```bash
just sync   # or: uv sync --all-extras --all-groups --all-packages
just hooks  # install the git hooks (lefthook; see lefthook.yml)
```

## Common tasks

All tasks are [just](https://github.com/casey/just) recipes — **run `just` to list them and use them consistently** (each recipe carries its own doc comment in the justfile); `just ci` is the pre-push gate. Policy the recipes can't tell you:

- `just eval` needs Docker **and a GraphDB license**; otherwise the tier is silently skipped (details in [tests/README.md](tests/README.md)).
- `just complexity` ratchets cognitive complexity against the committed `complexipy-snapshot.json`; a *passing* run rewrites the snapshot (auto-shrink) — accept an intentional increase with `just complexity-update`.
- `just mutate` gates on the committed mutation-score floor (`mutmut-floor.json`); the run is incremental from the cached `mutants/` directory.

## Code style

The tools are configured in [pyproject.toml](pyproject.toml) — that file is authoritative; the rules are not restated here.

- **ruff** — lint + format (rule families in `[tool.ruff]`).
- **ty** — type checker, run with `error-on-warning`.
- **Docstrings** follow the conventions below.

**Complexity gates.** ruff enforces per-function cyclomatic complexity (`C901`, max 15) as a *blocking* check; complexipy additionally enforces **cognitive** (nesting-weighted) complexity at the same threshold via the committed baseline (see above).

**Module boundaries.** [tach](https://docs.gauge.sh/) statically enforces the module DAG and the pinned public interfaces declared in [tach.toml](tach.toml) (`just architecture`, blocking in CI; ADR-0003). The framework-neutral Core may not import the Adapters (ADR-0001), declared-but-unused dependencies fail (`exact`), and cycles are forbidden. After editing `tach.toml`, regenerate the diagram in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) with `just module-graph`.

### Docstring conventions

The codebase maps directly to external specifications (SHACL 1.2, SPARQL 1.2, GraphQL); docstrings keep that mapping visible.

- **Module docstrings** — one-line summary, optional prose paragraph, full spec URL(s):

  ```python
  """Render RDFLib terms to SPARQL syntax.

  Uses RDFLib's ``n3()`` for URIRef, Literal, and BNode rendering.

  See: https://www.w3.org/TR/sparql12-query/#syntaxTerms
  """
  ```

- **Class and function docstrings** — one-line summary with spec *section numbers*, not full URLs (the module docstring already links the spec): `"""Degenerate property path: a single IRI (SPARQL §9)."""`. Google-style `Args:`/`Returns:` sections are reserved for entry-point functions — the public API surface (`parse_shapes`, `translate_query`, `build_schema`, …).
- **Dataclass fields** — inline attribute docstring on every field (no `Args:` sections for frozen dataclasses; the field docstring already documents the attribute).
- **Test file docstrings** — every `tests/tiers/**/test_*.py` module carries: a one-line summary (module under test, backtick-quoted path, optional ADR references), a prose paragraph (what the tests exercise and how), and an order line describing the file's ordering convention. Tests flow simple → complex within each file; mark logical groups with `# --- Section name ---` comments matching the order line. Naming: `test_{unit}_{scenario}_{expectation}` when useful for disambiguation.
- **Coverage** — every public class, function, and dataclass field gets a docstring. No exceptions.

## Testing

`just test` runs the default suite; a single tier: `just test -m e2e`. The triple-store evaluation tier (`just eval`) requires Docker and a license — see below.

The full test reference — directory layout, the tier model, fixtures (cases vs scenarios), the evaluation harness, the `demo/`↔`tests/` boundary, and coverage mechanics — lives in [tests/README.md](tests/README.md). Tier markers are auto-stamped from the test directory, and coverage runs in CI with branch coverage.

### Coverage exception policy

The deliverable is **100% accounted-for, not 100% executed**: every uncovered line is either covered by a test or annotated with a rationale.

- **Gate** — `[tool.coverage.report] fail_under` in [pyproject.toml](pyproject.toml) is **100**, locking the achieved floor against drift; CI enforces it via the `just test-cov` recipe.
- **Annotation convention** — `# pragma: no cover` plus a short inline reason that states *why*, not just *that*: `unreachable — graphql-core validates …`, `defensive — direct-call contract only`. A bare pragma without a reason is not accepted.
- **Mutation floor** — `just mutate` gates on the committed floor (`mutmut-floor.json`); raising it is deliberate, via the same recorded-rationale discipline.

## CI

CI ([.github/workflows/ci.yml](.github/workflows/ci.yml)) runs the same `just` recipes you run locally: each job installs the shared toolchain via a local composite action ([.github/actions/toolchain](.github/actions/toolchain/action.yml)) — uv and just versions come from [.tool-versions](.tool-versions), the single source of truth — then invokes `just <recipe>`; workflows only pick recipes and carry glue (artifacts). Nightly ([nightly.yml](.github/workflows/nightly.yml)): triple-store evaluation (GraphDB community), advisory preview-lint drift, and the mutation score floor; its `badges` job regenerates the coverage/mutants/complexity endpoint badges and pushes them to the `badges` branch.

## Demo / benchmarking environment

The `demo/` package is a workspace member and is **not** published. It combines the quickstart playground (guided tour in [demo/README.md](demo/README.md)) with reference FastAPI wiring (the shipped `httpx`-extra store + FastAPI lifespan) over your own shapes and data.

See [demo/README.md](demo/README.md) for the tour, reference wiring, and throughput/load-test usage.

## Release

Releases are published to PyPI from an annotated `vX.Y.Z` tag. The release workflow ([.github/workflows/release.yml](.github/workflows/release.yml)) builds the distribution, smoke-tests the wheel and sdist, publishes to PyPI via OIDC trusted publishing (attestations included), and opens a GitHub Release whose body is the tag's section of [CHANGELOG.md](CHANGELOG.md), extracted with `just release-notes <tag>` — the extraction runs in the build job, so a tag without a changelog section fails before anything is published. Pull requests into `main` run the same build and smoke in CI's `build` job. Full details: [ADR-0023](docs/adr/0023-package-release-and-ci.md).

```bash
uv version --bump <part>  # major, minor, patch
just changelog            # git-cliff draft (cliff.toml) + CITATION.cff sync (version, date-released)
# curate the new CHANGELOG.md section, then:
git commit -am "Release <tag>"
git tag -a "<tag>" # vX.Y.Z
git push && git push --tags
# consumer:
#   uv add "fastshaql[fastapi]"
```

Commit messages follow [Conventional Commits](https://www.conventionalcommits.org/) (`feat`, `fix`, `docs`, …) — `just changelog` groups the changelog by those types.

## Background reading

Authoritative specifications relevant to fastshaql:

- SHACL 1.2 core (draft): <https://www.w3.org/TR/shacl12-core/> · SPARQL extensions: <https://www.w3.org/TR/shacl12-sparql/> · node expressions: <https://www.w3.org/TR/shacl12-node-expr/>
- SPARQL 1.2 query: <https://www.w3.org/TR/sparql12-query/> · update: <https://www.w3.org/TR/sparql12-update/>
- GraphQL: <https://spec.graphql.org/October2021/>
- TopQuadrant `graphql:` namespace and docs (origin of the visibility mechanism): <https://datashapes.org/graphql> · <https://docs.topquadrant.com/latest/graphql/>

Markdown snapshots of the SHACL/SPARQL editors' drafts are committed under [`docs/references/`](docs/references/) and refreshed with `just fetch-specs`.
