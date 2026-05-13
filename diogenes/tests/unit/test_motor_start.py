"""tests/unit/test_motor_start.py"""
from __future__ import annotations

import pytest

from diogenes.config import get_config
from diogenes.motors.exceptions import InputMissingError, NoPreviousCycleError
from diogenes.motors.motor_start import MotorStart, _collect_inputs, _sha256_package
from diogenes.orchestrator.states import CycleState
from diogenes.persistence.audit_index import AuditIndex


@pytest.fixture
def cfg(env_vars, workspace):
    return get_config()


class TestMotorStart:

    def test_estrutura_ciclo_criada(self, cfg, module_input, workspace):
        motor = MotorStart(cfg)
        manifest = motor.run("MOD_SINT_001", 1)
        cycle_dir = workspace / "cycles" / manifest.cycle_id
        assert (cycle_dir / "inputs").is_dir()
        assert (cycle_dir / "stranger_room" / "watson_integridade").is_dir()
        assert (cycle_dir / "stranger_room" / "sherlock_validacao").is_dir()
        assert (cycle_dir / "output").is_dir()
        assert (cycle_dir / "_runtime" / "llm_calls").is_dir()

    def test_manifesto_gerado(self, cfg, module_input, workspace):
        motor = MotorStart(cfg)
        manifest = motor.run("MOD_SINT_001", 1)
        mp = workspace / "cycles" / manifest.cycle_id / "manifest.md"
        assert mp.exists()
        content = mp.read_text(encoding="utf-8")
        assert "# Manifesto de Abertura" in content
        assert "MOD_SINT_001" in content
        assert "Atividade 1 — Validação de Módulo" in content
        assert "TC 015.848/2025-6" in content
        assert manifest.cycle_id in content
        assert "descricao_metodologica.md" in content

    def test_inputs_copiados_e_originais_intactos(self, cfg, module_input, workspace):
        motor = MotorStart(cfg)
        manifest = motor.run("MOD_SINT_001", 1)
        inputs_dir = workspace / "cycles" / manifest.cycle_id / "inputs"
        assert (inputs_dir / "descricao_metodologica.md").exists()
        assert (inputs_dir / "planilha_cbs.xlsx").exists()
        assert (inputs_dir / "atas" / "ata_reuniao_entrega.md").exists()
        assert (module_input / "descricao_metodologica.md").exists()  # original intacto

    def test_registro_no_audit_index(self, cfg, module_input, workspace):
        motor = MotorStart(cfg)
        manifest = motor.run("MOD_SINT_001", 1)
        record = AuditIndex(workspace).get_cycle(manifest.cycle_id)
        assert record is not None
        assert record["module_id"] == "MOD_SINT_001"
        assert record["status"] == CycleState.PREPARADO.value
        assert record["watson_rodadas"] == "0"
        assert record["custo_total_usd"] == "0.00"

    def test_hash_deterministico(self, cfg, module_input, workspace):
        files = _collect_inputs(module_input)
        h1 = _sha256_package(files)
        h2 = _sha256_package(files)
        assert h1 == h2

    def test_cycle_id_formato(self, cfg, module_input):
        motor = MotorStart(cfg)
        manifest = motor.run("MOD_SINT_001", 1)
        assert "MOD_SINT_001" in manifest.cycle_id
        assert "_A1_" in manifest.cycle_id
        assert manifest.cycle_id.endswith("Z")

    def test_falha_sem_input_dir(self, cfg, workspace):
        motor = MotorStart(cfg)
        with pytest.raises(InputMissingError, match="não encontrado"):
            motor.run("MOD_NAO_EXISTE", 1)

    def test_falha_input_dir_vazio(self, cfg, workspace):
        (workspace / "input" / "MOD_VAZIO").mkdir()
        motor = MotorStart(cfg)
        with pytest.raises(InputMissingError, match="vazio"):
            motor.run("MOD_VAZIO", 1)

    def test_falha_atividade_invalida(self, cfg, module_input):
        motor = MotorStart(cfg)
        with pytest.raises(ValueError, match="inválida"):
            motor.run("MOD_SINT_001", 99)

    def test_atividade2_sem_ciclo_a1_levanta_erro(self, cfg, module_input):
        motor = MotorStart(cfg)
        with pytest.raises(NoPreviousCycleError):
            motor.run("MOD_SINT_001", 2)


class TestCycleState:

    def test_todos_estados_tem_transicoes(self):
        from diogenes.orchestrator.states import TRANSICOES_VALIDAS
        for state in CycleState:
            assert state in TRANSICOES_VALIDAS

    def test_estados_terminais_sem_transicao(self):
        from diogenes.orchestrator.states import TRANSICOES_VALIDAS
        terminais = {
            CycleState.ENCERRADO_CHANCELADO,
            CycleState.ABORTADO_FALHA_AGENTE,
            CycleState.ABORTADO_LESTRADE,
        }
        for t in terminais:
            assert TRANSICOES_VALIDAS[t] == set()
