"""
tests/unit/test_contexto_metodologico.py — DVA-CBS | Projeto Diógenes
Etapa 3: carregamento da régua metodológica (cat. C) e do corpus jurídico (cat. D)
+ injeção no pacote do Sherlock (montar_pacote_sherlock).
"""
from __future__ import annotations

from pathlib import Path

from diogenes.agents.contexto_metodologico import (
    carregar_corpus_juridico,
    carregar_metodologia_modulo,
)

# ── cat. C: metodologia/RN do módulo ─────────────────────────────────────────

def test_carregar_metodologia_seleciona_e_ignora_ruido(tmp_path):
    inputs = tmp_path / "inputs"
    rn = inputs / "_REGRA_NEGOCIO"
    rn.mkdir(parents=True)
    (rn / "Metodologia_Foco_10.md").write_text("Metodologia do módulo 10.", encoding="utf-8")
    (rn / "RegraDeNegocio_Modulo10.md").write_text("RN-10.01: regra.", encoding="utf-8")
    # ruído que NÃO deve entrar (denylist de dir / sem keyword)
    cat = inputs / "04_TRANSFORMADO" / "_CATALOGO"
    cat.mkdir(parents=True)
    (cat / "CATALOGO.md").write_text("catálogo de abas — ruído", encoding="utf-8")
    (inputs / "leia_me.md").write_text("instruções gerais — ruído", encoding="utf-8")

    doc = carregar_metodologia_modulo(inputs)
    assert "Metodologia do módulo 10" in doc
    assert "RN-10.01" in doc
    assert "catálogo de abas" not in doc   # _CATALOGO está na denylist
    assert "instruções gerais" not in doc  # sem keyword metodológica


def test_carregar_metodologia_dir_inexistente(tmp_path):
    assert carregar_metodologia_modulo(tmp_path / "nao_existe") == ""


# ── cat. D: corpus jurídico curado por módulo ────────────────────────────────

def _make_corpus(root: Path) -> Path:
    base = root / "ARCABOCO" / "normas_para_motor"
    lc = base / "LC_214_LC_227" / "por_modulo"
    cf = base / "CF_88_EC_132" / "por_modulo"
    lc.mkdir(parents=True)
    cf.mkdir(parents=True)
    (lc / "MOD_010.md").write_text("LC 214 — Módulo 10 Pessoa Física.", encoding="utf-8")
    (lc / "MOD_011.md").write_text("LC 214 — Módulo 11 (outro).", encoding="utf-8")
    (lc / "aliquota_referencia.md").write_text("Alíquota de referência (transversal).", encoding="utf-8")
    (lc / "incidencia_base_calculo.md").write_text("Incidência e base de cálculo.", encoding="utf-8")
    (cf / "CONST_010.md").write_text("CF/EC132 — dispositivo do módulo 10.", encoding="utf-8")
    (base / "LC_214_LC_227" / "INDICE.md").write_text("Índice dos módulos.", encoding="utf-8")
    return root / "ARCABOCO"


def test_carregar_corpus_recorte_do_modulo(tmp_path):
    arcaboco = _make_corpus(tmp_path)
    corpus = carregar_corpus_juridico(arcaboco, "MOD_010")
    assert "Módulo 10 Pessoa Física" in corpus       # MOD_010.md
    assert "dispositivo do módulo 10" in corpus       # CONST_010.md
    assert "Alíquota de referência" in corpus         # transversal
    assert "Índice dos módulos" in corpus             # INDICE p/ interseção
    assert "Módulo 11" not in corpus                  # não traz outros módulos inteiros


def test_carregar_corpus_none_e_inexistente(tmp_path):
    assert carregar_corpus_juridico(None, "MOD_010") == ""
    assert carregar_corpus_juridico(tmp_path / "vazio", "MOD_010") == ""


# ── injeção no pacote do Sherlock ────────────────────────────────────────────

class _FakeLLM:
    def complete(self, call):
        from diogenes.models import LLMResponse
        return LLMResponse(
            content="## Síntese para Sherlock\n\nSíntese de contexto (fake).",
            call_id=call.call_id, model_used=call.model, system_fingerprint="fake",
            prompt_tokens=1, completion_tokens=1, total_tokens=2, cost_usd=0.0,
            latency_ms=1, retry_attempts=0, http_status=200, finish_reason="stop",
        )


def test_montar_pacote_injeta_metodologia_e_corpus(env_vars, workspace, tmp_path):
    from diogenes.agents.mycroft import MycrooftAgent
    from diogenes.config import get_config
    from diogenes.models import CycleManifest, DecisaoFinal

    cfg = get_config()
    docs = Path("docs/agentes/mycroft")
    mycroft = MycrooftAgent(
        llm=_FakeLLM(), agent_spec=cfg.agentes.mycroft,
        cycle_id="MOD_010_A1_TESTE", docs_dir=docs, cycle_dir=tmp_path,
    )
    manifest = CycleManifest(
        cycle_id="MOD_010_A1_TESTE", module_id="MOD_010", activity=1,
        opened_at_utc="2026-06-02T00:00:00Z", is_sigilo_module=False,
        input_files=[], package_hash="x", git_commit="x",
        diogenes_version="0.1.0", python_version="3.14", openai_version="1.0",
        cycle_num=1,
    )
    decisao = DecisaoFinal(
        texto="Watson OK", mycroft_overruled=False, has_critical_alert=False,
        critical_alerts_count=0, has_dilemma=False, dilemmas_count=0,
    )
    pacote = mycroft.montar_pacote_sherlock(
        manifest, tmp_path, decisao, watson_apresentacao="análise watson",
        metodologia="METODOLOGIA_DO_MODULO_X", corpus_juridico="CORPUS_JURIDICO_Y",
    )
    assert "## Metodologia e Regra de Negócio do Módulo" in pacote
    assert "METODOLOGIA_DO_MODULO_X" in pacote
    assert "## Arcabouço Jurídico Curado" in pacote
    assert "CORPUS_JURIDICO_Y" in pacote
