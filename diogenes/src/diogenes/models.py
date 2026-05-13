"""
models.py — DVA-CBS | Projeto Diógenes
Dataclasses e modelos Pydantic de domínio do sistema.

Não contém lógica de negócio — apenas estruturas de dados com validação.
Referência normativa: Bloco 2.3.2, Bloco 6.3, Bloco 9 (SDD v0.1)
"""
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, ConfigDict


# ---------------------------------------------------------------------------
# AgentSpec — especificação de um agente lida de agents_spec.yaml
# ---------------------------------------------------------------------------
class AgentSpec(BaseModel):
    model_config = ConfigDict(frozen=True)
    modelo: str
    temperatura: float
    max_tokens: int
    max_tokens_ciclo: int
    timeout_segundos: int
    max_tentativas_retry: int
    backoff_segundos: int


# ---------------------------------------------------------------------------
# LLM — camada de comunicação com modelos
# ---------------------------------------------------------------------------
class LLMMessage(BaseModel):
    model_config = ConfigDict(frozen=True)
    role: str       # "system" | "user" | "assistant"
    content: str


class LLMCall(BaseModel):
    model_config = ConfigDict(frozen=True)
    # Identificação
    call_id: str        # {timestamp_utc}_{agente}_{tipo}
    cycle_id: str
    phase: str          # watson_integridade | sherlock_validacao | consolidacao
    agent: str          # mycroft | watson | sherlock
    call_type: str      # analise_inicial | resposta_r1 | ...
    # Parâmetros do modelo
    model: str
    temperature: float
    max_tokens: int
    seed: int
    # Conteúdo
    messages: list[LLMMessage]
    # Política de retry
    timeout_segundos: int
    max_tentativas_retry: int
    backoff_segundos: int


class LLMResponse(BaseModel):
    model_config = ConfigDict(frozen=True)
    content: str
    call_id: str
    model_used: str
    system_fingerprint: Optional[str]
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost_usd: float
    latency_ms: int
    retry_attempts: int
    http_status: int


# ---------------------------------------------------------------------------
# Outputs de agentes e decisões
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class WatsonOutput:
    texto: str
    critical_alerts_count: int
    has_unanalyzable_files: bool
    secoes: dict
    ultimo_id_alerta: str = ""   # ex: "W010-003" — propagado entre chamadas per-file


@dataclass(frozen=True)
class AvaliacaoMycroft:
    tipo: str           # "APROVADO" | "QUESTIONAR"
    texto: str          # texto completo produzido por Mycroft
    critica: str = ""   # pontos para revisão (quando QUESTIONAR)


@dataclass(frozen=True)
class DecisaoFinal:
    texto: str
    mycroft_overruled: bool
    has_critical_alert: bool
    critical_alerts_count: int
    has_dilemma: bool
    dilemmas_count: int


# ---------------------------------------------------------------------------
# CycleManifest
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class InputFileInfo:
    name: str
    extension: str
    size_bytes: int
    sha256: str
    rel_path: Path


@dataclass
class CycleManifest:
    cycle_id: str
    module_id: str
    activity: int
    opened_at_utc: str
    is_sigilo_module: bool
    input_files: list[InputFileInfo]
    package_hash: str
    git_commit: str
    diogenes_version: str
    python_version: str
    openai_version: str
    cycle_num: int
    previous_cycle_id: str = ""
    confirmed_at_utc: str = ""
    prioridades_analise: str = ""
    alertas_lestrade: str = ""


# ---------------------------------------------------------------------------
# CycleRecord — linha do audit_index.csv (SDD Bloco 5.5)
# ---------------------------------------------------------------------------
@dataclass
class CycleRecord:
    cycle_id: str
    module_id: str
    activity: int
    status: str
    opened_at_utc: str
    ended_at_utc: str = ""
    is_sigilo_module: str = "false"
    previous_cycle_id: str = ""
    watson_rodadas: str = "0"
    sherlock_rodadas: str = "0"
    mycroft_overruled_watson: str = "false"
    mycroft_overruled_sherlock: str = "false"
    watson_critical_alerts_count: str = "0"
    sherlock_dilemmas_count: str = "0"
    motor_saida_invocado_at_utc: str = ""
    motor_saida_occurrences: str = ""
    motor_saida_decision: str = ""
    lestrade_seal_at_utc: str = ""
    output_filename: str = ""
    output_hash: str = ""
    custo_total_usd: str = "0.00"
    tokens_mycroft: str = "0"
    tokens_watson: str = "0"
    tokens_sherlock: str = "0"
    ambiente: str = "local"
    diogenes_version: str = ""
    git_commit: str = ""


AUDIT_INDEX_COLUMNS: list[str] = [
    "cycle_id", "module_id", "activity", "status",
    "opened_at_utc", "ended_at_utc",
    "is_sigilo_module", "previous_cycle_id",
    "watson_rodadas", "sherlock_rodadas",
    "mycroft_overruled_watson", "mycroft_overruled_sherlock",
    "watson_critical_alerts_count", "sherlock_dilemmas_count",
    "motor_saida_invocado_at_utc", "motor_saida_occurrences", "motor_saida_decision",
    "lestrade_seal_at_utc", "output_filename", "output_hash",
    "custo_total_usd", "tokens_mycroft", "tokens_watson", "tokens_sherlock",
    "ambiente", "diogenes_version", "git_commit",
]


# ---------------------------------------------------------------------------
# Outputs específicos de Sherlock e Mycroft
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class SherlockOutput:
    texto: str
    dilemmas_count: int
    has_divergencias: bool
    secoes: dict


@dataclass(frozen=True)
class RelatorioOutput:
    """Output final de Mycroft.consolidar() — corpo do relatório preliminar/final."""
    texto: str


# ---------------------------------------------------------------------------
# StrangerRoomFile
# ---------------------------------------------------------------------------
class StrangerRoomFile(BaseModel):
    model_config = ConfigDict(frozen=True)
    cycle_id: str
    phase: str
    file_type: str
    author: str
    role: str
    round: Optional[int]
    timestamp_utc: str
    content_hash: str
    has_critical_alert: Optional[bool] = None
    has_dilemma: Optional[bool] = None
    mycroft_overruled: Optional[bool] = None
    content: str = ""


# ---------------------------------------------------------------------------
# MotorSaida
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class OcorrenciaDetectada:
    linha: int
    categoria: str
    padrao_detectado: str
    contexto: str
    posicao_documento: str
    classificacao_automatica: Optional[str]


@dataclass
class MotorSaidaReport:
    cycle_id: str
    doc_path: Path
    doc_hash: str
    ocorrencias: list[OcorrenciaDetectada]
    verificado_em_utc: str
    total_ocorrencias: int
    documento_limpo: bool
