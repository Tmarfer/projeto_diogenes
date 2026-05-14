"""orchestrator/exceptions.py — exceções do Orquestrador e StrangerRoom"""

class StrangerRoomWriteError(Exception):
    """Tentativa de sobrescrever arquivo imutável da Stranger's Room."""

class StrangerRoomValidationError(Exception):
    """Fase incompleta — arquivos obrigatórios ausentes."""

class OrchestratorError(Exception):
    """Erro irrecuperável no Orquestrador."""

class CorruptedStateError(OrchestratorError):
    """Status do ciclo no audit_index não corresponde a nenhum CycleState
    conhecido — indica corrupção do registro de auditoria. Fail-fast."""

class MotorSaidaError(Exception):
    """Erro no Motor de Saída."""
