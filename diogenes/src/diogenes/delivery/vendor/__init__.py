"""
delivery/vendor — loader das bibliotecas TCU vendorizadas.

Os arquivos em vendor/tcu/ usam imports bare (`from tcu_formatter import ...`),
herdados da biblioteca-fonte. Este loader insere a pasta no sys.path e importa
os módulos sob demanda (lazy), para que o pacote diogenes.delivery seja
importável mesmo sem python-docx/matplotlib/playwright instalados — o custo das
dependências pesadas só é pago quando a geração é de fato acionada.
"""
from __future__ import annotations

import sys
from pathlib import Path

_TCU_DIR = Path(__file__).resolve().parent / "tcu"


def _ensure_path() -> None:
    p = str(_TCU_DIR)
    if p not in sys.path:
        sys.path.insert(0, p)


def carregar_formatter():
    """Retorna o módulo tcu_formatter (requer python-docx)."""
    _ensure_path()
    import tcu_formatter  # type: ignore
    return tcu_formatter


def carregar_apendice_gerador():
    """Retorna a classe ApendiceGerador (requer python-docx + matplotlib)."""
    _ensure_path()
    from tcu_apendice_gerador import ApendiceGerador  # type: ignore
    return ApendiceGerador


def carregar_ficha():
    """Retorna o módulo gerar_ficha_sintese_pdf_png (requer playwright + chromium)."""
    _ensure_path()
    import gerar_ficha_sintese_pdf_png  # type: ignore
    return gerar_ficha_sintese_pdf_png
