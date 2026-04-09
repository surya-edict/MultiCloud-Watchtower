from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, Iterable, List, Optional

from src.config.settings import Settings
from src.models.schemas import CostRecord

"""
Core Provider Registry module.
Implements the Registry Pattern to decouple cloud-specific execution logic
from the main orchestrator, satisfying the Open-Closed Principle.
"""


@dataclass(frozen=True)
class ProviderSpec:
    """
    Defines the strict interface/contract for any cloud cost provider.
    
    Attributes:
        key (str): Unique internal identifier (e.g., 'aws').
        label (str): Human-readable display name for logging and alerts.
        is_configured (Callable): Function that checks settings to see if this provider should run.
        fetch (Callable): Function that actually executes the data collection.
    """
    key: str
    label: str
    is_configured: Callable[[Settings], bool]
    fetch: Callable[[Settings], List[CostRecord]]


class ProviderRegistry:
    """
    Stateful registry that manages the registration, ordering, and retrieval
    of available cloud provider specs.
    """
    def __init__(self) -> None:
        self._providers: Dict[str, ProviderSpec] = {}
        self._order: List[str] = []

    def register(self, spec: ProviderSpec) -> None:
        """
        Adds a new provider to the registry. Preserves the registration
        order so the pipeline processes them deterministically.
        """
        if spec.key not in self._providers:
            self._order.append(spec.key)
        self._providers[spec.key] = spec

    def get(self, key: str) -> Optional[ProviderSpec]:
        """Looks up a provider by its unique string key."""
        return self._providers.get(key)

    def ordered(self) -> Iterable[ProviderSpec]:
        """Yields all registered providers in the order they were added."""
        for key in self._order:
            spec = self._providers.get(key)
            if spec is not None:
                yield spec

    def clear(self) -> None:
        """Flushes the registry. Used primarily for unit test isolation."""
        self._providers.clear()
        self._order.clear()


_DEFAULT_REGISTRY: ProviderRegistry | None = None


def get_registry() -> ProviderRegistry:
    """
    Singleton accessor for the global ProviderRegistry instance.
    Lazy-loads and registers all built-in providers upon first invocation.
    
    Returns:
        ProviderRegistry: The initialized global registry.
    """
    global _DEFAULT_REGISTRY
    if _DEFAULT_REGISTRY is None:
        registry = ProviderRegistry()
        # Lazy import to prevent circular dependencies
        from src.collectors.providers_builtin import register_builtin_providers

        register_builtin_providers(registry)
        _DEFAULT_REGISTRY = registry
    return _DEFAULT_REGISTRY

