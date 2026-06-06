"""
reports/assets.py — DVA-CBS | Projeto Diógenes

Carrega os retratos dos personagens (ilustrações de Sidney Paget, domínio público)
como **data URIs** base64, para que o report.html permaneça um arquivo único e
portátil (princípio local/sem-SaaS — nada de rede ao abrir o painel).

Tolerante a ausência: se o asset não existir, devolve "" e o card cai no avatar
tipográfico de fallback. Ver assets/personagens/CREDITOS.md para atribuição.
"""
from __future__ import annotations

import base64
from functools import lru_cache
from pathlib import Path

_DIR_RETRATOS = Path(__file__).parent / "assets" / "personagens"


@lru_cache(maxsize=16)
def carregar_retrato(nome: str) -> str:
    """Data URI base64 do retrato `nome` (ex.: 'mycroft'); "" se ausente/ilegível."""
    path = _DIR_RETRATOS / f"{nome}.jpg"
    try:
        dados = path.read_bytes()
    except OSError:
        return ""
    if not dados:
        return ""
    b64 = base64.b64encode(dados).decode("ascii")
    return f"data:image/jpeg;base64,{b64}"
