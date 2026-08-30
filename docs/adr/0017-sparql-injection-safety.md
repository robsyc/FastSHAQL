# ADR-0017 — SPARQL injection safety

**Status:** Active

## Threat model

- **Untrusted** — the GraphQL operation: query text, variables, all `where` filter values, `lang_tags`, `limit`/`offset`, enum selections
- **Trusted** — the SHACL shapes graph, including embedded derived-field SPARQL (`sh:select`, `sh:sparqlExpr`, ADR-0015). The only runtime substitution into author SPARQL is the focus-node variable, which is fastshaql-generated — never client text

## Decision

**One render chokepoint.** Translation produces a frozen, typed AST whose terminal positions are rdflib terms; SPARQL text is assembled in exactly one place — `render_term` (`core/sparql/terms.py`) — and `execute_query` (`core/execution/`) is the sole site that materializes the string.

**No client value is ever concatenated into SPARQL text.** Every leaf reaches the string through the chokepoint:

- `Literal.n3()` applies SPARQL/Turtle string escaping
- `URIRef.n3()` validates the IRI and raises on breakout characters
- All other interpolation in the render layer is fixed SPARQL syntax — keywords, operators, joiners, recursion over already-rendered children; `LIMIT`/`OFFSET` interpolate ints guarded non-negative
- Operator and function names are never interpolated from client strings — they come from fixed dicts, and a graphql-core-validated enum name is re-mapped to a server-trusted rdflib term before rendering

**Two defence layers.** graphql-core validates the operation before resolvers run (typed coercion, enum membership, known field/argument names, `Int` for `limit`/`offset`). Term rendering is the **real** boundary: it holds even if graphql-core validation is bypassed (e.g. a direct `translate_query` call), because client values are wrapped in `Literal`/`URIRef` at the translation edge.

## Considered options

- **Store-side parameterised queries (bind variables) as primary defence:** rejected — fastshaql emits a single rendered string to a `SparqlStore`, and bind-variable semantics are uneven across SPARQL endpoints; parameterisation can be revisited per-store if a future adapter prefers prepared queries
- **Hand-rolled escaping in translation:** rejected — `rdflib.n3()` is the canonical, spec-aligned escaper; re-implementing it would be error-prone and drift from the grammar

Residual hardening items (IRI edge validation at the translation edge, negative `limit` as a validation error, a configurable max-limit) are recorded in the [ROADMAP](../ROADMAP.md) backlog — none are injection bugs.
