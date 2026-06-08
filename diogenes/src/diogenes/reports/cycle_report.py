"""
reports/cycle_report.py — DVA-CBS | Projeto Diógenes
Agrega artefatos do ciclo em CycleReportData para renderização local.
Todas as funções são best-effort: exceções são suprimidas silenciosamente.
"""
from __future__ import annotations

import contextlib
import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from diogenes.persistence.audit_index import AuditIndex

# ── Tabela de preços de referência (USD por 1M tokens) ───────────────────────
# Espelha src/diogenes/llm/chattcu.py::_PRECOS. O ChatTCU é institucional e não
# cobra (cost_usd=0.0 nos logs), então o custo exibido no painel é uma ESTIMATIVA
# de referência de mercado — o que o ciclo custaria via API paga ao preço público.
# Mantido local para não acoplar reports/ a llm/ (e suas deps msal/requests).
_PRECOS_REF: dict[str, tuple[float, float]] = {
    "Claude 4.6 Sonnet":      (3.00, 15.00),
    "claude-4-8-opus":        (5.00, 25.00),
    "claude-4-7-opus":        (5.00, 25.00),
    "claude-4-6-opus":        (5.00, 25.00),
    "gpt-5.5-thinking":       (5.00, 30.00),
    "gpt-5.4-thinking":       (2.50, 15.00),
    "gpt-5.3-instant":        (0.75,  4.50),
    "gpt-5.2-thinking":       (1.75, 14.00),
    "gpt-5.2-instant":        (0.75,  4.50),
    "GPT-4.1":                (2.00,  8.00),
    "GPT-4o":                 (2.50, 10.00),
    "o1":                    (15.00, 60.00),
    "o3":                    (10.00, 40.00),
    "o4-mini":                (1.10,  4.40),
    "gemini-3.1-pro-preview": (2.00, 12.00),
    "gemini-3.1-flash-lite":  (0.10,  0.40),
    "gemini-3-flash":         (0.50,  3.00),
    "DeepSeek R1":            (0.55,  2.19),
}


def _custo_ref_call(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    """Custo de referência (USD) de uma chamada, ao preço de mercado do modelo."""
    preco_in, preco_out = _PRECOS_REF.get(model, (0.0, 0.0))
    return (prompt_tokens * preco_in + completion_tokens * preco_out) / 1_000_000


# ── Modelos ──────────────────────────────────────────────────────────────────

@dataclass
class AgentCallStats:
    calls: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_response_length: int = 0
    estimated_cost_usd: float = 0.0

    @property
    def avg_response_length(self) -> float:
        return self.total_response_length / self.calls if self.calls else 0.0

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


@dataclass
class FaseEntry:
    fase: str
    started_at: str
    ended_at: str = ""
    duration_min: float = 0.0


@dataclass
class CycleReportData:
    # Identidade
    cycle_id: str
    module_id: str
    activity: int
    status: str
    opened_at_utc: str
    ended_at_utc: str
    duration_str: str
    git_commit: str
    diogenes_version: str

    # Irene
    irene_resultado: str
    irene_score: float | None
    irene_invocada_at: str

    # Watson
    arquivos_analisados: int
    watson_critical_alerts: int
    watson_rodadas: int
    watson_overruled: bool

    # Sherlock
    metodologia_chars: int
    corpus_juridico_chars: int
    sherlock_dilemmas: int
    sherlock_rodadas: int
    sherlock_overruled: bool

    # LLM
    total_calls: int
    calls_by_agent: dict[str, AgentCallStats]

    # Motor de Saída
    motor_saida_occurrences: int
    motor_saida_decision: str
    motor_saida_limpo: bool

    # Timeline
    fases: list[FaseEntry]
    key_events: list[dict]

    # Stranger Room — {fase: [{nome, path}]}
    stranger_room_files: dict[str, list[dict]]

    # Output
    output_filename: str
    output_hash: str
    output_path: Path | None

    # Controle de live mode
    is_terminal: bool

    generated_at: str = field(default_factory=lambda: datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"))

    # Fase de Entrega (defaults — backward-compatible)
    entrega_artefatos: int = 0
    entrega_invocado_at: str = ""
    entrega_veredito: str = ""
    entrega_artefatos_list: list[dict] = field(default_factory=list)   # {nome, path, bytes, tipo}
    entrega_calls_by_type: dict[str, int] = field(default_factory=dict)

    # Motor de Perfilamento (defaults — backward-compatible)
    perfil_arquivos_total: int = 0
    perfil_alertas_criticos: int = 0
    perfil_colunas_compartilhadas: int = 0
    perfil_arquivos_com_erro: int = 0
    perfil_executado: bool = False

    # Pacote de inputs
    package_hash: str = ""
    n_arquivos_total: int = 0
    n_arquivos_analisavel: int = 0

    # Watson — detalhe por arquivo
    watson_arquivos_detail: list[dict] = field(default_factory=list)  # {nome, timestamp_utc}


_TERMINAL_STATES = frozenset({
    "ENCERRADO_CHANCELADO",
    "ABORTADO_FALHA_AGENTE",
    "ABORTADO_LESTRADE",
})

_KEY_EVENT_TYPES = frozenset({
    "CYCLE_STARTED",
    "PHASE_STARTED",
    "PHASE_ENDED",
    "SHERLOCK_REGUA_CARREGADA",
    "SHERLOCK_CONSOLIDADO",
    "CRITICAL_ALERT_NOTIFIED",
    "LESTRADE_PROCEED_AUTHORIZED",
    "MYCROFT_APPROVED",
    "MYCROFT_DECISION_FINAL",
    "CONSOLIDACAO_CONCLUIDA",
    "CYCLE_READY_FOR_MOTOR_SAIDA",
    "IRENE_CATALOGO_REUTILIZADO",
    "TASKS_WATSON_CACHE_HIT",
    "REVALIDACAO_HISTORICO_INJETADO",
    "IRENE_VERIFICACAO_INICIO",
})


# ── API pública ───────────────────────────────────────────────────────────────

def build_report(cycle_id: str, workspace: Path) -> CycleReportData:
    """Constrói CycleReportData a partir dos artefatos em disco."""
    cycle_dir = workspace / "cycles" / cycle_id
    runtime_dir = cycle_dir / "_runtime"

    record = _ler_audit_record(workspace, cycle_id)
    events = _ler_events(runtime_dir)
    calls = _ler_llm_calls(runtime_dir)

    status = record.get("status", "")
    is_terminal = status in _TERMINAL_STATES

    opened = record.get("opened_at_utc", "")
    ended = record.get("ended_at_utc", "")

    irene_score_raw = record.get("irene_score", "")
    try:
        irene_score: float | None = float(irene_score_raw) if irene_score_raw else None
    except (ValueError, TypeError):
        irene_score = None

    irene_resultado = record.get("irene_resultado", "")
    # Quando o catálogo foi reutilizado, o audit_index fica sem irene_resultado.
    # Enriquecer a partir dos eventos.
    if not irene_resultado:
        for e in events:
            et = e.get("event_type", "")
            if et == "IRENE_CATALOGO_REUTILIZADO":
                irene_resultado = "CATALOGO_REUTILIZADO"
                break
            if et == "IRENE_CONCLUIDA_REGISTRADA":
                irene_resultado = "IRENE_CONCLUIDA"
                break

    arquivos_analisados = sum(1 for e in events if e.get("event_type") == "WATSON_ARQUIVO_ANALISADO")
    watson_critical_alerts = _safe_int(record.get("watson_critical_alerts_count", 0))
    watson_rodadas = _safe_int(record.get("watson_rodadas", 0))
    watson_overruled = str(record.get("mycroft_overruled_watson", "")).lower() == "true"

    metodologia_chars = 0
    corpus_juridico_chars = 0
    for e in events:
        if e.get("event_type") == "SHERLOCK_REGUA_CARREGADA":
            d = e.get("details", {})
            metodologia_chars = _safe_int(d.get("metodologia_chars", 0))
            corpus_juridico_chars = _safe_int(d.get("corpus_juridico_chars", 0))
            break

    sherlock_dilemmas = _safe_int(record.get("sherlock_dilemmas_count", 0))
    sherlock_rodadas = _safe_int(record.get("sherlock_rodadas", 0))
    sherlock_overruled = str(record.get("mycroft_overruled_sherlock", "")).lower() == "true"

    motor_occurrences = _safe_int(record.get("motor_saida_occurrences", 0))
    motor_decision = record.get("motor_saida_decision", "")
    motor_limpo = motor_decision in ("LIMPO", "ACEITO_JUSTIFICADO")

    output_filename = record.get("output_filename", "")
    output_hash = record.get("output_hash", "")
    output_path: Path | None = None
    if output_filename:
        candidate = cycle_dir / "output" / output_filename
        if candidate.exists():
            output_path = candidate

    return CycleReportData(
        cycle_id=cycle_id,
        module_id=record.get("module_id", ""),
        activity=_safe_int(record.get("activity", 0)),
        status=status,
        opened_at_utc=opened,
        ended_at_utc=ended,
        duration_str=_calcular_duracao(opened, ended),
        git_commit=(record.get("git_commit", "") or "")[:12],
        diogenes_version=record.get("diogenes_version", ""),
        irene_resultado=irene_resultado,
        irene_score=irene_score,
        irene_invocada_at=record.get("irene_invocada_at_utc", ""),
        arquivos_analisados=arquivos_analisados,
        watson_critical_alerts=watson_critical_alerts,
        watson_rodadas=watson_rodadas,
        watson_overruled=watson_overruled,
        metodologia_chars=metodologia_chars,
        corpus_juridico_chars=corpus_juridico_chars,
        sherlock_dilemmas=sherlock_dilemmas,
        sherlock_rodadas=sherlock_rodadas,
        sherlock_overruled=sherlock_overruled,
        total_calls=len(calls),
        calls_by_agent=_agregar_llm_por_agente(calls),
        motor_saida_occurrences=motor_occurrences,
        motor_saida_decision=motor_decision,
        motor_saida_limpo=motor_limpo,
        fases=_timeline_fases(events),
        key_events=_key_events(events),
        stranger_room_files=_listar_stranger_room(cycle_dir),
        output_filename=output_filename,
        output_hash=output_hash,
        output_path=output_path,
        is_terminal=is_terminal,
        entrega_artefatos=_safe_int(record.get("entrega_artefatos", 0)),
        entrega_invocado_at=record.get("entrega_invocado_at_utc", ""),
        entrega_veredito=record.get("entrega_veredito", ""),
        entrega_artefatos_list=_listar_entrega(cycle_dir),
        entrega_calls_by_type=_calls_entrega_por_tipo(calls),
        **_perfilamento_stats(runtime_dir, events),
        **_manifest_info(cycle_dir),
        watson_arquivos_detail=_watson_arquivos_detail(events),
    )


# ── Helpers (testáveis e reutilizáveis) ───────────────────────────────────────

def _ler_audit_record(workspace: Path, cycle_id: str) -> dict:
    try:
        return AuditIndex(workspace).get_cycle(cycle_id) or {}
    except Exception:  # noqa: BLE001
        return {}


def _ler_events(runtime_dir: Path) -> list[dict]:
    path = runtime_dir / "events.jsonl"
    if not path.exists():
        return []
    lines = []
    try:
        for raw in path.read_text(encoding="utf-8").splitlines():
            raw = raw.strip()
            if raw:
                with contextlib.suppress(json.JSONDecodeError):
                    lines.append(json.loads(raw))
    except OSError:
        pass
    return lines


def _ler_llm_calls(runtime_dir: Path) -> list[dict]:
    path = runtime_dir / "llm_calls.jsonl"
    if not path.exists():
        return []
    lines = []
    try:
        for raw in path.read_text(encoding="utf-8").splitlines():
            raw = raw.strip()
            if raw:
                with contextlib.suppress(json.JSONDecodeError):
                    lines.append(json.loads(raw))
    except OSError:
        pass
    return lines


def _agregar_llm_por_agente(calls: list[dict]) -> dict[str, AgentCallStats]:
    stats: dict[str, AgentCallStats] = {}
    for c in calls:
        agent = c.get("agent") or "desconhecido"
        if agent not in stats:
            stats[agent] = AgentCallStats()
        s = stats[agent]
        pt = _safe_int(c.get("prompt_tokens", 0))
        ct = _safe_int(c.get("completion_tokens", 0))
        s.calls += 1
        s.prompt_tokens += pt
        s.completion_tokens += ct
        s.total_response_length += _safe_int(c.get("response_length", 0))
        s.estimated_cost_usd += _custo_ref_call(str(c.get("model", "")), pt, ct)
    return stats


def _timeline_fases(events: list[dict]) -> list[FaseEntry]:
    fases: dict[str, FaseEntry] = {}
    for e in events:
        et = e.get("event_type", "")
        phase = e.get("phase") or ""
        ts = e.get("timestamp_utc", "")
        if not phase:
            continue
        if et == "PHASE_STARTED":
            fases[phase] = FaseEntry(fase=phase, started_at=ts)
        elif et == "PHASE_ENDED" and phase in fases:
            fases[phase].ended_at = ts
            dur = _diff_minutos(fases[phase].started_at, ts)
            if dur is not None:
                fases[phase].duration_min = dur
    return list(fases.values())


def _key_events(events: list[dict]) -> list[dict]:
    return [e for e in events if e.get("event_type") in _KEY_EVENT_TYPES]


_ENTREGA_CALL_TYPES = ("mapear_dados_modulo", "redigir_apendice", "avaliar_entrega")

_ENTREGA_TIPO_POR_PADRAO = (
    ("Dashboard", "dashboard"),
    ("Apendice", "apêndice"),
    ("Relatorio_Narrativo", "relatório narrativo"),
    ("Relatorio_Consolidado", "relatório consolidado"),
    ("Pre_Atendimento", "pré-atendimento"),
    ("ficha_sintese", "ficha síntese"),
)


def _classificar_entrega(nome: str) -> str:
    for prefixo, tipo in _ENTREGA_TIPO_POR_PADRAO:
        if prefixo.lower() in nome.lower():
            return tipo
    return nome.rsplit(".", 1)[-1].lower() if "." in nome else "artefato"


def _listar_entrega(cycle_dir: Path) -> list[dict]:
    """Artefatos gerados em output/entrega/ (best-effort; ignora temporários ~$ e manifestos)."""
    entrega_dir = cycle_dir / "output" / "entrega"
    if not entrega_dir.is_dir():
        return []
    itens: list[dict] = []
    for f in sorted(entrega_dir.iterdir()):
        if not f.is_file() or f.name.startswith("~$") or f.name.startswith("."):
            continue
        if f.suffix.lower() == ".json":   # manifesto/insumos internos, não entregáveis
            continue
        try:
            tamanho = f.stat().st_size
        except OSError:
            tamanho = 0
        itens.append({"nome": f.name, "path": str(f), "bytes": tamanho,
                      "tipo": _classificar_entrega(f.name)})
    return itens


def _calls_entrega_por_tipo(calls: list[dict]) -> dict[str, int]:
    """Itemiza as call_types da Fase de Entrega (do Mycroft), antes escondidas no agregado."""
    contagem: dict[str, int] = {}
    for c in calls:
        ct = c.get("call_type", "")
        if ct in _ENTREGA_CALL_TYPES:
            contagem[ct] = contagem.get(ct, 0) + 1
    return contagem


def _listar_stranger_room(cycle_dir: Path) -> dict[str, list[dict]]:
    """{fase: [{nome, path}]} — arquivos de deliberação, com path absoluto p/ link."""
    result: dict[str, list[dict]] = {}
    sr_dir = cycle_dir / "stranger_room"
    if not sr_dir.is_dir():
        return result
    for subfase in sorted(sr_dir.iterdir()):
        if subfase.is_dir():
            arquivos = [
                {"nome": f.name, "path": str(f)}
                for f in sorted(subfase.glob("*.md"))
            ]
            if arquivos:
                result[subfase.name] = arquivos
    return result


def _perfilamento_stats(runtime_dir: Path, events: list[dict]) -> dict:
    """Lê perfil_pacote.yaml e/ou eventos de perfilamento para popular as métricas."""
    result = {
        "perfil_arquivos_total": 0,
        "perfil_alertas_criticos": 0,
        "perfil_colunas_compartilhadas": 0,
        "perfil_arquivos_com_erro": 0,
        "perfil_executado": False,
    }
    # Tentar evento PERFILAMENTO_CONCLUIDO primeiro (mais confiável)
    for e in events:
        if e.get("event_type") == "PERFILAMENTO_CONCLUIDO":
            d = e.get("details", {})
            result["perfil_arquivos_total"] = _safe_int(d.get("arquivos_perfilados", 0))
            result["perfil_alertas_criticos"] = _safe_int(d.get("alertas_criticos", 0))
            result["perfil_colunas_compartilhadas"] = _safe_int(d.get("colunas_compartilhadas", 0))
            result["perfil_arquivos_com_erro"] = _safe_int(d.get("arquivos_com_erro", 0))
            result["perfil_executado"] = True
            return result
    # Fallback: ler perfil_pacote.yaml diretamente
    perfil_path = runtime_dir / "perfis" / "perfil_pacote.yaml"
    if perfil_path.exists():
        try:
            import yaml
            dados = yaml.safe_load(perfil_path.read_text(encoding="utf-8")) or {}
            result["perfil_arquivos_total"] = len(dados.get("arquivos_perfilados", []))
            result["perfil_arquivos_com_erro"] = len(dados.get("arquivos_com_erro", []))
            result["perfil_colunas_compartilhadas"] = len(dados.get("colunas_compartilhadas", {}))
            # Contar alertas críticos nos perfis individuais
            n_crit = 0
            for nome in dados.get("arquivos_perfilados", []):
                pf = runtime_dir / "perfis" / f"{nome}.perfil.yaml"
                if pf.exists():
                    with contextlib.suppress(Exception):
                        pf_data = yaml.safe_load(pf.read_text(encoding="utf-8")) or {}
                        for alerta in pf_data.get("alertas", []):
                            if alerta.get("severidade") == "CRITICA":
                                n_crit += 1
            result["perfil_alertas_criticos"] = n_crit
            result["perfil_executado"] = True
        except Exception:  # noqa: BLE001
            pass
    return result


def _manifest_info(cycle_dir: Path) -> dict:
    """Extrai package_hash e contagem de arquivos do manifest.md (best-effort)."""
    result = {"package_hash": "", "n_arquivos_total": 0, "n_arquivos_analisavel": 0}
    manifest = cycle_dir / "manifest.md"
    if not manifest.exists():
        return result
    try:
        texto = manifest.read_text(encoding="utf-8", errors="replace")
        import re
        m = re.search(r"Hash de integridade do pacote.*?`([a-f0-9]{16,})`", texto, re.IGNORECASE)
        if m:
            result["package_hash"] = m.group(1)[:16]
        # Contar linhas da tabela de arquivos (cada linha começa com "| ")
        linhas_tabela = [ln for ln in texto.splitlines()
                         if ln.startswith("| ") and "---" not in ln and "Arquivo" not in ln]
        result["n_arquivos_total"] = len(linhas_tabela)
        # "analisavel" — linhas que não têm "metadados"
        analisavel = sum(1 for ln in linhas_tabela if "metadados" not in ln.lower())
        result["n_arquivos_analisavel"] = analisavel
    except Exception:  # noqa: BLE001
        pass
    return result


def _watson_arquivos_detail(events: list[dict]) -> list[dict]:
    """Lista de arquivos analisados por Watson, na ordem de análise."""
    arquivos = []
    for e in events:
        if e.get("event_type") == "WATSON_ARQUIVO_ANALISADO":
            d = e.get("details", {})
            arquivos.append({
                "nome": d.get("arquivo", d.get("file", "")),
                "timestamp_utc": e.get("timestamp_utc", ""),
                "alertas": _safe_int(d.get("alertas_criticos", d.get("critical_alerts", 0))),
            })
    return arquivos


def _calcular_duracao(opened: str, ended: str) -> str:
    if not opened:
        return "—"
    fmt = "%Y-%m-%dT%H:%M:%SZ"
    try:
        t0 = datetime.strptime(opened, fmt).replace(tzinfo=UTC)
        t1 = datetime.strptime(ended, fmt).replace(tzinfo=UTC) if ended else datetime.now(UTC)
        total_s = int((t1 - t0).total_seconds())
        h, rem = divmod(total_s, 3600)
        m, s = divmod(rem, 60)
        if h > 0:
            return f"{h}h {m:02d}min"
        return f"{m}min {s:02d}s"
    except (ValueError, OverflowError):
        return "—"


def _diff_minutos(ts_inicio: str, ts_fim: str) -> float | None:
    fmt = "%Y-%m-%dT%H:%M:%SZ"
    try:
        t0 = datetime.strptime(ts_inicio, fmt).replace(tzinfo=UTC)
        t1 = datetime.strptime(ts_fim, fmt).replace(tzinfo=UTC)
        return (t1 - t0).total_seconds() / 60
    except (ValueError, OverflowError):
        return None


def _safe_int(val: object) -> int:
    try:
        return int(val) if val not in (None, "") else 0
    except (ValueError, TypeError):
        return 0
