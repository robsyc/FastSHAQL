"""Node-expression execution on rdflib — the ambient-binding discipline.

Integration tier: derived-field ``BIND`` emissions must see the ambient
focus variable. rdflib 7.6.0's ``evalExtend`` evaluates ``BIND``
expressions against ``forget()``-filtered solutions, dropping bindings
inherited from outside the ``BIND``'s group — so a ``$this``-referencing
``sh:sparqlExpr`` (plain, or as an ``shnex:if`` condition) wrapped in the
optional-field ``OPTIONAL`` computes on a forgotten focus: silent nulls,
or a condition error routed to ``else`` on every row. The fix these tests
pin: pure-``BIND`` value emissions sit at group level, never inside the
optionality wrap (a lone ``BIND`` cannot eliminate a row — SPARQL §10
leaves the variable unbound on expression error).

Order: plain sparqlExpr → if-condition discrimination → error routing →
impure defaults → impure if-arms and conditions.
"""

from __future__ import annotations

from graphql import graphql
from rdflib import Graph

from fastshaql.core.execution import InMemoryStore, ResolverContext
from fastshaql.core.kernel.io import load_shapes
from fastshaql.core.parser.parse import parse_shapes
from fastshaql.executable import build_executable_schema

_PREFIXES = """
@prefix ex: <http://example.com/> .
@prefix sh: <http://www.w3.org/ns/shacl#> .
@prefix shnex: <http://www.w3.org/ns/shacl-node-expr#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
ex:ThingShape a sh:NodeShape ;
    sh:codeIdentifier "Thing" ;
    sh:targetClass ex:Thing ;
"""


def _schema(shapes_body: str):
    registry = parse_shapes(load_shapes(_PREFIXES + shapes_body))
    return build_executable_schema(registry)


async def _rows(schema, query: str, data: str) -> dict[str, dict[str, object]]:
    """Run *query*; return ``{local IRI name: result row}``."""
    store = InMemoryStore(Graph().parse(data=data, format="turtle"))
    result = await graphql(schema, query, context_value=ResolverContext(store=store))
    assert result.errors is None, result.errors
    assert result.data is not None
    thing: list[dict[str, object]] = result.data["thing"]
    return {str(row["iri"]).rsplit("/", 1)[-1]: row for row in thing}


async def test_optional_sparql_expr_derived_field_computes_values() -> None:
    """An optional (no ``minCount``) ``sh:sparqlExpr``-derived field
    referencing ``$this`` computes per-entity values — not silent nulls
    from a focus-forgotten ``BIND``."""
    schema = _schema(
        """sh:property [
            sh:path ex:slug ;
            sh:codeIdentifier "slug" ;
            sh:datatype xsd:string ;
            sh:maxCount 1 ;
            sh:values [ sh:sparqlExpr "STRAFTER(STR($this), 'example.com/')" ] ;
        ] .
    """
    )
    rows = await _rows(
        schema,
        "{ thing { iri slug } }",
        "@prefix ex: <http://example.com/> .\nex:alpha a ex:Thing .\nex:beta a ex:Thing .",
    )
    assert rows["alpha"]["slug"] == "alpha"
    assert rows["beta"]["slug"] == "beta"


async def test_optional_if_with_sparql_expr_condition_discriminates_rows() -> None:
    """A form-1 ``shnex:if`` whose condition is a ``$this``-referencing
    ``sh:sparqlExpr`` picks the branch per entity — not ``else`` on every
    row from an errored (forgotten-focus) condition."""
    schema = _schema(
        """sh:property [
            sh:path ex:band ;
            sh:codeIdentifier "band" ;
            sh:datatype xsd:string ;
            sh:maxCount 1 ;
            sh:values [
                shnex:if [ sh:sparqlExpr "CONTAINS(STR($this), 'odd')" ] ;
                shnex:then "oddish" ;
                shnex:else "evenish" ;
            ] ;
        ] .
    """
    )
    rows = await _rows(
        schema,
        "{ thing { iri band } }",
        "@prefix ex: <http://example.com/> .\nex:num-odd-1 a ex:Thing .\nex:num-even-2 a ex:Thing .",
    )
    assert rows["num-odd-1"]["band"] == "oddish"
    assert rows["num-even-2"]["band"] == "evenish"


async def test_if_condition_error_routes_to_else_branch() -> None:
    """ADR-0015's else-on-error deviation, behaviourally: an erroring condition
    (``1/x`` with ``x = 0``, or a cast failure) takes the else branch —
    the ``COALESCE(test, false)`` guard — while a succeeding condition on
    the same query takes then (SPARQL §17.4.1.3: COALESCE skips errored
    expressions; §10: the errored ``BIND`` leaves its variable unbound)."""
    schema = _schema(
        """sh:property [
            sh:path ex:band ;
            sh:codeIdentifier "band" ;
            sh:datatype xsd:string ;
            sh:maxCount 1 ;
            sh:values [
                shnex:if [
                    sh:sparqlExpr
                        "1 / <http://www.w3.org/2001/XMLSchema#integer>(STRAFTER(STR($this), 'num-')) > 0.4"
                ] ;
                shnex:then "high" ;
                shnex:else "low" ;
            ] ;
        ] .
    """
    )
    rows = await _rows(
        schema,
        "{ thing { iri band } }",
        "@prefix ex: <http://example.com/> .\nex:num-2 a ex:Thing .\nex:num-0 a ex:Thing .\nex:bogus a ex:Thing .",
    )
    assert rows["num-2"]["band"] == "high"  # 1/2 = 0.5 > 0.4
    assert rows["num-0"]["band"] == "low"  # division by zero → error → else
    assert rows["bogus"]["band"] == "low"  # xsd:integer('') cast error → else


# --- Impure defaults (shnex:filterShape) ---


async def test_defaulted_exists_default_computes_at_group_level() -> None:
    """A pure ``shnex:exists`` default inlines its ``EXISTS`` into the
    group-level ``COALESCE`` ``BIND`` — the exact position the ambient-
    forgetting discipline requires. Behaviourally: an entity with the
    flag gets ``true``, one without gets ``false`` (never a silent null
    from a focus-forgotten inner expression)."""
    schema = _schema(
        """sh:property [
            sh:path ex:hasFlag ;
            sh:codeIdentifier "hasFlag" ;
            sh:datatype xsd:boolean ;
            sh:maxCount 1 ;
            sh:defaultValue [ shnex:exists [ shnex:pathValues ex:flag ] ] ;
        ] .
    """
    )
    rows = await _rows(
        schema,
        "{ thing { iri hasFlag } }",
        '@prefix ex: <http://example.com/> .\nex:t1 a ex:Thing ; ex:flag "y" .\nex:t2 a ex:Thing .',
    )
    assert rows["t1"]["hasFlag"] is True
    assert rows["t2"]["hasFlag"] is False


async def test_defaulted_filter_shape_passing_conjunct_binds_value() -> None:
    """An impure default whose candidate conforms keeps the value: the
    ``shnex:filterShape`` output (node-expr §4.2.5) is the candidate, and
    the ``COALESCE`` yields it when the path/values miss."""
    schema = _schema(
        """sh:property [
            sh:path ex:grade ;
            sh:codeIdentifier "grade" ;
            sh:datatype xsd:string ;
            sh:maxCount 1 ;
            sh:defaultValue [
                shnex:nodes "raw" ;
                shnex:filterShape [ sh:hasValue "raw" ] ;
            ] ;
        ] .
    """
    )
    rows = await _rows(
        schema,
        "{ thing { iri grade } }",
        "@prefix ex: <http://example.com/> .\nex:t1 a ex:Thing .",
    )
    assert rows["t1"]["grade"] == "raw"


async def test_defaulted_filter_shape_failing_conjunct_keeps_row() -> None:
    """A candidate failing the conjuncts is *not in the default's output*
    (node-expr §4.2.5) — the field falls to null on its non-null contract
    (SD-6): the entity row survives at the SPARQL layer, surfacing as a
    loud GraphQL error that nulls the query via non-null propagation —
    not the pre-fix silent drop (``{"thing": []}`` with no error)."""
    schema = _schema(
        """sh:property [
            sh:path ex:grade ;
            sh:codeIdentifier "grade" ;
            sh:datatype xsd:string ;
            sh:maxCount 1 ;
            sh:defaultValue [
                shnex:nodes "raw" ;
                shnex:filterShape [ sh:hasValue "other" ] ;
            ] ;
        ] .
    """
    )
    store = InMemoryStore(
        Graph().parse(
            data="@prefix ex: <http://example.com/> .\nex:t1 a ex:Thing .",
            format="turtle",
        )
    )
    result = await graphql(
        schema, "{ thing { iri grade } }", context_value=ResolverContext(store=store)
    )
    assert result.errors is not None
    assert any("grade" in e.message for e in result.errors)
    assert result.data is None  # non-null propagation nulls the query


async def test_defaulted_if_missing_else_true_condition_binds_default() -> None:
    """An ``shnex:if``-shaped default with a missing ``shnex:else`` whose
    condition is true binds the default: the if-output is the then value
    (node-expr §4.1.6), flowed through the ``COALESCE``. The if lowers to
    an all-row-keeping bag (one conditioned ``OPTIONAL``), which must sit
    flat — a wrapping ``OPTIONAL`` around it is the doubly-nested shape
    rdflib mis-scopes (module docstring)."""
    schema = _schema(
        """sh:property [
            sh:path ex:grade ;
            sh:codeIdentifier "grade" ;
            sh:datatype xsd:string ;
            sh:maxCount 1 ;
            sh:defaultValue [
                shnex:if [ shnex:exists [ shnex:pathValues ex:flag ] ] ;
                shnex:then "flagged" ;
            ] ;
        ] .
    """
    )
    rows = await _rows(
        schema,
        "{ thing { iri grade } }",
        '@prefix ex: <http://example.com/> .\nex:t1 a ex:Thing ; ex:flag "y" .',
    )
    assert rows["t1"]["grade"] == "flagged"


async def test_defaulted_if_missing_else_false_condition_keeps_row() -> None:
    """The same default on a condition-false entity: empty if-output (the
    missing else is the empty list, node-expr §4.1.6) → no default → the
    non-null contract errors loudly (SD-6) and the entity row survives —
    never a silently dropped row from a mis-scoped condition ``FILTER``."""
    schema = _schema(
        """sh:property [
            sh:path ex:grade ;
            sh:codeIdentifier "grade" ;
            sh:datatype xsd:string ;
            sh:maxCount 1 ;
            sh:defaultValue [
                shnex:if [ shnex:exists [ shnex:pathValues ex:flag ] ] ;
                shnex:then "flagged" ;
            ] ;
        ] .
    """
    )
    store = InMemoryStore(
        Graph().parse(
            data="@prefix ex: <http://example.com/> .\nex:t1 a ex:Thing .",
            format="turtle",
        )
    )
    result = await graphql(
        schema, "{ thing { iri grade } }", context_value=ResolverContext(store=store)
    )
    assert result.errors is not None
    assert any("grade" in e.message for e in result.errors)
    assert result.data is None  # non-null propagation nulls the query


# --- Form-2 branch FILTERs (impure arms) ---


async def test_if_impure_branch_filter_stays_in_branch() -> None:
    """Form-2 ``shnex:if`` (single-valued, impure arm): the branch's
    conjunct ``FILTER`` must only ever affect its own branch — an impure
    *then* arm sub-binds inside its own ``OPTIONAL``, and ``IF``
    laziness (SPARQL §17.4.1.2 — only one branch operand is evaluated)
    keeps the unbound branch variable from touching else-routed rows.
    Pre-fix: the flat conjunct ``FILTER`` nulled ``band`` on *every* row,
    including the else-routed one."""
    schema = _schema(
        """sh:property [
            sh:path ex:band ;
            sh:codeIdentifier "band" ;
            sh:datatype xsd:string ;
            sh:maxCount 1 ;
            sh:values [
                shnex:if [ shnex:exists [ shnex:pathValues ex:flag ] ] ;
                shnex:then [
                    shnex:nodes "raw" ;
                    shnex:filterShape [ sh:hasValue "nomatch" ] ;
                ] ;
                shnex:else "fallback" ;
            ] ;
        ] .
    """
    )
    rows = await _rows(
        schema,
        "{ thing { iri band } }",
        '@prefix ex: <http://example.com/> .\nex:t1 a ex:Thing ; ex:flag "y" .\nex:t2 a ex:Thing .',
    )
    assert rows["t1"]["band"] is None  # cond true, conjunct fails → empty output
    assert rows["t2"]["band"] == "fallback"  # cond false → else, uncorrupted


async def test_if_impure_condition_failed_conjunct_routes_to_else() -> None:
    """An impure *condition* (``shnex:filterShape``) whose conjunct fails
    has empty output — not ``( true )`` — so node-expr §4.1.6 routes to
    else; its conjunct ``FILTER`` must not eliminate the row. The
    ``COALESCE(test, false)`` guard composes: unbound ``?_cond`` errors
    the comparison, the guard converts it to ``false`` → else."""
    schema = _schema(
        """sh:property [
            sh:path ex:band ;
            sh:codeIdentifier "band" ;
            sh:datatype xsd:string ;
            sh:maxCount 1 ;
            sh:values [
                shnex:if [
                    shnex:nodes "cond-candidate" ;
                    shnex:filterShape [ sh:hasValue "nomatch" ] ;
                ] ;
                shnex:then "then-value" ;
                shnex:else "else-value" ;
            ] ;
        ] .
    """
    )
    rows = await _rows(
        schema,
        "{ thing { iri band } }",
        "@prefix ex: <http://example.com/> .\nex:t1 a ex:Thing .",
    )
    assert rows["t1"]["band"] == "else-value"
