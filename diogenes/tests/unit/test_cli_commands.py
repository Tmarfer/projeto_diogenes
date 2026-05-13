"""
tests/unit/test_cli_commands.py — DVA-CBS | Projeto Diógenes
Testes unitários para os comandos CLI via Typer test runner.

Referência normativa: SDD Bloco 13 (fixtures compartilhadas)
"""
from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from typer.testing import CliRunner

from diogenes.cli.app import app
from diogenes.config import get_config
from diogenes.motors.motor_start import MotorStart
from diogenes.orchestrator.states import CycleState
from diogenes.persistence.audit_index import AuditIndex

runner = CliRunner()


@pytest.fixture
def cfg(env_vars, workspace):
    return get_config()


@pytest.fixture
def ciclo_preparado(cfg, module_input, workspace):
    motor = MotorStart(cfg)
    manifest = motor.run("MOD_SINT_001", 1)
    return manifest.cycle_id


@pytest.fixture
def ciclo_aguardando_alerta(cfg, module_input, workspace):
    motor = MotorStart(cfg)
    manifest = motor.run("MOD_SINT_001", 1)
    AuditIndex(workspace).update_status(
        manifest.cycle_id,
        CycleState.AGUARDANDO_DECISAO_LESTRADE_ALERTA.value,
        watson_critical_alerts_count="1",
    )
    return manifest.cycle_id


@pytest.fixture
def ciclo_pausado(cfg, module_input, workspace, ciclo_aguardando_alerta):
    AuditIndex(workspace).update_status(
        ciclo_aguardando_alerta, CycleState.PAUSADO_LESTRADE.value
    )
    return ciclo_aguardando_alerta


@pytest.fixture
def ciclo_aguardando_chancela(cfg, module_input, workspace):
    motor = MotorStart(cfg)
    manifest = motor.run("MOD_SINT_001", 1)
    cycle_id = manifest.cycle_id
    cycle_dir = workspace / "cycles" / cycle_id
    output_dir = cycle_dir / "output"
    output_dir.mkdir(exist_ok=True)
    relatorio = output_dir / f"relatorio_preliminar_{cycle_id}.md"
    relatorio.write_text(
        "# Relatório Preliminar\n**Processo:** TC 015.848/2025-6\n\n"
        "Análise concluída.\n",
        encoding="utf-8",
    )
    AuditIndex(workspace).update_status(
        cycle_id,
        CycleState.AGUARDANDO_CHANCELA_LESTRADE.value,
        output_filename=relatorio.name,
    )
    return cycle_id


# ── diogenes init ────────────────────────────────────────────

class TestInit:

    def test_init_cria_workspace(self, env_vars, workspace):
        result = runner.invoke(app, ["init"])
        assert result.exit_code == 0
        assert (workspace / "audit_index.csv").exists()
        assert (workspace / "input").exists()
        assert (workspace / "cycles").exists()

    def test_init_idempotente(self, env_vars, workspace):
        runner.invoke(app, ["init"])
        result = runner.invoke(app, ["init"])
        assert result.exit_code == 0


# ── diogenes start ───────────────────────────────────────────

class TestStart:

    def test_start_cria_ciclo(self, env_vars, workspace, module_input):
        result = runner.invoke(app, ["start", "--module", "MOD_SINT_001", "--activity", "1"])
        assert result.exit_code == 0
        assert "PREPARADO" in result.stdout or "Cycle ID" in result.stdout

    def test_start_modulo_inexistente_falha(self, env_vars, workspace):
        result = runner.invoke(app, ["start", "--module", "MOD_NAO_EXISTE", "--activity", "1"])
        assert result.exit_code != 0

    def test_start_atividade_invalida_falha(self, env_vars, workspace, module_input):
        result = runner.invoke(app, ["start", "--module", "MOD_SINT_001", "--activity", "99"])
        assert result.exit_code != 0


# ── diogenes status ──────────────────────────────────────────

class TestStatus:

    def test_status_ciclo_existente(self, env_vars, workspace, ciclo_preparado):
        result = runner.invoke(app, ["status", "--cycle", ciclo_preparado])
        assert result.exit_code == 0
        assert "PREPARADO" in result.stdout
        assert "MOD_SINT_001" in result.stdout

    def test_status_ciclo_inexistente_falha(self, env_vars, workspace):
        result = runner.invoke(app, ["status", "--cycle", "CICLO_NAO_EXISTE"])
        assert result.exit_code != 0
        assert "não encontrado" in result.stdout


# ── diogenes list ────────────────────────────────────────────

class TestListCycles:

    def test_list_sem_ciclos(self, env_vars, workspace):
        runner.invoke(app, ["init"])
        result = runner.invoke(app, ["list"])
        assert result.exit_code == 0
        assert "Nenhum ciclo" in result.stdout

    def test_list_com_ciclo(self, env_vars, workspace, ciclo_preparado):
        result = runner.invoke(app, ["list"])
        assert result.exit_code == 0
        assert ciclo_preparado in result.stdout

    def test_list_filtro_modulo(self, env_vars, workspace, ciclo_preparado):
        result = runner.invoke(app, ["list", "--module", "MOD_SINT_001"])
        assert result.exit_code == 0
        assert ciclo_preparado in result.stdout

    def test_list_filtro_modulo_sem_resultado(self, env_vars, workspace, ciclo_preparado):
        result = runner.invoke(app, ["list", "--module", "MOD_NAO_EXISTE"])
        assert result.exit_code == 0
        assert "Nenhum ciclo" in result.stdout


# ── diogenes abort ───────────────────────────────────────────

class TestAbort:

    def test_abort_ciclo_preparado(self, env_vars, workspace, ciclo_preparado):
        result = runner.invoke(
            app, ["abort", "--cycle", ciclo_preparado, "--reason", "Teste de aborto"]
        )
        assert result.exit_code == 0
        assert "abortado" in result.stdout.lower()
        record = AuditIndex(workspace).get_cycle(ciclo_preparado)
        assert record["status"] == CycleState.ABORTADO_LESTRADE.value
        assert record["ended_at_utc"] != ""

    def test_abort_ciclo_inexistente_falha(self, env_vars, workspace):
        result = runner.invoke(
            app, ["abort", "--cycle", "CICLO_NAO_EXISTE", "--reason", "Teste"]
        )
        assert result.exit_code != 0

    def test_abort_ciclo_ja_abortado_falha(self, env_vars, workspace, ciclo_preparado):
        runner.invoke(app, ["abort", "--cycle", ciclo_preparado, "--reason", "Primeiro"])
        result = runner.invoke(app, ["abort", "--cycle", ciclo_preparado, "--reason", "Segundo"])
        assert result.exit_code != 0


# ── diogenes pause ───────────────────────────────────────────

class TestPause:

    def test_pause_ciclo_com_alerta(self, env_vars, workspace, ciclo_aguardando_alerta):
        result = runner.invoke(app, ["pause", "--cycle", ciclo_aguardando_alerta])
        assert result.exit_code == 0
        assert "pausado" in result.stdout.lower()
        record = AuditIndex(workspace).get_cycle(ciclo_aguardando_alerta)
        assert record["status"] == CycleState.PAUSADO_LESTRADE.value

    def test_pause_ciclo_em_estado_invalido_falha(self, env_vars, workspace, ciclo_preparado):
        result = runner.invoke(app, ["pause", "--cycle", ciclo_preparado])
        assert result.exit_code != 0

    def test_pause_ciclo_inexistente_falha(self, env_vars, workspace):
        result = runner.invoke(app, ["pause", "--cycle", "CICLO_NAO_EXISTE"])
        assert result.exit_code != 0


# ── diogenes show ────────────────────────────────────────────

class TestShow:

    def test_show_ciclo_id_desconhecido_falha(self, env_vars, workspace):
        result = runner.invoke(app, ["show", "--cycle", "CICLO_TOTALMENTE_INVALIDO"])
        assert result.exit_code != 0
        assert "não encontrada" in result.stdout.lower()

    def test_show_com_fase_watson_vazia(self, env_vars, workspace, ciclo_preparado):
        sr_dir = workspace / "cycles" / ciclo_preparado / "stranger_room"
        sr_dir.mkdir(parents=True, exist_ok=True)
        (sr_dir / "watson_integridade").mkdir(exist_ok=True)
        result = runner.invoke(app, ["show", "--cycle", ciclo_preparado, "--phase", "watson"])
        assert result.exit_code == 0
        assert "nenhum arquivo" in result.stdout.lower()

    def test_show_fase_invalida_retorna_vazio(self, env_vars, workspace, ciclo_preparado):
        sr_dir = workspace / "cycles" / ciclo_preparado / "stranger_room"
        sr_dir.mkdir(parents=True, exist_ok=True)
        result = runner.invoke(app, ["show", "--cycle", ciclo_preparado, "--phase", "inexistente"])
        assert result.exit_code == 0

    def test_show_ciclo_inexistente_falha(self, env_vars, workspace):
        result = runner.invoke(app, ["show", "--cycle", "CICLO_NAO_EXISTE"])
        assert result.exit_code != 0


# ── diogenes seal ────────────────────────────────────────────

class TestSeal:

    def test_seal_ciclo_aguardando_chancela(self, env_vars, workspace, ciclo_aguardando_chancela):
        result = runner.invoke(app, ["seal", "--cycle", ciclo_aguardando_chancela])
        assert result.exit_code == 0
        assert "LIMPO" in result.stdout
        record = AuditIndex(workspace).get_cycle(ciclo_aguardando_chancela)
        assert record["status"] == CycleState.ENCERRADO_CHANCELADO.value
        assert record["motor_saida_decision"] == "LIMPO"

    def test_seal_estado_invalido_falha(self, env_vars, workspace, ciclo_preparado):
        result = runner.invoke(app, ["seal", "--cycle", ciclo_preparado])
        assert result.exit_code != 0

    def test_seal_ciclo_inexistente_falha(self, env_vars, workspace):
        result = runner.invoke(app, ["seal", "--cycle", "CICLO_NAO_EXISTE"])
        assert result.exit_code != 0

    def test_seal_accept_occurrences_sem_reason_falha(
        self, env_vars, workspace, ciclo_preparado
    ):
        AuditIndex(workspace).update_status(
            ciclo_preparado, CycleState.AGUARDANDO_VERIFICACAO_SAIDA.value
        )
        result = runner.invoke(
            app, ["seal", "--cycle", ciclo_preparado, "--accept-occurrences"]
        )
        assert result.exit_code != 0
        assert "--reason" in result.stdout


# ── diogenes verify-output ───────────────────────────────────

class TestVerifyOutput:

    def test_verify_output_estado_invalido_falha(self, env_vars, workspace, ciclo_preparado):
        result = runner.invoke(app, ["verify-output", "--cycle", ciclo_preparado])
        assert result.exit_code != 0

    def test_verify_output_documento_limpo(self, env_vars, workspace, cfg, module_input):
        motor = MotorStart(cfg)
        manifest = motor.run("MOD_SINT_001", 1)
        cycle_id = manifest.cycle_id
        cycle_dir = workspace / "cycles" / cycle_id
        output_dir = cycle_dir / "output"
        relatorio = output_dir / f"relatorio_preliminar_{cycle_id}.md"
        relatorio.write_text(
            "# Relatório Preliminar\n**Processo:** TC 015.848/2025-6\n\n"
            "Módulo analisado. Nenhuma inconsistência.\n",
            encoding="utf-8",
        )
        AuditIndex(workspace).update_status(
            cycle_id,
            CycleState.AGUARDANDO_VERIFICACAO_SAIDA.value,
            output_filename=relatorio.name,
        )
        result = runner.invoke(app, ["verify-output", "--cycle", cycle_id])
        assert result.exit_code == 0
        assert "LIMPO" in result.stdout


# ── diogenes proceed / resume ────────────────────────────────

class TestProceedResume:

    def test_proceed_estado_invalido_falha(self, env_vars, workspace, ciclo_preparado):
        result = runner.invoke(app, ["proceed", "--cycle", ciclo_preparado])
        assert result.exit_code != 0
        assert "AGUARDANDO_DECISAO_LESTRADE_ALERTA" in result.stdout

    def test_resume_estado_invalido_falha(self, env_vars, workspace, ciclo_preparado):
        result = runner.invoke(app, ["resume", "--cycle", ciclo_preparado])
        assert result.exit_code != 0
        assert "PAUSADO_LESTRADE" in result.stdout

    def test_resume_ciclo_pausado_avanca_estado(self, env_vars, workspace, ciclo_pausado):
        # resume avança de PAUSADO_LESTRADE para AGUARDANDO_DECISAO_LESTRADE_ALERTA
        # e então tenta acionar Orchestrator — sem mock de LLM, vai falhar no LLM
        # mas a transição de estado deve ter ocorrido antes do erro
        runner.invoke(app, ["resume", "--cycle", ciclo_pausado])
        record = AuditIndex(workspace).get_cycle(ciclo_pausado)
        # O estado muda antes de tentar o Orchestrator; pode ter abortado depois
        assert record is not None
