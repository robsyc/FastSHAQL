"""Shared helpers for translation unit tests."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastshaql.core.translation.scope import TranslationScope
from fastshaql.core.translation.variables import VariableAllocator

if TYPE_CHECKING:
    from fastshaql.core.registry import ShapeRegistry


def translation_scope(registry: ShapeRegistry) -> TranslationScope:
    """Return a root :class:`TranslationScope` for unit tests."""
    allocator = VariableAllocator()
    subject = allocator.allocate("iri")
    return TranslationScope(subject=subject, allocator=allocator, registry=registry)
