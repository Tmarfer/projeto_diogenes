"""
orchestrator/states.py — DVA-CBS | Projeto Diógenes
Enum CycleState e mapa explícito de transições válidas.

O Orquestrador é uma máquina de estados: toda mudança de fase é uma
transição validada contra TRANSICOES_VALIDAS. Transições inválidas
levantam InvalidTransitionError — por construção, nunca ocorrem em
fluxo normal, mas protegem contra bugs de implementação.

Referência normativa: RF-OR-11 (PRD v0.1), Bloco 8.2 (SDD v0.1)
"""

from __future__ import annotations

from enum import StrEnum


class CycleState(StrEnum):
    # Progressão normal
    PREPARADO                              = "PREPARADO"
    AGUARDANDO_CONFIRMACAO_MANIFESTO       = "AGUARDANDO_CONFIRMACAO_MANIFESTO"
    # Estados do Irene (SDD Bloco 15 / INTEGRACAO_DIOGENES.md seção 6)
    # Inseridos entre AGUARDANDO_CONFIRMACAO_MANIFESTO e EM_EXECUCAO_WATSON.
    VERIFICANDO_EXISTENCIA                 = "VERIFICANDO_EXISTENCIA"   # Mycroft decide se Irene precisa rodar
    AGUARDANDO_IRENE                       = "AGUARDANDO_IRENE"          # pipeline Irene em execução (C1-C5)
    IRENE_CONCLUIDA                        = "IRENE_CONCLUIDA"           # catálogo disponível; Orquestrador retoma
    EM_EXECUCAO_WATSON                     = "EM_EXECUCAO_WATSON"
    AGUARDANDO_REVISAO_MYCROFT_WATSON      = "AGUARDANDO_REVISAO_MYCROFT_WATSON"
    AGUARDANDO_DECISAO_LESTRADE_ALERTA     = "AGUARDANDO_DECISAO_LESTRADE_ALERTA_CRITICO"
    EM_EXECUCAO_SHERLOCK                   = "EM_EXECUCAO_SHERLOCK"
    AGUARDANDO_REVISAO_MYCROFT_SHERLOCK    = "AGUARDANDO_REVISAO_MYCROFT_SHERLOCK"
    # Estado de espera quando sherlock_consolidado.md está incompleto (faltam seções 10.x)
    # Lestrade é notificado; Mycroft.consolidar() só é acionado após completude confirmada
    AGUARDANDO_COMPLETUDE                  = "AGUARDANDO_COMPLETUDE"
    AGUARDANDO_VERIFICACAO_SAIDA           = "AGUARDANDO_VERIFICACAO_SAIDA"
    AGUARDANDO_CHANCELA_LESTRADE           = "AGUARDANDO_CHANCELA_LESTRADE"
    # Fase de Entrega — excursão a partir de AGUARDANDO_CHANCELA_LESTRADE.
    # Mycroft localiza dados (mapa de extração) → Motor de Entrega gera os
    # entregáveis → Mycroft avalia aderência (QA). Retorna à chancela para o seal.
    EM_EXECUCAO_ENTREGA                    = "EM_EXECUCAO_ENTREGA"
    AGUARDANDO_AJUSTE_ENTREGA              = "AGUARDANDO_AJUSTE_ENTREGA"
    ENCERRADO_CHANCELADO                   = "ENCERRADO_CHANCELADO"
    # Interrupção
    PAUSADO_LESTRADE                       = "PAUSADO_LESTRADE"
    ABORTADO_FALHA_AGENTE                  = "ABORTADO_FALHA_AGENTE"
    ABORTADO_LESTRADE                      = "ABORTADO_LESTRADE"


TRANSICOES_VALIDAS: dict[CycleState, set[CycleState]] = {
    CycleState.PREPARADO: {
        CycleState.AGUARDANDO_CONFIRMACAO_MANIFESTO,
        CycleState.ABORTADO_LESTRADE,
    },
    CycleState.AGUARDANDO_CONFIRMACAO_MANIFESTO: {
        CycleState.VERIFICANDO_EXISTENCIA,  # novo fluxo via Irene
        CycleState.EM_EXECUCAO_WATSON,      # fluxo legado / bypass Irene
        CycleState.ABORTADO_LESTRADE,
    },
    CycleState.VERIFICANDO_EXISTENCIA: {
        CycleState.AGUARDANDO_IRENE,         # manifesto válido → executa Irene
        CycleState.EM_EXECUCAO_WATSON,       # catálogo existente reutilizável → pula Irene
        CycleState.ABORTADO_LESTRADE,
    },
    CycleState.AGUARDANDO_IRENE: {
        CycleState.IRENE_CONCLUIDA,          # IRENE_APROVADO ou IRENE_ALERTA ou IRENE_BLOQUEADO
        CycleState.ABORTADO_FALHA_AGENTE,    # IRENE_ERRO_FATAL
        CycleState.ABORTADO_LESTRADE,
    },
    CycleState.IRENE_CONCLUIDA: {
        CycleState.EM_EXECUCAO_WATSON,       # fluxo normal (APROVADO, ALERTA ou BLOQUEADO — Watson pondera)
        CycleState.ABORTADO_FALHA_AGENTE,    # fallback para erros não tratados
        CycleState.ABORTADO_LESTRADE,
    },
    CycleState.EM_EXECUCAO_WATSON: {
        CycleState.AGUARDANDO_REVISAO_MYCROFT_WATSON,
        CycleState.PAUSADO_LESTRADE,           # consolidação em fallback determinístico
        CycleState.ABORTADO_FALHA_AGENTE,
        CycleState.ABORTADO_LESTRADE,
    },
    CycleState.AGUARDANDO_REVISAO_MYCROFT_WATSON: {
        CycleState.EM_EXECUCAO_WATSON,         # Mycroft questiona → Watson responde
        CycleState.AGUARDANDO_DECISAO_LESTRADE_ALERTA,
        CycleState.EM_EXECUCAO_SHERLOCK,       # sem alerta crítico → segue
        CycleState.ABORTADO_FALHA_AGENTE,
        CycleState.ABORTADO_LESTRADE,
    },
    CycleState.AGUARDANDO_DECISAO_LESTRADE_ALERTA: {
        CycleState.EM_EXECUCAO_SHERLOCK,       # Lestrade autoriza
        CycleState.PAUSADO_LESTRADE,
        CycleState.ABORTADO_LESTRADE,
    },
    CycleState.EM_EXECUCAO_SHERLOCK: {
        CycleState.AGUARDANDO_REVISAO_MYCROFT_SHERLOCK,
        CycleState.PAUSADO_LESTRADE,           # validação/consolidação em fallback determinístico
        CycleState.ABORTADO_FALHA_AGENTE,
        CycleState.ABORTADO_LESTRADE,
    },
    CycleState.AGUARDANDO_REVISAO_MYCROFT_SHERLOCK: {
        CycleState.EM_EXECUCAO_SHERLOCK,       # Mycroft questiona → Sherlock responde
        CycleState.AGUARDANDO_COMPLETUDE,      # relatório incompleto → espera Sherlock completar
        CycleState.AGUARDANDO_VERIFICACAO_SAIDA,
        CycleState.ABORTADO_FALHA_AGENTE,
        CycleState.ABORTADO_LESTRADE,
    },
    CycleState.AGUARDANDO_COMPLETUDE: {
        CycleState.AGUARDANDO_VERIFICACAO_SAIDA,  # após Sherlock completar as seções faltantes
        CycleState.ABORTADO_LESTRADE,
    },
    CycleState.AGUARDANDO_VERIFICACAO_SAIDA: {
        CycleState.AGUARDANDO_CHANCELA_LESTRADE,
        CycleState.ABORTADO_LESTRADE,
    },
    CycleState.AGUARDANDO_CHANCELA_LESTRADE: {
        CycleState.EM_EXECUCAO_ENTREGA,        # excursão opcional: gera entregáveis antes do seal
        CycleState.ENCERRADO_CHANCELADO,
        CycleState.ABORTADO_LESTRADE,
    },
    CycleState.EM_EXECUCAO_ENTREGA: {
        CycleState.AGUARDANDO_CHANCELA_LESTRADE,  # QA aprovou → volta para o seal
        CycleState.AGUARDANDO_AJUSTE_ENTREGA,     # QA reprovou → aguarda ajuste/regeneração
        CycleState.ABORTADO_LESTRADE,
    },
    CycleState.AGUARDANDO_AJUSTE_ENTREGA: {
        CycleState.EM_EXECUCAO_ENTREGA,           # nova rodada de geração
        CycleState.AGUARDANDO_CHANCELA_LESTRADE,  # Lestrade aceita assim mesmo → segue para o seal
        CycleState.ABORTADO_LESTRADE,
    },
    CycleState.PAUSADO_LESTRADE: {
        CycleState.EM_EXECUCAO_WATSON,         # retomada após fallback na consolidação Watson
        CycleState.EM_EXECUCAO_SHERLOCK,       # retomada após alerta crítico ou fallback Sherlock
        CycleState.ABORTADO_LESTRADE,
    },
    # Estados terminais — sem transições de saída
    CycleState.ENCERRADO_CHANCELADO: set(),
    CycleState.ABORTADO_FALHA_AGENTE: set(),
    CycleState.ABORTADO_LESTRADE: set(),
}


class InvalidTransitionError(Exception):
    """Tentativa de transição de estado inválida — indica bug no Orquestrador."""

    def __init__(self, current: CycleState, target: CycleState) -> None:
        valid = ", ".join(s.value for s in TRANSICOES_VALIDAS.get(current, set()))
        super().__init__(
            f"Transição inválida: {current.value} → {target.value}. "
            f"Transições válidas a partir de {current.value}: [{valid}]"
        )
