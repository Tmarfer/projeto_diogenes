"""
llm/azure_foundry.py — DVA-CBS | Projeto Diógenes
AzureFoundryClient — implementação futura para produção institucional.

Stub criado desde o início para forçar o design da interface a contemplar
os dois providers (SDD Bloco 1.2.4 e Bloco 14.7).

Para implementar: substituir NotImplementedError pela lógica real usando
o mesmo openai SDK com base_url apontando para o endpoint do Foundry.
Adicionar azure-identity como dependência de runtime nesse momento.
"""

from __future__ import annotations

from pathlib import Path

from diogenes.config import DiogenesConfig
from diogenes.models import LLMCall, LLMResponse


class AzureFoundryClient:
    """
    Cliente LLM para Azure AI Foundry (produção pós-piloto).
    Implementa a interface LLMClient.
    """

    def __init__(self, cfg: DiogenesConfig, runtime_dir: Path) -> None:
        self._cfg = cfg
        self._runtime_dir = runtime_dir

    def complete(self, call: LLMCall) -> LLMResponse:
        raise NotImplementedError(
            "AzureFoundryClient não implementado. "
            "Implementar quando a migração para Azure AI Foundry for aprovada."
        )
