"""
models.py — DVA-CBS | Projeto Diógenes
Dataclasses e modelos Pydantic de domínio do sistema.

Não contém lógica de negócio — apenas estruturas de dados com validação.
Referência normativa: Bloco 2.3.2, Bloco 6.3, Bloco 9 (SDD v0.1)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

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
    raciocinio: bool = True
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
    system_fingerprint: str | None
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost_usd: float
    latency_ms: int
    retry_attempts: int
    http_status: int
    finish_reason: str = ""   # "stop" | "length" | ... — "length" sinaliza truncagem


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
    # cabeçalho watson_consolidado.md — lido pelo orquestrador para acionar Sherlock com prioridade
    nota_metodologica_com_alteracao: bool = False


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
    categoria: str = "analisavel"   # analisavel | metadados (file_prep.classificar)
    tipo: str = ""                  # rótulo legível: csv, sql, notebook, ...


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
    delivery_manifest_status: str = "AUSENTE"   # AUSENTE | PRESENTE_OK | PRESENTE_COM_DIVERGENCIA
    delivery_reconciliation: str = ""           # texto markdown pronto para o render


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
    # Irene — rastreamento da fase de catalogação (INTEGRACAO_DIOGENES.md seção 5)
    irene_invocada_at_utc: str = ""
    irene_resultado: str = ""   # IRENE_APROVADO | IRENE_ALERTA | IRENE_BLOQUEADO | IRENE_ERRO_FATAL
    irene_score: str = ""       # score_consolidado como string (ex: "0.9737")
    irene_dir_saida: str = ""   # caminho absoluto do IRENE_OUT/{modulo}
    # Fase de Entrega — rastreamento da geração dos entregáveis
    entrega_invocado_at_utc: str = ""
    entrega_artefatos: str = ""   # nº de artefatos gerados com sucesso
    entrega_veredito: str = ""    # APROVADO | REQUER_AJUSTE (QA de Mycroft)


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
    "irene_invocada_at_utc", "irene_resultado", "irene_score", "irene_dir_saida",
    "entrega_invocado_at_utc", "entrega_artefatos", "entrega_veredito",
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
    # campos do cabeçalho dos templates de Sherlock — extraídos pelo parser
    nota_metodologica_com_alteracao: bool = False  # sherlock_ponto_*.md: campo "verificada neste ponto"
    notas_metodologicas_count: int = 0             # sherlock_consolidado.md seção 7
    pendencias_simulador_count: int = 0            # sherlock_consolidado.md seção 9


@dataclass(frozen=True)
class RelatorioOutput:
    """Output final de Mycroft.consolidar() — corpo do relatório preliminar/final."""
    texto: str
    # campos de rastreabilidade extraídos do MC_consolidado.md
    overrule_watson: bool = False
    overrule_sherlock: bool = False


@dataclass(frozen=True)
class DefinirTasksResult:
    """Resultado de Mycroft.definir_tasks_watson() — separa tasks do flag de planilha."""
    tasks_text: str
    # flag lido do cabeçalho MC_tasks_watson.md — controla call_types condicionais
    planilha_verificacao_no_pacote: bool = False


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
    round: int | None
    timestamp_utc: str
    content_hash: str
    has_critical_alert: bool | None = None
    has_dilemma: bool | None = None
    mycroft_overruled: bool | None = None
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
    classificacao_automatica: str | None


@dataclass
class MotorSaidaReport:
    cycle_id: str
    doc_path: Path
    doc_hash: str
    ocorrencias: list[OcorrenciaDetectada]
    verificado_em_utc: str
    total_ocorrencias: int
    documento_limpo: bool


# ---------------------------------------------------------------------------
# Fase de Entrega — esquema canônico do PacoteEntrega (módulo-agnóstico)
#
# Alimenta os geradores vendorizados (TCUFormatter / ApendiceGerador /
# DashboardGenerator / ficha síntese). Mapeia 1:1 no dicionário de dados do
# ApendiceGerador (ver delivery/vendor/tcu — README das bibliotecas) e no
# template genérico do dashboard. Sem lógica, sem imports internos.
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class KPIEntrega:
    """Cartão de indicador no dashboard / ficha síntese."""
    rotulo: str
    valor: str
    nota: str = ""
    destaque: str = ""   # "" | "red" | "green" | "amber" | "navy"
    unidade: str = ""    # rótulo curto sob o valor, ex.: "R$ bi", "mil CPFs"
    delta: str = ""      # variação formatada, ex.: "+5,2%" (calculada pelo extractor)
    delta_tipo: str = "" # "" | "up" | "down" | "neutral" — cor/seta do delta


@dataclass(frozen=True)
class TabelaEntrega:
    titulo: str
    headers: list[str]
    rows: list[list[str]]
    fonte: str = ""
    # Textos da primeira coluna que devem ser realçados como total-row (case-insensitive).
    total_labels: list[str] = field(default_factory=list)
    subtitulo: str = ""


@dataclass(frozen=True)
class GraficoEntrega:
    tipo: str             # "barras" | "rosca" | "linha" | "barras_horizontais"
    titulo: str
    labels: list[str]
    series: list[float]
    nota: str = ""
    subtitulo: str = ""   # linha de apoio sob o título do gráfico
    layout: str = "grid"  # "grid" (meia-largura, par a par) | "full" (largura total)


@dataclass(frozen=True)
class MetodologiaCard:
    """Card explicativo do que foi homologado (consome o texto da Metodologia)."""
    tag: str              # ex.: "Seção 10.1 — Produtor Rural"
    titulo: str
    corpo: str
    chips: list[str] = field(default_factory=list)   # ex.: ["DIRPF", "Arts. 164/165"]


@dataclass(frozen=True)
class CenarioSensibilidade:
    """Cartão de cenário na aba de Sensibilidade (base vs. ajustado)."""
    rotulo: str
    valor: str
    nota: str = ""
    destaque: str = ""    # "" | "red" | "green" | "amber" | "navy"


@dataclass
class BlocoFinanceiro:
    """Aba/seção financeira genérica do dashboard (acomoda 18 layouts distintos)."""
    id: str
    titulo: str
    descricao: str = ""
    # "visao_geral" | "analitica" | "sensibilidade" — dirige o render no dashboard.
    tipo: str = "analitica"
    narrativa: str = ""   # parágrafo analítico curado por Mycroft (texto, sem números)
    kpis: list[KPIEntrega] = field(default_factory=list)
    cards_metodologia: list[MetodologiaCard] = field(default_factory=list)
    tabelas: list[TabelaEntrega] = field(default_factory=list)
    graficos: list[GraficoEntrega] = field(default_factory=list)
    cenarios: list[CenarioSensibilidade] = field(default_factory=list)


@dataclass(frozen=True)
class OcorrenciaEntrega:
    """Ocorrência do insumo_json_dashboard de Sherlock (skills.md §11)."""
    codigo: str
    titulo: str
    nivel: str            # CRITICO | ALERTA | ATENCAO | RESOLVIDO
    fundamento_violado: str = ""
    descricao: str = ""
    solicitacao_rfb: str = ""
    status: str = "aberto"             # aberto | encaminhado | resolvido
    status_resolucao: str | None = None


@dataclass(frozen=True)
class PendenciaSimulador:
    codigo: str
    descricao: str
    verificacao_futura: str = ""


@dataclass(frozen=True)
class TesteRealizado:
    id: str
    descricao: str
    resultado: str
    status: str           # Atendido | Atendido Parcialmente | Divergência | ...


@dataclass(frozen=True)
class NotaMetodologica:
    nome: str
    data: str = ""
    descricao: str = ""
    conteudo_resumo: str = ""
    situacao_inventario: str = ""
    observacao: str = ""


@dataclass
class PacoteEntrega:
    cycle_id: str
    modulo: int
    modulo_nome: str
    versao: str = ""
    timestamp_utc: str = ""
    # Identificação institucional (defaults do TC 015.848/2025-6)
    processo: str = "TC 015.848/2025-6"
    acordao: str = "2833/2025-Plenário"
    relator: str = "Ministro Vital do Rêgo"
    unidade: str = "SecexContas / TCU"
    # Apêndice — seções 1 e 2
    proposta_descricao: str = ""
    proposta_contexto: str = ""
    proposta_fonte: str = ""
    objetivo: str = ""
    objetivo_detalhado: str = ""
    # Apêndice — seção 3 (arquivos): cada item é dict {nome, descricao, tamanho|tipo}
    arquivos_principal: list[dict] = field(default_factory=list)
    arquivos_auxiliares: list[dict] = field(default_factory=list)
    arquivos_fontes: list[dict] = field(default_factory=list)
    # Camada financeira (genérica) — extraída deterministicamente da planilha
    blocos_financeiros: list[BlocoFinanceiro] = field(default_factory=list)
    valores_agregados: list[dict] = field(default_factory=list)   # {descricao, valor_2023, valor_2024}
    sensibilidade_redutor: dict | None = None                     # {redutores:[int], valores:[float]}
    # Camada de auditoria (Sherlock + Watson + Mycroft)
    ocorrencias: list[OcorrenciaEntrega] = field(default_factory=list)
    pendencias_simulador: list[PendenciaSimulador] = field(default_factory=list)
    testes_camada_1: list[TesteRealizado] = field(default_factory=list)
    testes_camada_2: list[TesteRealizado] = field(default_factory=list)
    testes_camada_3: list[TesteRealizado] = field(default_factory=list)
    notas_metodologicas: list[NotaMetodologica] = field(default_factory=list)
    veredito: str = ""                # APROVADO | APROVADO_COM_RESSALVAS | ...
    conclusao_conformidade: str = ""
    conclusao_consistencia: str = ""
    # Narrativa — markdown consolidado (higienizado) e ata RFB opcional
    relatorio_markdown: str = ""
    ata_rfb_markdown: str = ""
    # Conteúdo qualitativo do Apêndice redigido por Mycroft (call_type redigir_apendice).
    # Mescla-se com a camada numérica determinística em builders.dados_apendice.
    apendice_conteudo: dict | None = None


@dataclass(frozen=True)
class ArtefatoEntrega:
    """Um artefato gerado pela Fase de Entrega."""
    tipo: str             # dashboard | apendice | narrativo | consolidado | pre_atendimento | ficha
    nome: str
    path: Path
    hash: str
    bytes: int
    ok: bool
    nota: str = ""


@dataclass
class MotorEntregaReport:
    cycle_id: str
    gerado_em_utc: str
    artefatos: list[ArtefatoEntrega]
    total_artefatos: int
    entrega_dir: Path
    avisos: list[str] = field(default_factory=list)
