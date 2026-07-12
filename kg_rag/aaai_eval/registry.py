from __future__ import annotations

from pathlib import Path
from typing import Callable

from kg_rag.aaai_eval.adapters.base import MethodAdapter
from kg_rag.aaai_eval.schemas import MethodSpec


AdapterFactory = Callable[[MethodSpec, Path], MethodAdapter]


class AdapterRegistry:
    def __init__(self) -> None:
        self._factories: dict[str, AdapterFactory] = {}

    def register(self, adapter_id: str, factory: AdapterFactory) -> None:
        if adapter_id in self._factories:
            raise ValueError(f"Adapter already registered: {adapter_id}")
        self._factories[adapter_id] = factory

    def create(self, method: MethodSpec, *, base_dir: Path) -> MethodAdapter:
        try:
            factory = self._factories[method.adapter]
        except KeyError as exc:
            raise ValueError(f"Unknown method adapter: {method.adapter}") from exc
        return factory(method, base_dir)

    def adapter_ids(self) -> list[str]:
        return sorted(self._factories)


def default_registry() -> AdapterRegistry:
    from kg_rag.aaai_eval.adapters.story_pilot import StoryPilotArtifactAdapter

    registry = AdapterRegistry()
    registry.register(
        StoryPilotArtifactAdapter.adapter_id,
        lambda method, base_dir: StoryPilotArtifactAdapter(method=method, base_dir=base_dir),
    )
    return registry
