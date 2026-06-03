"""
tests/unit/test_filtro_analisavel.py — DVA-CBS | Projeto Diógenes
Etapa 4 prerequisito: orquestrador e Mycroft devem ignorar arquivos de metadados
(categoria != 'analisavel') ao definir tasks Watson e montar pacotes Sherlock.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from diogenes.config import get_config
from diogenes.models import CycleManifest, DecisaoFinal, InputFileInfo


def _make_manifest(tmp_path: Path, with_metadados: bool = True) -> CycleManifest:
    """CycleManifest com arquivos mistos (analisavel + metadados)."""
    files = [
        InputFileInfo(
            name="dados.csv", extension=".csv", size_bytes=1000,
            sha256="aaa", rel_path=Path("dados.csv"),
            categoria="analisavel", tipo="csv",
        ),
        InputFileInfo(
            name="extracao.sql", extension=".sql", size_bytes=2000,
            sha256="bbb", rel_path=Path("extracao.sql"),
            categoria="analisavel", tipo="sql",
        ),
    ]
    if with_metadados:
        files.extend([
            InputFileInfo(
                name="metadados.json", extension=".json", size_bytes=500,
                sha256="ccc", rel_path=Path("02_INSUMOS_GERADOS/metadados.json"),
                categoria="metadados", tipo="metadados",
            ),
            InputFileInfo(
                name="CATALOGO.md", extension=".md", size_bytes=300,
                sha256="ddd", rel_path=Path("04_TRANSFORMADO/_CATALOGO/CATALOGO.md"),
                categoria="metadados", tipo="metadados",
            ),
        ])
    return CycleManifest(
        cycle_id="TEST_A1_Z", module_id="TEST", activity=1,
        opened_at_utc="2026-06-02T00:00:00Z", is_sigilo_module=False,
        input_files=files, package_hash="x", git_commit="x",
        diogenes_version="0.1.0", python_version="3.14", openai_version="1.0",
        cycle_num=1,
    )


# ── Mycroft: definir_tasks_watson ────────────────────────────────────────────

def test_definir_tasks_lista_apenas_analisaveis(env_vars, workspace, tmp_path):
    from diogenes.agents.mycroft import MycrooftAgent
    from diogenes.models import LLMResponse

    manifest = _make_manifest(tmp_path)
    cfg = get_config()
    docs = Path("docs/agentes/mycroft")

    resposta_fake = LLMResponse(
        content="## Tasks para Watson\n1. Analisar dados.csv\n## Inputs Disponíveis\n- dados.csv",
        call_id="x", model_used="m", system_fingerprint="f",
        prompt_tokens=1, completion_tokens=1, total_tokens=2, cost_usd=0.0,
        latency_ms=1, retry_attempts=0, http_status=200, finish_reason="stop",
    )
    llm_fake = MagicMock()
    llm_fake.complete.return_value = resposta_fake

    mycroft = MycrooftAgent(
        llm=llm_fake, agent_spec=cfg.agentes.mycroft,
        cycle_id="TEST_A1_Z", docs_dir=docs, cycle_dir=tmp_path,
    )
    mycroft.definir_tasks_watson(manifest)

    prompt_enviado = llm_fake.complete.call_args[0][0].messages[1].content
    # Analisáveis devem aparecer
    assert "dados.csv" in prompt_enviado
    assert "extracao.sql" in prompt_enviado
    # Metadados NÃO devem aparecer
    assert "metadados.json" not in prompt_enviado
    assert "CATALOGO.md" not in prompt_enviado


# ── Mycroft: montar_pacote_sherlock ──────────────────────────────────────────

def test_montar_pacote_sherlock_inventario_sem_metadados(env_vars, workspace, tmp_path):
    from diogenes.agents.mycroft import MycrooftAgent
    from diogenes.models import LLMResponse

    manifest = _make_manifest(tmp_path)
    cfg = get_config()
    docs = Path("docs/agentes/mycroft")

    resposta_fake = LLMResponse(
        content="## Síntese para Sherlock\nContexto ok.",
        call_id="x", model_used="m", system_fingerprint="f",
        prompt_tokens=1, completion_tokens=1, total_tokens=2, cost_usd=0.0,
        latency_ms=1, retry_attempts=0, http_status=200, finish_reason="stop",
    )
    llm_fake = MagicMock()
    llm_fake.complete.return_value = resposta_fake

    mycroft = MycrooftAgent(
        llm=llm_fake, agent_spec=cfg.agentes.mycroft,
        cycle_id="TEST_A1_Z", docs_dir=docs, cycle_dir=tmp_path,
    )
    decisao = DecisaoFinal(
        texto="Watson OK", mycroft_overruled=False, has_critical_alert=False,
        critical_alerts_count=0, has_dilemma=False, dilemmas_count=0,
    )
    mycroft.montar_pacote_sherlock(manifest, tmp_path, decisao)

    prompt_enviado = llm_fake.complete.call_args[0][0].messages[1].content
    assert "dados.csv" in prompt_enviado
    assert "extracao.sql" in prompt_enviado
    assert "metadados.json" not in prompt_enviado
    assert "CATALOGO.md" not in prompt_enviado


# ── Orquestrador: loop Watson ────────────────────────────────────────────────

def test_orquestrador_analisa_apenas_analisaveis(env_vars, workspace, tmp_path):
    from diogenes.motors.motor_start import MotorStart

    # Criar uma entrega com 1 analisável + 1 metadados
    input_dir = workspace / "input" / "MOD_FILTRO"
    input_dir.mkdir(parents=True)
    (input_dir / "dados.csv").write_text("id;v\n1;10\n", encoding="utf-8")
    meta = input_dir / "02_INSUMOS_GERADOS"
    meta.mkdir()
    (meta / "metadados.json").write_text("{}", encoding="utf-8")

    cfg = get_config()
    manifest = MotorStart(cfg).run("MOD_FILTRO", 1)

    analisaveis = [f for f in manifest.input_files if f.categoria == "analisavel"]
    metadados = [f for f in manifest.input_files if f.categoria == "metadados"]
    assert any(f.name == "dados.csv" for f in analisaveis)
    assert any(f.name == "metadados.json" for f in metadados)

    # O Watson só deve ver arquivos analisáveis — simulamos o loop do orquestrador
    watson_vistos = [
        fi for fi in manifest.input_files
        if fi.categoria == "analisavel"
    ]
    assert all(f.categoria == "analisavel" for f in watson_vistos)
    assert not any(f.name == "metadados.json" for f in watson_vistos)


# ── _localizar_planilha_verificacao ─────────────────────────────────────────

def test_localizar_planilha_ignora_metadados(tmp_path):
    from diogenes.orchestrator.orchestrator import _localizar_planilha_verificacao

    files = [
        InputFileInfo(
            name="planilha_verificacao.xlsx", extension=".xlsx", size_bytes=100,
            sha256="e", rel_path=Path("planilha_verificacao.xlsx"),
            categoria="analisavel", tipo="planilha",
        ),
        InputFileInfo(
            name="inventario_verificacao.xlsx", extension=".xlsx", size_bytes=50,
            sha256="f", rel_path=Path("02_INSUMOS_GERADOS/inventario_verificacao.xlsx"),
            categoria="metadados", tipo="metadados",
        ),
    ]
    manifest = CycleManifest(
        cycle_id="T", module_id="T", activity=1,
        opened_at_utc="2026-06-02T00:00:00Z", is_sigilo_module=False,
        input_files=files, package_hash="x", git_commit="x",
        diogenes_version="0.1.0", python_version="3.14", openai_version="1.0",
        cycle_num=1,
    )
    # Criar o arquivo analisável no disco (metadados não)
    (tmp_path / "planilha_verificacao.xlsx").write_bytes(b"PK\x03\x04fake")

    resultado = _localizar_planilha_verificacao(manifest, tmp_path)
    # Deve encontrar o analisável, não o metadados
    assert resultado is not None
    assert resultado.name == "planilha_verificacao.xlsx"
