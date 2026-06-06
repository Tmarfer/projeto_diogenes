"""
tests/unit/test_delivery.py — DVA-CBS | Projeto Diógenes
Etapa 1: classificação de arquivos (file_prep) + manifesto de entrega best-effort
+ Motor de Start com --delivery (árvore real, categorias, reconciliação).
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from diogenes.agents.file_prep import classificar
from diogenes.config import get_config
from diogenes.motors.motor_start import MotorStart
from diogenes.persistence.delivery import (
    DeliveryManifest,
    ler_manifesto_entrega,
    reconciliar,
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# ── classificar ────────────────────────────────────────────────────────────

def test_classificar_analisaveis():
    assert classificar("a/b/dados.csv") == (True, "csv")
    assert classificar("x.sql") == (True, "sql")
    assert classificar("nb.ipynb") == (True, "notebook")
    assert classificar("util.py") == (True, "script")
    assert classificar("doc.md") == (True, "documento")
    assert classificar("plan.xlsx") == (True, "planilha")


def test_classificar_metadados_e_denylist():
    # diretório na denylist
    assert classificar("03_LOGS/run.md")[0] is False
    assert classificar("02_INSUMOS_GERADOS/x.md")[0] is False
    # arquivo de metadados por nome
    assert classificar("metadados.json") == (False, "metadados")
    assert classificar("hashes_integridade.txt") == (False, "metadados")
    # extensão fora da allowlist
    assert classificar("foto.png") == (False, "metadados")
    assert classificar(".DS_Store") == (False, "metadados")


def test_classificar_allowlist_inventario_protocolo():
    # protocolo_recebimento.md e inventario.xlsx são analisados mesmo sob
    # 02_INSUMOS_GERADOS — os agentes precisam saber o que foi entregue.
    assert classificar("2026_04_27/02_INSUMOS_GERADOS/protocolo_recebimento.md") == (True, "documento")
    assert classificar("2026_04_27/02_INSUMOS_GERADOS/inventario.xlsx") == (True, "planilha")
    # metadados.json e hashes seguem ignorados (usados só na reconciliação)
    assert classificar("2026_04_27/02_INSUMOS_GERADOS/metadados.json")[0] is False
    assert classificar("2026_04_27/02_INSUMOS_GERADOS/hashes_integridade.txt")[0] is False


# ── manifesto de entrega (best-effort) ───────────────────────────────────────

def _delivery_tree(root: Path, com_manifesto: bool = True, hash_errado: bool = False) -> Path:
    delivery = root / "MOD_X" / "2026_04_27"
    entrada = delivery / "01_ENTRADA_COPIADA"
    entrada.mkdir(parents=True)
    (entrada / "dados.csv").write_text("id;v\n1;10\n", encoding="utf-8")
    (entrada / "extracao.sql").write_text("select 1;", encoding="utf-8")
    logs = delivery / "03_LOGS"
    logs.mkdir()
    (logs / "intake.log").write_text("log", encoding="utf-8")
    if com_manifesto:
        insumos = delivery / "02_INSUMOS_GERADOS"
        insumos.mkdir()
        csv_hash = _sha256(entrada / "dados.csv")
        sql_hash = "0" * 64 if hash_errado else _sha256(entrada / "extracao.sql")
        metadados = {
            "id_recebimento": "REC_MOD_X_1",
            "modulo": "MOD_X",
            "data_entrega": "2026-04-27",
            "totais": {"arquivos": 2},
            "hashes": {"dados.csv": csv_hash, "extracao.sql": sql_hash},
        }
        (insumos / "metadados.json").write_text(json.dumps(metadados), encoding="utf-8")
    return delivery


def test_ler_manifesto_entrega_e_reconciliar_ok(tmp_path):
    delivery = _delivery_tree(tmp_path, com_manifesto=True)
    dm = ler_manifesto_entrega(delivery)
    assert isinstance(dm, DeliveryManifest)
    assert dm.id_recebimento == "REC_MOD_X_1"

    encontrados = [
        ("01_ENTRADA_COPIADA/dados.csv", _sha256(delivery / "01_ENTRADA_COPIADA/dados.csv")),
        ("01_ENTRADA_COPIADA/extracao.sql", _sha256(delivery / "01_ENTRADA_COPIADA/extracao.sql")),
    ]
    rec = reconciliar(dm, encontrados)
    assert rec.status == "PRESENTE_OK"
    assert rec.total_casado == 2
    assert rec.faltando == []
    assert rec.hash_divergente == []


def test_reconciliar_ausente_quando_sem_manifesto(tmp_path):
    delivery = _delivery_tree(tmp_path, com_manifesto=False)
    assert ler_manifesto_entrega(delivery) is None
    rec = reconciliar(None, [("a.csv", "abc")])
    assert rec.status == "AUSENTE"


def test_reconciliar_divergencia_hash_e_faltando(tmp_path):
    delivery = _delivery_tree(tmp_path, com_manifesto=True, hash_errado=True)
    dm = ler_manifesto_entrega(delivery)
    # csv casa; sql tem hash errado; declara um terceiro que não existe
    dm.hashes["inexistente.csv"] = "f" * 64
    encontrados = [
        ("01_ENTRADA_COPIADA/dados.csv", _sha256(delivery / "01_ENTRADA_COPIADA/dados.csv")),
        ("01_ENTRADA_COPIADA/extracao.sql", _sha256(delivery / "01_ENTRADA_COPIADA/extracao.sql")),
    ]
    rec = reconciliar(dm, encontrados)
    assert rec.status == "PRESENTE_COM_DIVERGENCIA"
    assert "extracao.sql" in rec.hash_divergente
    assert "inexistente.csv" in rec.faltando


# ── Motor de Start com --delivery ────────────────────────────────────────────

@pytest.fixture
def cfg(env_vars, workspace):
    return get_config()


def test_motor_start_com_delivery_classifica_e_reconcilia(cfg, workspace, tmp_path):
    delivery = _delivery_tree(tmp_path, com_manifesto=True)
    manifest = MotorStart(cfg).run("MOD_X", 1, delivery_dir=delivery)

    por_nome = {f.name: f for f in manifest.input_files}
    assert por_nome["dados.csv"].categoria == "analisavel"
    assert por_nome["dados.csv"].tipo == "csv"
    assert por_nome["extracao.sql"].categoria == "analisavel"
    assert por_nome["intake.log"].categoria == "metadados"
    assert por_nome["metadados.json"].categoria == "metadados"

    assert manifest.delivery_manifest_status == "PRESENTE_OK"

    mp = workspace / "cycles" / manifest.cycle_id / "manifest.md"
    content = mp.read_text(encoding="utf-8")
    assert "## Arquivos para Análise" in content
    assert "## Metadados / Manifesto de Entrega" in content
    assert "## Reconciliação com Manifesto de Entrega" in content
    assert "PRESENTE_OK" in content


def test_motor_start_sem_manifesto_entrega_abre_normalmente(cfg, workspace, tmp_path):
    delivery = _delivery_tree(tmp_path, com_manifesto=False)
    manifest = MotorStart(cfg).run("MOD_X", 1, delivery_dir=delivery)
    assert manifest.delivery_manifest_status == "AUSENTE"
    # ciclo abre mesmo sem manifesto de entrega (best-effort)
    assert (workspace / "cycles" / manifest.cycle_id / "manifest.md").exists()
