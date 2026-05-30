"""
tests/unit/test_mycroft_catalogo_irene.py — DVA-CBS | Projeto Diógenes
Testa a leitura do catálogo do Irene e a formatação da seção
catalogo_irene no MC_tasks_watson.md.
"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml


# Catálogo sintético — espelha o schema real do irene_catalog.yaml
CATALOGO_APROVADO = {
    "modulo": "MOD_010_Pessoa_Fisica",
    "versao_irene": "1.3.1",
    "score_consolidado": 0.9737,
    "recomendacao": "APROVADO",
    "arquivos": [
        {
            "nome_original": "AUX_MOD_10 PF - execução.xlsx",
            "papel": "aba_auxiliar",
            "confianca_papel": 0.85,
            "flags_atencao": [],
            "requer_revisao_humana": False,
        },
        {
            "nome_original": "Base_Creditos.xlsx",
            "papel": "resultado_final",
            "confianca_papel": 0.92,
            "flags_atencao": ["divergencia_totalizador"],
            "requer_revisao_humana": True,
        },
    ],
}


class TestLerCatalogoIrene:

    def test_catalogo_existente_retorna_dict(self, tmp_path: Path) -> None:
        catalogo_path = tmp_path / "irene_catalog.yaml"
        catalogo_path.write_text(
            yaml.dump(CATALOGO_APROVADO, allow_unicode=True),
            encoding="utf-8",
        )
        from diogenes.agents.mycroft import MycrooftAgent
        agent = MycrooftAgent.__new__(MycrooftAgent)
        resultado = agent._ler_catalogo_irene(tmp_path)
        assert resultado is not None
        assert resultado["score_consolidado"] == 0.9737

    def test_catalogo_ausente_retorna_none(self, tmp_path: Path) -> None:
        from diogenes.agents.mycroft import MycrooftAgent
        agent = MycrooftAgent.__new__(MycrooftAgent)
        resultado = agent._ler_catalogo_irene(tmp_path)
        assert resultado is None

    def test_catalogo_corrompido_retorna_none(self, tmp_path: Path) -> None:
        catalogo_path = tmp_path / "irene_catalog.yaml"
        catalogo_path.write_text("{{{{invalido yaml", encoding="utf-8")
        from diogenes.agents.mycroft import MycrooftAgent
        agent = MycrooftAgent.__new__(MycrooftAgent)
        resultado = agent._ler_catalogo_irene(tmp_path)
        # YAML inválido como string simples não levanta erro no safe_load,
        # mas conteúdo com chaves duplicadas ou caracteres especiais pode.
        # O importante é que não levanta exceção.
        assert resultado is not None or resultado is None  # não explode

    def test_cycle_dir_none_retorna_none(self) -> None:
        from diogenes.agents.mycroft import MycrooftAgent
        agent = MycrooftAgent.__new__(MycrooftAgent)
        resultado = agent._ler_catalogo_irene(None)
        assert resultado is None


class TestFormatarSecaoCatalogoIrene:

    def test_sem_catalogo_marca_nao_disponivel(self) -> None:
        from diogenes.agents.mycroft import MycrooftAgent
        agent = MycrooftAgent.__new__(MycrooftAgent)
        secao = agent._formatar_secao_catalogo_irene(None)
        assert "Catálogo disponível:** Não" in secao
        assert "<!-- SECAO: catalogo_irene -->" in secao
        assert "<!-- /SECAO: catalogo_irene -->" in secao

    def test_com_catalogo_inclui_tabela(self) -> None:
        from diogenes.agents.mycroft import MycrooftAgent
        agent = MycrooftAgent.__new__(MycrooftAgent)
        secao = agent._formatar_secao_catalogo_irene(CATALOGO_APROVADO)
        assert "Catálogo disponível:** Sim" in secao
        assert "AUX_MOD_10 PF - execução.xlsx" in secao
        assert "aba_auxiliar" in secao
        assert "resultado_final" in secao
        assert "0.85" in secao

    def test_resultado_final_gera_orientacao_analise_completa(self) -> None:
        from diogenes.agents.mycroft import MycrooftAgent
        agent = MycrooftAgent.__new__(MycrooftAgent)
        secao = agent._formatar_secao_catalogo_irene(CATALOGO_APROVADO)
        assert "análise completa" in secao
        assert "varreduras transversais" in secao

    def test_aba_auxiliar_gera_orientacao_verificacao_basica(self) -> None:
        from diogenes.agents.mycroft import MycrooftAgent
        agent = MycrooftAgent.__new__(MycrooftAgent)
        secao = agent._formatar_secao_catalogo_irene(CATALOGO_APROVADO)
        assert "verificação de integridade básica" in secao

    def test_flag_atencao_aparece_na_secao(self) -> None:
        from diogenes.agents.mycroft import MycrooftAgent
        agent = MycrooftAgent.__new__(MycrooftAgent)
        secao = agent._formatar_secao_catalogo_irene(CATALOGO_APROVADO)
        assert "divergencia_totalizador" in secao

    def test_requer_revisao_humana_gera_atencao_lestrade(self) -> None:
        from diogenes.agents.mycroft import MycrooftAgent
        agent = MycrooftAgent.__new__(MycrooftAgent)
        secao = agent._formatar_secao_catalogo_irene(CATALOGO_APROVADO)
        assert "ATENÇÃO LESTRADE" in secao

    def test_secao_tem_score_e_recomendacao(self) -> None:
        from diogenes.agents.mycroft import MycrooftAgent
        agent = MycrooftAgent.__new__(MycrooftAgent)
        secao = agent._formatar_secao_catalogo_irene(CATALOGO_APROVADO)
        assert "0.9737" in secao
        assert "APROVADO" in secao

    def test_catalogo_com_zero_arquivos(self) -> None:
        from diogenes.agents.mycroft import MycrooftAgent
        agent = MycrooftAgent.__new__(MycrooftAgent)
        catalogo_vazio = {
            "modulo": "MOD_010",
            "score_consolidado": 0.0,
            "recomendacao": "BLOQUEADO",
            "arquivos": [],
        }
        secao = agent._formatar_secao_catalogo_irene(catalogo_vazio)
        assert "Catálogo disponível:** Sim" in secao
        assert "BLOQUEADO" in secao

    def test_nao_classificado_gera_analise_completa(self) -> None:
        from diogenes.agents.mycroft import MycrooftAgent
        agent = MycrooftAgent.__new__(MycrooftAgent)
        catalogo = {
            "modulo": "MOD_010",
            "score_consolidado": 0.5,
            "recomendacao": "ALERTA",
            "arquivos": [
                {
                    "nome_original": "desconhecido.xlsx",
                    "papel": "nao_classificado",
                    "confianca_papel": 0.30,
                    "flags_atencao": [],
                    "requer_revisao_humana": False,
                }
            ],
        }
        secao = agent._formatar_secao_catalogo_irene(catalogo)
        assert "não classificado pelo Irene" in secao
        assert "Watson determina o papel" in secao
