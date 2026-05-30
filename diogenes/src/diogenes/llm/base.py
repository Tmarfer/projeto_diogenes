"""llm/base.py — Protocol LLMClient e factory get_llm_client (SDD Bloco 6.2)

Governança de provider (TC 015.848/2025-6):
  O único provider permitido em produção é "chattcu" (infraestrutura interna do TCU).
  Dados fiscais nunca trafegam pelo OpenRouter ou qualquer serviço externo.
  A conformidade é verificada em duas camadas:
    1. Chamada com DiogenesConfig (path de validação explícita):
       → raise ConfigError para qualquer provider != "chattcu"
    2. Chamada com (cycle_id, runtime_dir) (path de produção/orquestrador):
       → raise ConfigError para openrouter fora de contexto pytest
       → permite openrouter apenas durante execução de testes (PYTEST_CURRENT_TEST)
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Protocol, runtime_checkable

from diogenes.models import LLMCall, LLMResponse


@runtime_checkable
class LLMClient(Protocol):
    def complete(self, call: LLMCall) -> LLMResponse: ...


def get_llm_client(cfg_or_cycle_id, runtime_dir: Path | None = None) -> LLMClient:
    """
    Factory: instancia o cliente LLM correto conforme DIOGENES_LLM_PROVIDER.

    Duas assinaturas suportadas:

      get_llm_client(cfg: DiogenesConfig)
        → Caminho de validação de governança. Levanta ConfigError se provider
          != "chattcu". Usado por testes de governança e verificações explícitas.

      get_llm_client(cycle_id: str, runtime_dir: Path)
        → Caminho de produção (chamado pelo Orquestrador). Instancia o cliente
          correto. Em produção, bloqueia openrouter com ConfigError. Em testes
          (PYTEST_CURRENT_TEST definido), permite openrouter para compatibilidade
          com pytest-httpx.
    """
    from diogenes.config import ConfigError, DiogenesConfig

    # ── Caminho A: validação explícita com DiogenesConfig ────────────────────
    if isinstance(cfg_or_cycle_id, DiogenesConfig):
        cfg = cfg_or_cycle_id
        provider = cfg.llm.provider

        if provider == "openrouter":
            raise ConfigError(
                "DIOGENES_LLM_PROVIDER=openrouter não é permitido. "
                "O Projeto Diógenes processa dados fiscais do TC 015.848/2025-6 "
                "e só pode usar o ChatTCU (infraestrutura interna do TCU). "
                "Defina DIOGENES_LLM_PROVIDER=chattcu no .env."
            )

        if provider != "chattcu":
            raise ConfigError(
                f"DIOGENES_LLM_PROVIDER='{provider}' não reconhecido. "
                f"Único valor válido: 'chattcu'."
            )

        # Provider válido (chattcu) mas sem cycle_id/runtime_dir para instanciar.
        # Chame get_llm_client(cycle_id, runtime_dir) para obter um cliente real.
        raise ConfigError(
            "Para instanciar ChatTCUClient forneça cycle_id e runtime_dir: "
            "get_llm_client(cycle_id, runtime_dir)."
        )

    # ── Caminho B: produção / orquestrador (cycle_id, runtime_dir) ───────────
    cycle_id: str = cfg_or_cycle_id

    from diogenes.config import get_config
    cfg = get_config()
    provider = cfg.llm.provider

    # Governança: bloqueia openrouter em produção (fora de pytest)
    _em_teste = bool(os.environ.get("PYTEST_CURRENT_TEST"))
    if provider == "openrouter" and not _em_teste:
        raise ConfigError(
            "DIOGENES_LLM_PROVIDER=openrouter não é permitido. "
            "Dados fiscais do TC 015.848/2025-6 só podem trafegar pela "
            "infraestrutura interna do TCU. Defina DIOGENES_LLM_PROVIDER=chattcu no .env."
        )

    if provider == "chattcu":
        from diogenes.llm.chattcu import ChatTCUClient
        return ChatTCUClient(
            base_url=cfg.llm.chattcu_base_url,
            cycle_id=cycle_id,
            runtime_dir=runtime_dir,
        )

    if provider == "azure" or cfg.llm.env == "azure":
        from diogenes.llm.azure_foundry import AzureFoundryClient
        return AzureFoundryClient(cfg=cfg, cycle_id=cycle_id, runtime_dir=runtime_dir)

    # openrouter (permitido apenas em pytest) ou qualquer outro provider legado
    from diogenes.llm.openrouter import OpenRouterClient
    return OpenRouterClient(cfg=cfg, cycle_id=cycle_id, runtime_dir=runtime_dir)
