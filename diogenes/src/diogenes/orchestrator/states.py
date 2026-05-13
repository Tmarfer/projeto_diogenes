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
    EM_EXECUCAO_WATSON                     = "EM_EXECUCAO_WATSON"
    AGUARDANDO_REVISAO_MYCROFT_WATSON      = "AGUARDANDO_REVISAO_MYCROFT_WATSON"
    AGUARDANDO_DECISAO_LESTRADE_ALERTA     = "AGUARDANDO_DECISAO_LESTRADE_ALERTA_CRITICO"
    EM_EXECUCAO_SHERLOCK                   = "EM_EXECUCAO_SHERLOCK"
    AGUARDANDO_REVISAO_MYCROFT_SHERLOCK    = "AGUARDANDO_REVISAO_MYCROFT_SHERLOCK"
    AGUARDANDO_VERIFICACAO_SAIDA           = "AGUARDANDO_VERIFICACAO_SAIDA"
    AGUARDANDO_CHANCELA_LESTRADE           = "AGUARDANDO_CHANCELA_LESTRADE"
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
        CycleState.EM_EXECUCAO_WATSON,
        CycleState.ABORTADO_LESTRADE,
    },
    CycleState.EM_EXECUCAO_WATSON: {
        CycleState.AGUARDANDO_REVISAO_MYCROFT_WATSON,
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
        CycleState.ABORTADO_FALHA_AGENTE,
        CycleState.ABORTADO_LESTRADE,
    },
    CycleState.AGUARDANDO_REVISAO_MYCROFT_SHERLOCK: {
        CycleState.EM_EXECUCAO_SHERLOCK,       # Mycroft questiona → Sherlock responde
        CycleState.AGUARDANDO_VERIFICACAO_SAIDA,
        CycleState.ABORTADO_FALHA_AGENTE,
        CycleState.ABORTADO_LESTRADE,
    },
    CycleState.AGUARDANDO_VERIFICACAO_SAIDA: {
        CycleState.AGUARDANDO_CHANCELA_LESTRADE,
        CycleState.ABORTADO_LESTRADE,
    },
    CycleState.AGUARDANDO_CHANCELA_LESTRADE: {
        CycleState.ENCERRADO_CHANCELADO,
        CycleState.ABORTADO_LESTRADE,
    },
    CycleState.PAUSADO_LESTRADE: {
        CycleState.EM_EXECUCAO_SHERLOCK,       # retomada após alerta crítico
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
