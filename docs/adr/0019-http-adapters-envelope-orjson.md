# ADR-0019 — HTTP adapters, envelope, and orjson

**Status:** Active

## No GraphQL server library

Findings: **graphql-core ships no server** — it is the spec implementation (parse/validate/execute) and nothing more. **Strawberry cannot consume a `GraphQLSchema`** — its router takes `@strawberry.type` classes, strictly one-way, so adopting it would force re-expression of the entire generated schema as decorator classes (the superseded Strawberry-native design). `graphql-server-core` is unmaintained; `graphql-server`/Starlette adds protocol-boilerplate dependencies; Ariadne ties consumers to its own schema-construction API. The schema is already executable (ADR-0002); a middleman library would only re-own schema construction — a job fastshaql already does from Shape IR.

**Decision: hand-roll the `graphql-core ↔ HTTP` glue** in `fastshaql.adapters.{fastapi,django}`, depending on the web framework as an **optional extra** and taking no GraphQL server library. The adapter is genuine framework code — an `APIRouter` / a `View` — with full access to the host app's dependency injection, middleware, auth, and async; `ResolverContext` injection is under exact adapter control, not a library's. The request-validation ladder, error payload, and response serialization live once in Core and are shared by both adapters. Reversible: a future adapter demanding a library can be added without touching Core.

## Envelope contract

- **POST-only** execution at the path; body is `application/json` `{query, variables?, operationName?}` — malformed bodies are 400, fail-fast, first error wins
- **Wrong `Content-Type` → 415.** Only `application/json` prefixes are accepted (`text/plain`, form-encoded, unrelated `+json` suffixes rejected) — this doubles as the **CSRF mitigation**: a cross-origin form or plain-text fetch cannot set a JSON Content-Type without triggering a CORS preflight, which the browser blocks
- **HTTP 200 for every well-formed request**, including validation and field errors — `{data, errors}` carries the outcome (the conformant always-200 policy; monitoring must inspect the `errors` array, not the status). Status-code-by-error-class is deferred
- **GraphiQL behind a build-time flag** (`ide=True` serves it at the same path it queries; `ide=False` omits the GET route entirely — with the IDE disabled, GET answers 405 on both adapters: FastAPI's POST-only route; Django's `HttpResponseNotAllowed`) — a flag, not a runtime/auth gate; production deployments front the route themselves
- GraphiQL is delivered via an **ESM import map with pinned versions + SRI integrity hashes**, not a bundled asset — zero npm/webpack in the repo, no extra dependency

Both adapters implement this envelope through one shared Core call; their HTTP-contract tests mirror each other.

## orjson at the two JSON seams

The result pipeline has exactly two JSON boundaries — decoding the SPARQL-results+json wire body (`decode_sparql_results`, the shared decoder every HTTP-backed store calls) and encoding the GraphQL response. Both were stdlib `json`; evals showed orjson measurably faster at both. **orjson is a base dependency**, confined to those two modules so a revert is mechanical; it is not used in translation or SPARQL rendering (pure string-building, no JSON). **Intended behavior change:** Django responses now emit raw UTF-8 (matching FastAPI) instead of `\uXXXX`-escaped ASCII — status codes, messages, and fail-fast order unchanged.

Base install (`pip install fastshaql`) pulls `rdflib` + `graphql-core` + `orjson`; frameworks arrive only via their extras.

## Consequences

- A plain JSON POST client works with no special headers beyond Content-Type; clients POSTing `text/plain` or form-encoded bodies (curl defaults, some older GraphQL clients) get 415, not a silent parse failure — deliberate, documented for adopters
- Django's `async` view wants an ASGI deployment — under WSGI it degrades to a threadpool (functional, not optimal); FastAPI has no such split
- Lazy top-level imports in `fastshaql.adapters.*` keep the base install from ever importing a framework
- The orjson move mirrors the ship-behind-narrow-seams-then-confirm arc of ADR-0018 — the revert stays mechanical
- Subscriptions are out of scope: the `SparqlStore` protocol is SELECT-only; a streaming store contract would be a separate design
- Deferred to the [ROADMAP](../ROADMAP.md): GET-query execution, request batching, `application/graphql-response+json` status semantics
