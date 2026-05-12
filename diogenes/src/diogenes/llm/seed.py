"""llm/seed.py — seed determinística por chamada (SDD Bloco 6.5)"""
from __future__ import annotations
import hashlib


def calcular_seed(seed_base: int, cycle_id: str, phase: str, call_type: str, attempt: int = 0) -> int:
    contexto = f"{cycle_id}:{phase}:{call_type}:{attempt}"
    digest = hashlib.sha256(contexto.encode("utf-8")).hexdigest()
    return (seed_base + int(digest[:8], 16)) % 100_000
