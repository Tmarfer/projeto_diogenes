"""
config.py — DVA-CBS | Projeto Diógenes
Ponto único de leitura de toda configuração do sistema.

Todos os demais módulos importam de config.py — nunca de os.environ
ou dos arquivos YAML diretamente (SDD Bloco 2.3.1).

O decorator @lru_cache garante que a configuração é lida uma única vez
por processo. Em testes, usar get_config.cache_clear() antes de cada
teste que precise de configuração diferente.

Referência normativa: RNF-PORT-04 (PRD v0.1), Bloco 4.5 (SDD v0.1)
"""

from __future__ import annotations

import os
import sys
from functools import lru_cache
from pathlib import Path

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, field_validator

from diogenes.models import AgentSpec


# ---------------------------------------------------------------------------
# Modelos de configuração
# ---------------------------------------------------------------------------

class LLMConfig(BaseModel):
    api_key: str
    base_url: str
    env: str = "local"
    openrouter_site_url: str = ""
    openrouter_app_name: str = ""
    ssl_verify: bool = True  # False em redes com proxy de inspeção SSL (TCU)


class WorkspaceConfig(BaseModel):
    path: Path
    max_path_depth: int = 8

    @field_validator("path", mode="before")
    @classmethod
    def resolve_path(cls, v: object) -> Path:
        return Path(str(v)).resolve()


class CicloConfig(BaseModel):
    max_rodadas_revisao: int = 2
    stranger_room_prefixos: dict[str, str]
    estados: list[str]


class MotorSaidaConfig(BaseModel):
    padroes_agentes: list[str]
    padroes_cargo_identificador: list[str]
    padroes_estruturas_internas: list[str]
    regex_cycle_id: str


class PersistenciaConfig(BaseModel):
    audit_index_filename: str = "audit_index.csv"
    encoding: str = "utf-8"
    timestamp_format: str = "%Y%m%dT%H%M%SZ"
    timestamp_iso_format: str = "%Y-%m-%dT%H:%M:%SZ"


class ObservabilidadeConfig(BaseModel):
    log_level: str = "INFO"
    mostrar_progresso_llm: bool = True
    progresso_intervalo_segundos: int = 60


class AgentesConfig(BaseModel):
    mycroft: AgentSpec
    watson: AgentSpec
    sherlock: AgentSpec
    teto_custo_ciclo_usd: float
    seed_base: int
    fase_ativa: str = "A"


class DiogenesConfig(BaseModel):
    llm: LLMConfig
    workspace: WorkspaceConfig
    ciclo: CicloConfig
    motor_saida: MotorSaidaConfig
    persistencia: PersistenciaConfig
    observabilidade: ObservabilidadeConfig
    agentes: AgentesConfig


# ---------------------------------------------------------------------------
# Exceção de configuração
# ---------------------------------------------------------------------------

class ConfigError(Exception):
    """Erro de configuração — variável ausente, valor inválido, arquivo não encontrado."""


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------

def _require_env(name: str) -> str:
    """Retorna o valor da variável de ambiente ou levanta ConfigError."""
    value = os.environ.get(name, "").strip()
    if not value:
        raise ConfigError(
            f"Variável de ambiente obrigatória '{name}' não encontrada. "
            f"Verifique o arquivo .env."
        )
    return value


def _load_yaml(filename: str) -> dict:
    """Carrega um arquivo YAML da raiz do projeto (diretório de trabalho)."""
    path = Path(filename)
    if not path.exists():
        raise ConfigError(
            f"Arquivo '{filename}' não encontrado em '{Path.cwd()}'. "
            f"Execute o comando a partir da raiz do repositório."
        )
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data or {}


def _get_package_version(pkg: str) -> str:
    try:
        import importlib.metadata
        return importlib.metadata.version(pkg)
    except Exception:
        return "desconhecida"


# ---------------------------------------------------------------------------
# get_config — ponto de entrada público
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def get_config() -> DiogenesConfig:
    """
    Lê e valida toda a configuração do sistema.
    Chamado uma única vez por processo — resultado cacheado via lru_cache.
    Levanta ConfigError com mensagem clara se qualquer campo obrigatório
    estiver ausente ou inválido.
    """
    load_dotenv()  # carrega .env; não sobrescreve vars já no ambiente

    runtime = _load_yaml("runtime.yaml")
    agents_raw = _load_yaml("agents_spec.yaml")

    # DIOGENES_WORKSPACE sobrescreve runtime.yaml::workspace.path
    workspace_path = os.environ.get(
        "DIOGENES_WORKSPACE",
        runtime.get("workspace", {}).get("path", "./workspace"),
    )

    ciclo_cfg = CicloConfig(**runtime["ciclo"])

    # Aviso constitucional se max_rodadas_revisao divergir de 2
    if ciclo_cfg.max_rodadas_revisao != 2:
        import warnings
        warnings.warn(
            f"max_rodadas_revisao está definido como {ciclo_cfg.max_rodadas_revisao}. "
            f"O valor constitucional é 2 (Artigo 8). "
            f"Certifique-se de que essa alteração é intencional.",
            stacklevel=2,
        )

    return DiogenesConfig(
        llm=LLMConfig(
            api_key=_require_env("DIOGENES_LLM_API_KEY"),
            base_url=_require_env("DIOGENES_LLM_BASE_URL"),
            env=os.environ.get("DIOGENES_ENV", "local"),
            openrouter_site_url=os.environ.get("DIOGENES_OPENROUTER_SITE_URL", ""),
            openrouter_app_name=os.environ.get("DIOGENES_OPENROUTER_APP_NAME", ""),
            ssl_verify=os.environ.get("DIOGENES_SSL_VERIFY", "true").lower() not in ("false", "0"),
        ),
        workspace=WorkspaceConfig(
            path=workspace_path,
            max_path_depth=runtime.get("workspace", {}).get("max_path_depth", 8),
        ),
        ciclo=ciclo_cfg,
        motor_saida=MotorSaidaConfig(**runtime["motor_saida"]),
        persistencia=PersistenciaConfig(**runtime["persistencia"]),
        observabilidade=ObservabilidadeConfig(**runtime["observabilidade"]),
        agentes=AgentesConfig(
            mycroft=AgentSpec(**agents_raw["agentes"]["mycroft"]),
            watson=AgentSpec(**agents_raw["agentes"]["watson"]),
            sherlock=AgentSpec(**agents_raw["agentes"]["sherlock"]),
            teto_custo_ciclo_usd=agents_raw["teto_custo_ciclo_usd"],
            seed_base=agents_raw["seed_base"],
            fase_ativa=agents_raw.get("fase_ativa", "A"),
        ),
    )
