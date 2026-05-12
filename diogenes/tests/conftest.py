"""
tests/conftest.py — DVA-CBS | Projeto Diógenes
Fixtures compartilhadas conforme SDD Bloco 13.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from diogenes.config import get_config


@pytest.fixture(autouse=True)
def clear_config_cache():
    """Limpa o cache de configuração antes de cada teste."""
    get_config.cache_clear()
    yield
    get_config.cache_clear()


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    ws = tmp_path / "workspace"
    (ws / "input").mkdir(parents=True)
    (ws / "cycles").mkdir(parents=True)
    return ws


@pytest.fixture
def module_input(workspace: Path) -> Path:
    """Cria MOD_SINT_001 com estrutura realista para testes."""
    mod = workspace / "input" / "MOD_SINT_001"
    mod.mkdir()
    (mod / "descricao_metodologica.md").write_text(
        "# Metodologia MOD_SINT_001\nDescrição do método de cálculo CBS.", encoding="utf-8"
    )
    (mod / "planilha_cbs.xlsx").write_bytes(b"PK\x03\x04fake-xlsx-0001")
    (mod / "script_extracao.sql").write_text(
        "SELECT * FROM arrecadacao WHERE modulo = 'SINT_001';", encoding="utf-8"
    )
    atas = mod / "atas"
    atas.mkdir()
    (atas / "ata_reuniao_entrega.md").write_text(
        "# Ata de Reunião\nData: 10/05/2026", encoding="utf-8"
    )
    return mod


@pytest.fixture
def env_vars(workspace: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Define variáveis de ambiente mínimas para get_config() funcionar."""
    monkeypatch.setenv("DIOGENES_LLM_API_KEY", "test-key")
    monkeypatch.setenv("DIOGENES_LLM_BASE_URL", "https://openrouter.ai/api/v1")
    monkeypatch.setenv("DIOGENES_WORKSPACE", str(workspace))
    monkeypatch.setenv("DIOGENES_ENV", "local")
