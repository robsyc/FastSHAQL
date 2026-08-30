"""Translation ``VariableMap`` smoke — ``core/translation/`` (ADR-0013).

Integration tier: declarative fixture wiring without full execution. SPARQL
golden strings for fixture cases are asserted in ``tests/tiers/e2e/`` via
``RecordingStore``.

Order: minimal smoke ``VariableMap`` checks.
"""

from __future__ import annotations

from rdflib import Variable

from support.cases import CaseSet
from support.runners import translate_case


def test_translate_minimal_smoke_var_map() -> None:
    result = translate_case(CaseSet("minimal"), "smoke")
    assert result.var_map.subject_var == Variable("iri")
    assert result.var_map.fields == {
        "iri": Variable("iri"),
        "label": Variable("label"),
    }
    assert result.var_map.relationships == {}
