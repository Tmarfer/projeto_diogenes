"""llm/exceptions.py — exceções tipadas da camada LLM (SDD Bloco 6.7)"""

class LLMCallError(Exception):
    """Erro não transiente ou retry esgotado."""

class LLMTimeoutError(LLMCallError):
    """Chamada excedeu timeout_segundos."""

class LLMCostLimitError(LLMCallError):
    """Custo acumulado do ciclo atingiu teto_custo_ciclo_usd."""
