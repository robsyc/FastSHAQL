# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-08-30

First public release. fastshaql turns SHACL shapes into a GraphQL schema and translates GraphQL operations into SPARQL — a read-only operationally-oriented and frontend-friendly interface for RDF knowledge graphs.

- Architecture and module map: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- Feature scope (shipped and deferred): [docs/ROADMAP.md](docs/ROADMAP.md)
- SHACL/SPARQL support matrix: [docs/SUPPORT.md](docs/SUPPORT.md)

Install from PyPI: `pip install fastshaql` — adapters and the remote store ship as extras (`fastshaql[fastapi]`, `fastshaql[django]`, `fastshaql[httpx]`).
