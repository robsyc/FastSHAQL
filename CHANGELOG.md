# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0](https://github.com/robsyc/fastshaql/compare/v0.1.0..v0.2.0) - 2026-09-29

Breaking release: root query fields now take their names from `sh:codeIdentifier` without the lowercased-plural mangling, the evaluation harness matures into a multi-store matrix, and parser/translation internals were hardened and refactored under mutation testing. Regenerating a 0.1.0 schema renames every root query field (`medicationadministrations` → `medicationAdministration`); generated SPARQL is unchanged.

### Features

- **[breaking]** Derive singular root field names from `sh:codeIdentifier`: the GraphQL type name decapitalized, replacing the lowercased-plural mangling (`medicationadministrations`). Duplicate derived root field names are rejected at build (`DuplicateRootFieldError`) instead of silent last-shape-wins, and `__`-prefixed reserved names are rejected at parse. (#1)
- Multi-store evaluation matrix: nightly parity/performance evaluation covers Oxigraph, Fuseki, and QLever, with GraphDB as the licensed leg and per-store divergences recorded. (#6)
- Optional profiling through the store protocol: `SparqlStore.query` accepts an `ExecutionMetrics` — profiling runs record `execute_ms` end-to-end plus `http_ms`/`decode_ms` in the HTTP store. One-argument stores keep working in production; profiling against them fails loudly. (#6)

### Bug Fixes

- Strict parse-time rejection of ill-formed shapes instead of silent degradation: malformed SHACL-list paths, at-most-one declarations (`sh:path`, `sh:deactivated`, `sh:codeIdentifier`, counts), non-integer count literals, and unsupported `sh:class` forms now raise.
- Coerce `xsd:decimal` literals to float — rdflib's `decimal.Decimal` was rejected by graphql-core's Float serializer, failing the whole field. (#9)

### Security

- Raise the `graphql-core` floor to `>=3.2.12` (CVE) and refresh the Python dependency group. (#8)

### Refactor

- Collapse the translation filters subpackage into `where`/`exists_scope` with promotion state concentrated in one `FieldBindings` object (ADR-0009/0010); extract the datatype grammar into `parser/datatypes` and visibility resolution into `parser/visibility`; one canonical protected-region transform (`map_code_spans`) in the SPARQL lexer. (#3)

### Documentation

- Update the spec snapshots; mature the evaluation harness into a store matrix (ADR-0022); research mutations via shape rules and SPARQL templates (ADR-0024); roadmap refinements.

### Miscellaneous Tasks

- Mutation-testing hardening (#3): survivor waves killed with contract tests across parser, translation, registry, schema, execution, and adapters — floor ratcheted to 94.3, every remaining survivor triaged in docs/mutation-triage.md.
- Nightly badges job: run as a module and restore the checkout around the badges-branch push.

## [0.1.0] - 2026-08-30

First public release. fastshaql turns SHACL shapes into a GraphQL schema and translates GraphQL operations into SPARQL — a read-only operationally-oriented and frontend-friendly interface for RDF knowledge graphs.

- Architecture and module map: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- Feature scope (shipped and deferred): [docs/ROADMAP.md](docs/ROADMAP.md)
- SHACL/SPARQL support matrix: [docs/SUPPORT.md](docs/SUPPORT.md)

Install from PyPI: `pip install fastshaql` — adapters and the remote store ship as extras (`fastshaql[fastapi]`, `fastshaql[django]`, `fastshaql[httpx]`).
