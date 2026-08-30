"""Evaluation-tier triple-store support (ADR-0022).

Groups the store session contract and the evaluation report — the eval-specific
half of ``tests/support``. Generic test support (cases, runners, goldens, …)
stays at the ``support`` root; this package is the only part consumed solely by
``tests/tiers/evaluation/``.
"""
