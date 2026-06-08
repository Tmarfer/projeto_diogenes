"""tests/unit/test_report.py — Testes do módulo reports."""
from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from diogenes.reports.cycle_report import (
    _agregar_llm_por_agente,
    _calcular_duracao,
    _timeline_fases,
    build_report,
)
from diogenes.reports.render_html import render_html
from diogenes.reports.render_markdown import render_markdown

_CYCLE_ID = "MOD_010_A1_20260604T013158Z"

_AUDIT_COLUMNS = [
    "cycle_id", "module_id", "activity", "status", "opened_at_utc", "ended_at_utc",
    "is_sigilo_module", "previous_cycle_id", "watson_rodadas", "sherlock_rodadas",
    "mycroft_overruled_watson", "mycroft_overruled_sherlock", "watson_critical_alerts_count",
    "sherlock_dilemmas_count", "motor_saida_invocado_at_utc", "motor_saida_occurrences",
    "motor_saida_decision", "lestrade_seal_at_utc", "output_filename", "output_hash",
    "custo_total_usd", "tokens_mycroft", "tokens_watson", "tokens_sherlock", "ambiente",
    "diogenes_version", "git_commit", "irene_invocada_at_utc", "irene_resultado",
    "irene_score", "irene_dir_saida",
]

_AUDIT_VALUES = [
    _CYCLE_ID, "MOD_010", "1", "ENCERRADO_CHANCELADO",
    "2026-06-04T01:31:58Z", "2026-06-04T14:39:14Z",
    "false", "", "2", "1", "false", "false", "257", "0",
    "2026-06-04T14:39:01Z", "14", "LIMPO", "2026-06-04T14:39:14Z",
    f"relatorio_preliminar_{_CYCLE_ID}.md", "sha256:abc123",
    "0.00", "0", "0", "0", "local", "0.1.0", "abc12345def0",
    "2026-06-04T01:31:59Z", "IRENE_ALERTA", "0.9529", "/path/irene",
]

_EVENTS = [
    {"timestamp_utc": "2026-06-04T01:31:59Z", "cycle_id": _CYCLE_ID, "event_type": "CYCLE_STARTED", "phase": None, "agent": None, "details": {}},
    {"timestamp_utc": "2026-06-04T01:34:51Z", "cycle_id": _CYCLE_ID, "event_type": "PHASE_STARTED", "phase": "watson_integridade", "agent": None, "details": {}},
    {"timestamp_utc": "2026-06-04T02:00:00Z", "cycle_id": _CYCLE_ID, "event_type": "WATSON_ARQUIVO_ANALISADO", "phase": "watson_integridade", "agent": "watson", "details": {"arquivo": "test.md", "criticos": 2}},
    {"timestamp_utc": "2026-06-04T02:30:00Z", "cycle_id": _CYCLE_ID, "event_type": "WATSON_ARQUIVO_ANALISADO", "phase": "watson_integridade", "agent": "watson", "details": {"arquivo": "test2.md", "criticos": 0}},
    {"timestamp_utc": "2026-06-04T14:00:00Z", "cycle_id": _CYCLE_ID, "event_type": "PHASE_ENDED", "phase": "watson_integridade", "agent": None, "details": {}},
    {"timestamp_utc": "2026-06-04T14:10:00Z", "cycle_id": _CYCLE_ID, "event_type": "SHERLOCK_REGUA_CARREGADA", "phase": "sherlock_validacao", "agent": "sherlock", "details": {"metodologia_chars": 41834, "corpus_juridico_chars": 28500, "corpus_dir": "/path"}},
    {"timestamp_utc": "2026-06-04T14:30:00Z", "cycle_id": _CYCLE_ID, "event_type": "CONSOLIDACAO_CONCLUIDA", "phase": None, "agent": None, "details": {"arquivo": f"relatorio_preliminar_{_CYCLE_ID}.md"}},
]

_CALLS = [
    {"call_id": "c1", "cycle_id": _CYCLE_ID, "timestamp_utc": "2026-06-04T01:34:51Z", "provider": "chattcu", "model": "gpt-5.5-thinking", "phase": "watson_integridade", "agent": "watson", "call_type": "analise_inicial", "prompt_tokens": 1000, "completion_tokens": 500, "cost_usd": 0.0, "response_length": 1200},
    {"call_id": "c2", "cycle_id": _CYCLE_ID, "timestamp_utc": "2026-06-04T02:00:00Z", "provider": "chattcu", "model": "gpt-5.5-thinking", "phase": "watson_integridade", "agent": "watson", "call_type": "analise_arquivo", "prompt_tokens": 2000, "completion_tokens": 800, "cost_usd": 0.0, "response_length": 2000},
    {"call_id": "c3", "cycle_id": _CYCLE_ID, "timestamp_utc": "2026-06-04T14:10:00Z", "provider": "chattcu", "model": "gpt-5.5-thinking", "phase": "sherlock_validacao", "agent": "sherlock", "call_type": "validacao_inicial", "prompt_tokens": 5000, "completion_tokens": 2000, "cost_usd": 0.0, "response_length": 5000},
]


@pytest.fixture
def workspace(tmp_path: Path) -> tuple[Path, str]:
    cycle_dir = tmp_path / "cycles" / _CYCLE_ID
    runtime_dir = cycle_dir / "_runtime"
    runtime_dir.mkdir(parents=True)
    (cycle_dir / "output").mkdir()
    (runtime_dir / "watson_checkpoints").mkdir()
    (cycle_dir / "stranger_room" / "watson_integridade").mkdir(parents=True)
    (cycle_dir / "stranger_room" / "sherlock_validacao").mkdir(parents=True)

    # Stranger Room files
    (cycle_dir / "stranger_room" / "watson_integridade" / "01_apresentacao.md").write_text("ok")
    (cycle_dir / "stranger_room" / "watson_integridade" / "99_decisao_final.md").write_text("ok")

    # events.jsonl
    with open(runtime_dir / "events.jsonl", "w", encoding="utf-8") as f:
        for e in _EVENTS:
            f.write(json.dumps(e) + "\n")

    # llm_calls.jsonl
    with open(runtime_dir / "llm_calls.jsonl", "w", encoding="utf-8") as f:
        for c in _CALLS:
            f.write(json.dumps(c) + "\n")

    # audit_index.csv
    with open(tmp_path / "audit_index.csv", "w", encoding="utf-8") as f:
        f.write(",".join(_AUDIT_COLUMNS) + "\n")
        f.write(",".join(_AUDIT_VALUES) + "\n")

    return tmp_path, _CYCLE_ID


# ── build_report ──────────────────────────────────────────────────────────────

def test_build_report_campos_preenchidos(workspace: tuple[Path, str]) -> None:
    ws, cid = workspace
    data = build_report(cid, ws)
    assert data.cycle_id == cid
    assert data.module_id == "MOD_010"
    assert data.status == "ENCERRADO_CHANCELADO"
    assert data.arquivos_analisados == 2
    assert data.watson_critical_alerts == 257
    assert data.metodologia_chars == 41834
    assert data.corpus_juridico_chars == 28500
    assert data.is_terminal is True
    assert data.total_calls == 3
    assert data.irene_score == pytest.approx(0.9529)
    assert data.watson_rodadas == 2
    assert data.sherlock_rodadas == 1
    assert data.motor_saida_occurrences == 14
    assert data.motor_saida_decision == "LIMPO"
    assert data.motor_saida_limpo is True


def test_build_report_stranger_room(workspace: tuple[Path, str]) -> None:
    ws, cid = workspace
    data = build_report(cid, ws)
    assert "watson_integridade" in data.stranger_room_files
    nomes = [f["nome"] for f in data.stranger_room_files["watson_integridade"]]
    assert "01_apresentacao.md" in nomes
    # cada entrada carrega path absoluto p/ link file://
    assert all(f.get("path") for f in data.stranger_room_files["watson_integridade"])


def test_build_report_sem_audit_index(tmp_path: Path) -> None:
    """build_report não levanta exceção quando audit_index não existe."""
    cid = "MOD_999_A1_20260101T000000Z"
    (tmp_path / "cycles" / cid / "_runtime").mkdir(parents=True)
    data = build_report(cid, tmp_path)
    assert data.cycle_id == cid
    assert data.status == ""
    assert data.total_calls == 0


# ── _agregar_llm_por_agente ───────────────────────────────────────────────────

def test_agregar_llm_por_agente() -> None:
    calls = [
        {"agent": "watson", "prompt_tokens": 1000, "completion_tokens": 500, "response_length": 1200},
        {"agent": "watson", "prompt_tokens": 2000, "completion_tokens": 800, "response_length": 2000},
        {"agent": "sherlock", "prompt_tokens": 5000, "completion_tokens": 2000, "response_length": 5000},
    ]
    stats = _agregar_llm_por_agente(calls)
    assert stats["watson"].calls == 2
    assert stats["watson"].prompt_tokens == 3000
    assert stats["watson"].completion_tokens == 1300
    assert stats["watson"].avg_response_length == pytest.approx(1600.0)
    assert stats["sherlock"].calls == 1
    assert stats["sherlock"].prompt_tokens == 5000


def test_agregar_llm_vazio() -> None:
    assert _agregar_llm_por_agente([]) == {}


# ── _timeline_fases ───────────────────────────────────────────────────────────

def test_timeline_fases_ordem() -> None:
    events = [
        {"event_type": "PHASE_STARTED", "phase": "watson_integridade", "timestamp_utc": "2026-06-04T01:34:51Z"},
        {"event_type": "PHASE_ENDED",   "phase": "watson_integridade", "timestamp_utc": "2026-06-04T14:00:00Z"},
        {"event_type": "PHASE_STARTED", "phase": "sherlock_validacao", "timestamp_utc": "2026-06-04T14:01:00Z"},
        {"event_type": "PHASE_ENDED",   "phase": "sherlock_validacao", "timestamp_utc": "2026-06-04T14:30:00Z"},
    ]
    fases = _timeline_fases(events)
    assert len(fases) == 2
    assert fases[0].fase == "watson_integridade"
    assert fases[0].duration_min > 0
    assert fases[1].fase == "sherlock_validacao"


def test_timeline_fases_sem_phase_ended() -> None:
    events = [
        {"event_type": "PHASE_STARTED", "phase": "watson_integridade", "timestamp_utc": "2026-06-04T01:34:51Z"},
    ]
    fases = _timeline_fases(events)
    assert len(fases) == 1
    assert fases[0].ended_at == ""
    assert fases[0].duration_min == 0.0


# ── _calcular_duracao ─────────────────────────────────────────────────────────

def test_calcular_duracao_horas() -> None:
    d = _calcular_duracao("2026-06-04T01:31:58Z", "2026-06-04T14:39:14Z")
    assert "h" in d


def test_calcular_duracao_minutos() -> None:
    d = _calcular_duracao("2026-06-04T01:31:58Z", "2026-06-04T01:45:00Z")
    assert "min" in d
    assert "h" not in d


def test_calcular_duracao_sem_opened() -> None:
    assert _calcular_duracao("", "") == "—"


# ── render_markdown ───────────────────────────────────────────────────────────

def test_render_markdown_tem_secoes(workspace: tuple[Path, str]) -> None:
    ws, cid = workspace
    data = build_report(cid, ws)
    md = render_markdown(data)
    assert cid in md
    assert "Watson" in md
    assert "Sherlock" in md
    assert "257" in md  # alertas críticos
    assert "41" in md   # metodologia chars
    assert "LIMPO" in md


def test_render_markdown_irene_score(workspace: tuple[Path, str]) -> None:
    ws, cid = workspace
    data = build_report(cid, ws)
    md = render_markdown(data)
    assert "0.9529" in md


# ── render_html ───────────────────────────────────────────────────────────────

def test_render_html_estrutura_basica(workspace: tuple[Path, str]) -> None:
    ws, cid = workspace
    data = build_report(cid, ws)
    html = render_html(data)
    assert "<!DOCTYPE html>" in html
    assert "<html" in html
    assert "<table" in html
    assert cid in html


def test_render_html_terminal_sem_refresh(workspace: tuple[Path, str]) -> None:
    ws, cid = workspace
    data = build_report(cid, ws)
    assert data.is_terminal is True
    html = render_html(data)
    assert 'http-equiv="refresh"' not in html


def test_render_html_live_com_refresh(workspace: tuple[Path, str]) -> None:
    ws, cid = workspace
    data = build_report(cid, ws)
    data_live = replace(data, status="EM_EXECUCAO_WATSON", is_terminal=False)
    html = render_html(data_live)
    assert 'http-equiv="refresh"' in html
    assert "AO VIVO" in html


def test_render_html_status_badge_success(workspace: tuple[Path, str]) -> None:
    ws, cid = workspace
    data = build_report(cid, ws)
    html = render_html(data)
    assert "badge-success" in html  # ENCERRADO_CHANCELADO → success


# ── Fase de Entrega + assets (painel v2) ──────────────────────────────────────

def test_listar_entrega_coleta_e_ignora_temporarios(tmp_path: Path) -> None:
    from diogenes.reports.cycle_report import _listar_entrega
    entrega = tmp_path / "cycles" / "C" / "output" / "entrega"
    entrega.mkdir(parents=True)
    (entrega / "Dashboard.html").write_text("x" * 100)
    (entrega / "Apendice_Modulo10.docx").write_bytes(b"y" * 2048)
    (entrega / "~$Apendice_Modulo10.docx").write_text("tmp")          # temporário Office
    (entrega / "entrega_manifesto.json").write_text("{}")             # insumo interno
    itens = _listar_entrega(tmp_path / "cycles" / "C")
    nomes = {i["nome"] for i in itens}
    assert nomes == {"Dashboard.html", "Apendice_Modulo10.docx"}
    tipos = {i["nome"]: i["tipo"] for i in itens}
    assert tipos["Dashboard.html"] == "dashboard"
    assert tipos["Apendice_Modulo10.docx"] == "apêndice"


def test_calls_entrega_por_tipo() -> None:
    from diogenes.reports.cycle_report import _calls_entrega_por_tipo
    calls = [
        {"agent": "mycroft", "call_type": "mapear_dados_modulo"},
        {"agent": "mycroft", "call_type": "avaliar_entrega"},
        {"agent": "mycroft", "call_type": "avaliar_entrega"},
        {"agent": "mycroft", "call_type": "consolidar"},   # não é de entrega
        {"agent": "watson", "call_type": "analise_inicial"},
    ]
    assert _calls_entrega_por_tipo(calls) == {"mapear_dados_modulo": 1, "avaliar_entrega": 2}


def test_carregar_retrato() -> None:
    from diogenes.reports.assets import carregar_retrato
    assert carregar_retrato("mycroft").startswith("data:image/jpeg;base64,")
    assert carregar_retrato("inexistente_zzz") == ""


def test_render_html_secao_entrega_presente(workspace: tuple[Path, str]) -> None:
    ws, cid = workspace
    data = replace(
        build_report(cid, ws),
        entrega_invocado_at="2026-06-04T17:45:00Z", entrega_veredito="APROVADO",
        entrega_artefatos_list=[{"nome": "Dashboard.html", "path": "/x/Dashboard.html",
                                 "bytes": 17228, "tipo": "dashboard"}],
        entrega_calls_by_type={"mapear_dados_modulo": 1, "avaliar_entrega": 3},
    )
    html = render_html(data)
    assert "<h2>Fase de Entrega</h2>" in html
    assert "Dashboard.html" in html and "avaliar_entrega" in html


def test_render_html_secao_entrega_ausente(workspace: tuple[Path, str]) -> None:
    ws, cid = workspace
    assert "<h2>Fase de Entrega</h2>" not in render_html(build_report(cid, ws))


def test_render_html_cards_com_retrato_e_lestrade(workspace: tuple[Path, str]) -> None:
    html = render_html(build_report(workspace[1], workspace[0]))
    assert html.count('class="avatar-img"') == 5   # Irene, Watson, Mycroft, Sherlock, Lestrade
    assert "Insp. Lestrade" in html
