"""tests/unit/test_motor_saida.py"""
from __future__ import annotations

from datetime import UTC

import pytest

from diogenes.config import get_config
from diogenes.motors.exceptions import MotorSaidaError
from diogenes.motors.motor_saida import (
    MotorSaida,
    _classificar_posicao,
    _extrair_contexto,
    sanitizar_delivery_text,
)
from diogenes.motors.motor_start import MotorStart
from diogenes.orchestrator.states import CycleState
from diogenes.persistence.audit_index import AuditIndex

# ── Relatório limpo (sem marcas) ─────────────────────────────────────────

RELATORIO_LIMPO = """# Relatório Preliminar de Análise
**Processo:** TC 015.848/2025-6
**Módulo:** MOD_SINT_001

## Contexto

Análise do módulo realizada conforme metodologia homologada.

## Achados de Integridade

Nenhuma inconsistência identificada nos artefatos entregues.

## Achados de Aderência Metodológica

O módulo atende aos requisitos metodológicos aplicáveis.

## Posição do Departamento

Módulo apto para validação.
"""

# ── Relatório com marcas ─────────────────────────────────────────────────

RELATORIO_COM_MARCAS = """# Relatório Preliminar
**Processo:** TC 015.848/2025-6

## Análise

Watson identificou inconsistências nos dados.
O Auditor de Integridade Técnica analisou as planilhas.
"""


# ── Fixtures ─────────────────────────────────────────────────────────────

@pytest.fixture
def cfg(env_vars, workspace):
    return get_config()


@pytest.fixture
def ciclo_aguardando_saida(cfg, module_input, workspace):
    """Ciclo em AGUARDANDO_VERIFICACAO_SAIDA com relatório gerado."""
    motor = MotorStart(cfg)
    manifest = motor.run("MOD_SINT_001", 1)
    cycle_dir = workspace / "cycles" / manifest.cycle_id

    # Gerar relatório fictício
    output_dir = cycle_dir / "output"
    output_dir.mkdir(exist_ok=True)
    relatorio = output_dir / f"relatorio_preliminar_{manifest.cycle_id}.md"
    relatorio.write_text(RELATORIO_LIMPO, encoding="utf-8")

    # Avançar para o estado correto
    audit = AuditIndex(workspace)
    audit.update_status(manifest.cycle_id, CycleState.AGUARDANDO_VERIFICACAO_SAIDA.value,
                        output_filename=relatorio.name)
    return manifest.cycle_id, cycle_dir


@pytest.fixture
def ciclo_com_marcas(cfg, module_input, workspace, ciclo_aguardando_saida):
    """Ciclo com relatório contendo marcas internas."""
    cycle_id, cycle_dir = ciclo_aguardando_saida
    # Substituir o relatório por um com marcas
    outputs = list((cycle_dir / "output").glob("relatorio_*.md"))
    outputs[0].write_text(RELATORIO_COM_MARCAS, encoding="utf-8")
    return cycle_id


# ── Testes unitários puros (sem instanciar MotorSaida) ───────────────────

class TestHelpers:

    def test_classificar_posicao_cabecalho(self):
        assert _classificar_posicao(1, 100) == "CABECALHO"
        assert _classificar_posicao(5, 100) == "CABECALHO"

    def test_classificar_posicao_rodape(self):
        assert _classificar_posicao(95, 100) == "RODAPE"
        assert _classificar_posicao(100, 100) == "RODAPE"

    def test_classificar_posicao_corpo(self):
        assert _classificar_posicao(6, 100) == "CORPO"
        assert _classificar_posicao(50, 100) == "CORPO"

    def test_extrair_contexto(self):
        linhas = ["linha 1", "linha 2", "linha 3 ALVO", "linha 4", "linha 5"]
        ctx = _extrair_contexto(linhas, 2)   # idx=2, linha 3 é o alvo
        assert ">>>" in ctx
        assert "linha 3 ALVO" in ctx

    def test_varredura_documento_limpo(self, cfg):
        motor = MotorSaida()
        ocorrencias = motor._varrer(RELATORIO_LIMPO)
        # Relatório limpo: "Projeto Diógenes" não está no texto
        assert len(ocorrencias) == 0

    def test_varredura_detecta_nome_agente(self, cfg):
        motor = MotorSaida()
        ocorrencias = motor._varrer(RELATORIO_COM_MARCAS)
        categorias = [o.categoria for o in ocorrencias]
        assert "NOME_AGENTE" in categorias

    def test_varredura_detecta_cargo_identificador(self, cfg):
        motor = MotorSaida()
        ocorrencias = motor._varrer(RELATORIO_COM_MARCAS)
        categorias = [o.categoria for o in ocorrencias]
        assert "CARGO_IDENTIFICADOR" in categorias


# ── Testes integrados (com estado real do ciclo) ──────────────────────────

class TestMotorSaidaIntegrado:

    def test_verificar_documento_limpo(self, cfg, ciclo_aguardando_saida):
        cycle_id, _ = ciclo_aguardando_saida
        motor = MotorSaida()
        report = motor.verificar(cycle_id)
        assert report.documento_limpo
        assert report.total_ocorrencias == 0
        assert report.doc_hash.startswith("sha256:")

        # Deve ter avançado para AGUARDANDO_CHANCELA
        record = AuditIndex(cfg.workspace.path).get_cycle(cycle_id)
        assert record["status"] == CycleState.AGUARDANDO_CHANCELA_LESTRADE.value
        assert record["motor_saida_occurrences"] == "0"

    def test_verificar_documento_com_marcas(self, cfg, ciclo_com_marcas):
        motor = MotorSaida()
        report = motor.verificar(ciclo_com_marcas)
        assert not report.documento_limpo
        assert report.total_ocorrencias > 0

        # NÃO avança para chancela quando há marcas
        record = AuditIndex(cfg.workspace.path).get_cycle(ciclo_com_marcas)
        assert record["status"] == CycleState.AGUARDANDO_VERIFICACAO_SAIDA.value

    def test_verificar_estado_invalido_levanta_erro(self, cfg, module_input, workspace):
        motor_start = MotorStart(cfg)
        manifest = motor_start.run("MOD_SINT_001", 1)
        # Estado PREPARADO — não pode chamar Motor de Saída
        motor = MotorSaida()
        with pytest.raises(MotorSaidaError, match="AGUARDANDO_VERIFICACAO_SAIDA"):
            motor.verificar(manifest.cycle_id)

    def test_seal_ciclo_limpo(self, cfg, ciclo_aguardando_saida):
        from datetime import datetime
        cycle_id, _ = ciclo_aguardando_saida
        motor = MotorSaida()
        motor.verificar(cycle_id)   # avança para AGUARDANDO_CHANCELA_LESTRADE
        now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        AuditIndex(cfg.workspace.path).seal_cycle(cycle_id, "LIMPO", now)
        record = AuditIndex(cfg.workspace.path).get_cycle(cycle_id)
        assert record["status"] == CycleState.ENCERRADO_CHANCELADO.value
        assert record["motor_saida_decision"] == "LIMPO"
        assert record["lestrade_seal_at_utc"] == now
        assert record["ended_at_utc"] == now


# ── sanitizar_delivery_text (RF-EN-06) ──────────────────────────────────────

class TestSanitizarDeliveryText:
    def test_remove_tags_secao(self, cfg):
        text = "Texto <!-- SECAO: intro --> antes <!-- /SECAO: intro --> depois"
        result = sanitizar_delivery_text(text)
        assert "SECAO" not in result
        assert "antes" in result and "depois" in result

    def test_remove_linha_arquivos(self, cfg):
        text = "Linha 1\n**Arquivos que compõem este consolidado:** lista\nLinha 3"
        result = sanitizar_delivery_text(text)
        assert "Arquivos que compõem" not in result
        assert "Linha 1" in result and "Linha 3" in result

    def test_remove_referencia_md_interna(self, cfg):
        text = "Conforme [MC_decisao_watson.md] e [sherlock_consolidado.md] acima."
        result = sanitizar_delivery_text(text)
        assert "[MC_decisao_watson.md]" not in result
        assert "[sherlock_consolidado.md]" not in result

    def test_texto_limpo_passa_intacto(self, cfg):
        text = "Análise do Módulo CBS — sem marcas internas."
        result = sanitizar_delivery_text(text)
        assert "Análise do Módulo CBS" in result
