"""llm/base.py — Protocol LLMClient e factory get_llm_client (SDD Bloco 6.2)"""
from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

from diogenes.models import LLMCall, LLMResponse


@runtime_checkable
class LLMClient(Protocol):
    def complete(self, call: LLMCall) -> LLMResponse: ...


def get_llm_client(cycle_id: str, runtime_dir: Path) -> LLMClient:
    """Factory: instancia o cliente correto conforme DIOGENES_ENV."""
    from diogenes.config import get_config
    from diogenes.llm.openrouter import OpenRouterClient
    cfg = get_config()
    if cfg.llm.env == "azure":
        from diogenes.llm.azure_foundry import AzureFoundryClient
        return AzureFoundryClient(cfg=cfg, cycle_id=cycle_id, runtime_dir=runtime_dir)
    return OpenRouterClient(cfg=cfg, cycle_id=cycle_id, runtime_dir=runtime_dir)
