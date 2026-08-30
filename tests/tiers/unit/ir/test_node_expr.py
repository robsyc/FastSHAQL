"""Unit tests for the node-expression IR structural predicates."""

from typing import cast

import pytest

from fastshaql.core.ir.node_expr import NodeExprIR, is_multivalued_capable, is_total


def test_union_predicates_fail_loudly_on_unknown_arm() -> None:
    """The closed ``NodeExprIR`` union's structural predicates raise on an
    unlisted arm (docstring contract: a forgotten arm is a loud
    ``assert_never`` failure, never a silent single-valued fall-through)."""
    intruder = cast("NodeExprIR", object())
    with pytest.raises(AssertionError):
        is_multivalued_capable(intruder)
    with pytest.raises(AssertionError):
        is_total(intruder)
