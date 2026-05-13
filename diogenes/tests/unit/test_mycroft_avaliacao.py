"""
tests/unit/test_mycroft_avaliacao.py

Testa o parsing de AvaliacaoMycroft e a persistência da crítica na Stranger's Room.

Contexto do bug: o LLM segue o template do skills.md (heartbeat `avaliar_agente`)
que coloca a crítica em `## Avaliação`, não em `## Pontos para Revisão`.
O parser antigo buscava apenas `## Pontos para Revisão`, resultando em critica = "".
"""
from __future__ import annotations

import frontmatter
import pytest

from diogenes.agents.mycroft import _parsear_avaliacao
from diogenes.config import get_config
from diogenes.orchestrator.stranger_room import StrangerRoom


# ── Outputs realistas do LLM ──────────────────────────────────────────────────

_CRITICA_TEMPLATE_FORMAT = """\
# Avaliação de Output — Watson — Rodada r0
**Módulo:** MOD_010_A1
**Agente avaliado:** Watson — Auditor de Integridade Técnica
**Arquivo avaliado:** 01_apresentacao.md
**Rodada de avaliação:** r0
**Timestamp:** 2026-05-13T17:46:38Z
**resultado:** CRITICA

## Avaliação

**Ponto questionado:** Seção "Alertas por Severidade", alerta W010-003

**O que o output registra:** Watson classifica o desvio no script de extração como ALTA,
indicando impacto relevante na base de cálculo CBS sem evidência de propagação sistêmica.

**Referência ao Registro de Decisão:** Decisão [3] — Watson registrou incerteza quanto
ao alcance do desvio mas optou por ALTA por ausência de confirmação de propagação.

**Por que requer revisão:** O critério de CRITICA exige presença de desvio com potencial
de comprometer a integridade de todo o módulo. A própria Decisão [3] registra que o
script processa 100% das linhas da tabela de arrecadação — ausência de confirmação
de propagação não afasta a hipótese de impacto sistêmico. A classificação ALTA
subestima o risco identificado.

**O que Mycroft espera:** Reclassificação para CRITICA com sustentação evidenciada,
ou sustentação de ALTA com evidência concreta de que a propagação foi descartada.

## Alertas Críticos de Watson / Trace sob Demanda

**Uso 2 — Trace sob demanda:**
**Trace a injetar:** watson_trace_script_extracao.md

## Próximo Passo — Instrução ao Invocador

**resultado:** CRITICA

→ Acionar Watson: resposta_r1 com este arquivo como input de crítica.
→ Após resposta_r1: acionar Mycroft: avaliar_agente (rodada r1).

---
*Documento produzido por: Mycroft Holmes — Auditor Chefe*
"""

_APROVADO_TEMPLATE_FORMAT = """\
# Avaliação de Output — Watson — Rodada r1
**Módulo:** MOD_010_A1
**resultado:** APROVADO

## Avaliação

Output bem fundamentado. Watson sustentou a classificação ALTA com evidência concreta
de que a propagação do desvio foi verificada e descartada via amostragem das linhas
processadas. Decisão [3] atualizada com o argumento adicional. Cobertura de tasks
completa. Localizações precisas.

## Alertas Críticos de Watson / Trace sob Demanda

**Número de alertas CRITICA:** 0

## Próximo Passo — Instrução ao Invocador

**resultado:** APROVADO
→ Acionar Mycroft: montar_pacote_sherlock.
"""

_CRITICA_LEGACY_FORMAT = """\
## Avaliação

QUESTIONAR

## Pontos para Revisão

O alerta W010-005 carece de localização precisa. Indicar arquivo, aba e linha.
"""


# ── Testes de parsing ─────────────────────────────────────────────────────────

class TestParsearAvaliacao:

    def test_critica_template_formato_extrai_tipo_questionar(self):
        av = _parsear_avaliacao(_CRITICA_TEMPLATE_FORMAT)
        assert av.tipo == "QUESTIONAR"

    def test_critica_template_formato_corpo_nao_vazio(self):
        av = _parsear_avaliacao(_CRITICA_TEMPLATE_FORMAT)
        assert len(av.critica) >= 10, (
            f"Crítica deve ter ≥ 10 caracteres, obteve {len(av.critica)!r}"
        )

    def test_critica_template_contem_ponto_questionado(self):
        av = _parsear_avaliacao(_CRITICA_TEMPLATE_FORMAT)
        assert "Ponto questionado" in av.critica

    def test_aprovado_template_formato_tipo_correto(self):
        av = _parsear_avaliacao(_APROVADO_TEMPLATE_FORMAT)
        assert av.tipo == "APROVADO"

    def test_aprovado_template_critica_vazia(self):
        av = _parsear_avaliacao(_APROVADO_TEMPLATE_FORMAT)
        assert av.critica == ""

    def test_critica_legacy_formato_ainda_funciona(self):
        av = _parsear_avaliacao(_CRITICA_LEGACY_FORMAT)
        assert av.tipo == "QUESTIONAR"
        assert len(av.critica) >= 10

    def test_aprovado_legacy_formato(self):
        content = "## Avaliação\n\nAPROVADO\n\nOutput dentro do esperado.\n"
        av = _parsear_avaliacao(content)
        assert av.tipo == "APROVADO"
        assert av.critica == ""

    def test_texto_completo_preservado(self):
        av = _parsear_avaliacao(_CRITICA_TEMPLATE_FORMAT)
        assert av.texto == _CRITICA_TEMPLATE_FORMAT


# ── Teste de persistência na Stranger's Room ─────────────────────────────────

class TestCriticaGravadaComCorpo:
    """Garante que o corpo da crítica tem ≥ 10 chars após escrever_critica."""

    @pytest.fixture
    def sr(self, env_vars, workspace):
        cfg = get_config()
        sr_dir = workspace / "cycles" / "MOD_010_A1_BUG" / "stranger_room"
        sr_dir.mkdir(parents=True)
        return StrangerRoom("MOD_010_A1_BUG", sr_dir, cfg)

    def test_critica_r1_corpo_nao_vazio(self, sr):
        av = _parsear_avaliacao(_CRITICA_TEMPLATE_FORMAT)
        path = sr.escrever_critica("watson_integridade", 1, "mycroft", av.critica)

        post = frontmatter.load(str(path))
        assert len(post.content) >= 10, (
            f"Corpo da crítica gravada deve ter ≥ 10 caracteres, "
            f"obteve hash {post['content_hash']!r} e conteúdo {post.content!r}"
        )

    def test_critica_r2_corpo_nao_vazio(self, sr):
        sr.escrever_apresentacao("watson_integridade", "watson", "Análise inicial")
        sr.escrever_resposta("watson_integridade", 1, "watson", "Resposta r1")

        av = _parsear_avaliacao(_CRITICA_TEMPLATE_FORMAT)
        path = sr.escrever_critica("watson_integridade", 2, "mycroft", av.critica)

        post = frontmatter.load(str(path))
        assert len(post.content) >= 10, (
            f"Corpo da crítica r2 deve ter ≥ 10 caracteres, obteve {post.content!r}"
        )

    def test_critica_aprovada_nao_gravada(self, sr):
        """Quando tipo=APROVADO, escrever_critica NÃO deve ser chamado (orquestrador dá break).
        Este teste valida a convenção: critica == "" para APROVADO."""
        av = _parsear_avaliacao(_APROVADO_TEMPLATE_FORMAT)
        assert av.critica == "", "APROVADO não deve produzir texto de crítica"
