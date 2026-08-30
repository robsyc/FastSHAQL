# ADR-0007 — Parse-time description language selection

**Status:** Active

## Context

graphql-core builds one `GraphQLSchema` at startup; `description` is a static `str` on each type/field with no per-request introspection hook. Descriptions therefore cannot vary per request without rebuilding the schema or a custom introspection layer — unlike instance-data language handling (ADR-0012), which is a translation-time concern.

## Decision

Descriptions are selected **once at parse time** and frozen into the IR: a preference chain — preferred language > untagged > any other language — applied within each description predicate, falling through to the next predicate only when the current one has no value. The preferred language defaults to `en` and is configurable via `parse_shapes(description_language=)`; hardcoding `en` with no knob was rejected as a footgun for non-English-primary graphs. Only SHACL-sourced text is wired into the schema (object types, fields, root fields); synthetic elements (`iri`, `where`/`limit`/`offset` arguments, filter inputs) get none.

The implicit precedence **deliberately diverges** from the query-time language chain (ADR-0012): schema text needs one string at parse time, so the fallback must terminate somewhere; a query has a natural null and should not hide values the client did not ask for. The two mechanisms share the precedence idea and nothing else.

Richer §8 non-validating characteristics (`sh:order`, `sh:group`, `sh:unit`, …) are deferred: graphql-core cannot introspect or SDL-print applied custom directives, so they would be invisible to any consumer that introspects the schema. Revisit when a real consumer exists.
