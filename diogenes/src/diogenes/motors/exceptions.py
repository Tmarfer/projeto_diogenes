"""
motors/exceptions.py — DVA-CBS | Projeto Diógenes
Exceções tipadas do Motor de Start (SDD Bloco 7.7).
"""


class MotorStartError(Exception):
    """Classe base para erros do Motor de Start."""


class InputMissingError(MotorStartError):
    """Input obrigatório ausente no diretório de origem."""


class NoPreviousCycleError(MotorStartError):
    """Atividade 2 sem ciclo A1 encerrado correspondente no audit_index."""


class CopyIntegrityError(MotorStartError):
    """Hash diverge após cópia — possível corrupção de filesystem."""


class CycleIdCollisionError(MotorStartError):
    """cycle_id gerado já existe no audit_index."""


class MotorSaidaError(Exception):
    """Ciclo não está no estado correto ou documento de output não encontrado."""
