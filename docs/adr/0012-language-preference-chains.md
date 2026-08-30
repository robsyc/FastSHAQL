# ADR-0012 — Language preference chains

**Status:** Active

## A request parameter, not a per-field filter

Language preference for language-accepting properties is a cross-cutting request parameter — a client wants "all persons in English", not "persons whose English name matches X". `QueryContext.lang_tags` carries an **ordered chain** (BCP 47 basic ranges plus sentinels; grammar in the [support matrix](../SUPPORT.md)); each language-accepting field resolves to the first step with a value, falling back through the chain. The empty tuple means *no preference* — no language machinery is emitted anywhere. Translation consumes the chain verbatim; normalization is the Accept-Language resolver's job, the single site where it happens.

## Strict precedence

The first chain step with any matching value for that entity wins the field; when the chain is exhausted, the field is **null** (or the entity drops, when the field is required) — the null terminal falls out of `COALESCE` error semantics with no scaffolding. There is **no implicit any-language terminal and no implicit untagged terminal**: best-effort is opt-in — a caller wanting it writes the sentinels into the chain explicitly. The chain stays a complete, literal description of precedence and never hides values the client did not ask for.

The chain is request-level — one chain per operation, never per field; per-field language arguments would be a separate, deferred mechanism (ROADMAP).

Sentinels are ordinary chain entries — usable anywhere in the chain, order significant; single-entry chains are not special-cased. Step matching is range-based (`"en"` serves `en-US`); a chain wanting exact-`en`-only is not expressible — deferred with the other named remainders (ROADMAP).

**One exception — string-union properties** (a scalar whose declared datatypes span `xsd:string` and a language-tagged string type): the untagged terminal *is* implicit and always last. The union declares plain strings a first-class lane of the value space; untagged is the absence of a language, not one.

The rule is per-field, not per-entity-kind: selected, promoted, and filter-only fields resolve identically, and "required" re-states as *resolves to a value*. Filters over chain-resolved fields compare `STR()` of the resolved variable — the value the client would see, language-agnostic.

## Divergence from parse-time selection

This strict precedence deliberately diverges from parse-time description selection (ADR-0007: preferred > untagged > any): schema text needs one string at parse time, so the fallback must terminate; a query has a natural null. The two mechanisms share the precedence idea and nothing else.

## Converter safety

Per-step `OPTIONAL`s multiply rows cartesian across steps, but the converter needs no change: the resolved variable is `COALESCE`-identical in every row of an entity whenever the winning step matched anywhere (last-write-wins is stable), and list fields keep a single-variable shape.

Cost grows multiplicatively with per-step matches — bounded by the request (realistic chains are one to three entries) — an evaluation-tier concern, not a blocker. Adapters stay thin: a caller's `context_getter` resolves the framework header via the Core Accept-Language helper; no subtag expansion, no locale bundling, no injected defaults.

## Accept-Language resolution

`lang_tags_from_accept_language` (Core, exported from `fastshaql.core`) is the single normalization site: an Accept-Language header value becomes a chain of BCP 47 basic ranges (RFC 9110 §12.5.4 / RFC 4647). Entries are comma-separated; the tag is the segment before the first `;`, lowercased; `*` passes through as the any-language sentinel. Each entry carries an optional `q` weight (RFC 9110 §12.4.2): `0` with up to three decimals or `1` with up to three zeros, name case-insensitive, ASCII digits only. A malformed parameter is skipped, not the entry — the weight falls back to 1.0, so a later valid `q` in the same entry may still win (the RFC constrains senders only; recipient handling of invalid weights is unspecified). `q=0` entries drop; the rest sort weight-descending, first-seen on ties; exact duplicates keep the higher-weighted occurrence. `None` or a blank header yields the empty chain. No subtag expansion, and the untagged sentinel `""` is never synthesized — the header cannot express it, and best-effort stays explicit.
