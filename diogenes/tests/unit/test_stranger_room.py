"""tests/unit/test_stranger_room.py"""
from __future__ import annotations
from pathlib import Path
import pytest
from diogenes.config import get_config
from diogenes.models import DecisaoFinal
from diogenes.orchestrator.stranger_room import StrangerRoom
from diogenes.orchestrator.exceptions import StrangerRoomWriteError, StrangerRoomValidationError


@pytest.fixture
def sr(env_vars, workspace):
    cfg = get_config()
    sr_dir = workspace / "cycles" / "MOD_010_A1_TEST" / "stranger_room"
    sr_dir.mkdir(parents=True)
    return StrangerRoom("MOD_010_A1_TEST", sr_dir, cfg)


class TestStrangerRoom:

    def test_escrever_apresentacao(self, sr):
        path = sr.escrever_apresentacao("watson_integridade", "watson", "Conteúdo de análise")
        assert path.name == "01_apresentacao.md"
        assert path.exists()

    def test_frontmatter_preenchido(self, sr):
        import frontmatter
        sr.escrever_apresentacao("watson_integridade", "watson", "Conteúdo")
        post = frontmatter.load(str(sr._path_para("watson_integridade", "apresentacao")))
        assert post["cycle_id"] == "MOD_010_A1_TEST"
        assert post["author"] == "watson"
        assert post["role"] == "Auditor de Integridade Técnica"
        assert post["has_critical_alert"] is None  # null para apresentacao

    def test_imutabilidade_artigo11(self, sr):
        sr.escrever_apresentacao("watson_integridade", "watson", "Conteúdo 1")
        with pytest.raises(StrangerRoomWriteError):
            sr.escrever_apresentacao("watson_integridade", "watson", "Conteúdo 2")

    def test_critica_e_resposta(self, sr):
        sr.escrever_apresentacao("watson_integridade", "watson", "Análise")
        sr.escrever_critica("watson_integridade", 1, "mycroft", "Ponto 1: revisar X")
        sr.escrever_resposta("watson_integridade", 1, "watson", "Revisado: X corrigido")
        arquivos = sr.listar_arquivos_fase("watson_integridade")
        nomes = [p.name for p in arquivos]
        assert "01_apresentacao.md" in nomes
        assert "02_critica_mycroft_r1.md" in nomes
        assert "03_resposta_r1.md" in nomes

    def test_decisao_final_com_alerta_critico(self, sr):
        sr.escrever_apresentacao("watson_integridade", "watson", "Análise")
        decisao = DecisaoFinal(
            texto="Decisão final — alerta crítico confirmado",
            mycroft_overruled=False,
            has_critical_alert=True,
            critical_alerts_count=2,
            has_dilemma=False,
            dilemmas_count=0,
        )
        path = sr.escrever_decisao_final("watson_integridade", "mycroft", decisao)
        assert path.name == "99_decisao_final.md"

        import frontmatter
        post = frontmatter.load(str(path))
        assert post["has_critical_alert"] is True
        assert post["critical_alerts_count"] == 2
        assert post["mycroft_overruled"] is False

    def test_ler_decisao_final(self, sr):
        sr.escrever_apresentacao("watson_integridade", "watson", "Análise")
        decisao_orig = DecisaoFinal(
            texto="Decisão", mycroft_overruled=True,
            has_critical_alert=False, critical_alerts_count=0,
            has_dilemma=False, dilemmas_count=0,
        )
        sr.escrever_decisao_final("watson_integridade", "mycroft", decisao_orig)
        lida = sr.ler_decisao_final("watson_integridade")
        assert lida.mycroft_overruled is True
        assert lida.has_critical_alert is False

    def test_validar_fase_completa_ok(self, sr):
        sr.escrever_apresentacao("watson_integridade", "watson", "A")
        decisao = DecisaoFinal("D", False, False, 0, False, 0)
        sr.escrever_decisao_final("watson_integridade", "mycroft", decisao)
        sr.validar_fase_completa("watson_integridade")  # não deve levantar

    def test_validar_fase_incompleta_levanta_erro(self, sr):
        sr.escrever_apresentacao("watson_integridade", "watson", "A")
        # Sem decisao_final
        with pytest.raises(StrangerRoomValidationError):
            sr.validar_fase_completa("watson_integridade")
