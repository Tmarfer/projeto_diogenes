# /// script
# requires-python = ">=3.11"
# dependencies = ["python-docx>=1.1.0"]
# ///
"""
tcu_docx_lib.py — Shim de compatibilidade
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Re-exporta o `tcu_formatter.py` com a API antiga do `tcu_docx_lib`, sem
modificar o tcu_formatter. Permite que scripts legados (ex.: motor v3)
continuem importando `from tcu_docx_lib import ...` enquanto o projeto
migra para a nova biblioteca.

Símbolos legados re-expostos:
  - Constantes: CORES, FONT_NAME, FONT_MONO, CRITICIDADE_COR, COR_FUNDO
  - Caminhos:   LOGO_TCU, PROJETO_ROOT, LIB_DIR
  - Helpers:    _set_cell_shading, _set_cell_font, _set_cell_margins
  - Utilitário: mes_ano(), _MESES
  - Classe:     TCUDocx (alias para TCUFormatter)
  - Validação:  validar_documento()

Restrições do usuário:
  - tcu_formatter.py NÃO é modificado.
  - LOGO_TCU aponta para `logo_tcu_extracted.png` na MESMA pasta do script.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

from datetime import datetime
from pathlib import Path

from tcu_formatter import (
    COR_FUNDO,
    CORES,
    CRITICIDADE_COR,
    FONT_MONO,
    FONT_NAME,
    TCUFormatter,
    _set_cell_font,
    _set_cell_margins,
    _set_cell_shading,
    validar_documento,
)

# Alias de compatibilidade: motor v3 importa TCUDocx, mas usa apenas
# constantes/helpers do módulo (não instancia métodos divergentes).
TCUDocx = TCUFormatter

# Caminhos (replicam a convenção do tcu_docx_lib original)
LIB_DIR = Path(__file__).resolve().parent
# Logo na mesma pasta do script (restrição do usuário)
LOGO_TCU = LIB_DIR / "logo_tcu_extracted.png"
# 01-BIBLIOTECAS_UTILITARIAS → UTILITARIOS → 4-SCRIPTS_PROCESSAMENTO → raiz
PROJETO_ROOT = LIB_DIR.parent.parent.parent

# Utilitário de data em português
_MESES = {
    1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril",
    5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
    9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro",
}


def mes_ano():
    """Retorna mês e ano em português (ex: 'Maio de 2026')."""
    now = datetime.now()
    return f"{_MESES[now.month]} de {now.year}"


__all__ = [
    "CORES",
    "FONT_NAME",
    "FONT_MONO",
    "CRITICIDADE_COR",
    "COR_FUNDO",
    "_set_cell_shading",
    "_set_cell_font",
    "_set_cell_margins",
    "TCUDocx",
    "TCUFormatter",
    "LOGO_TCU",
    "LIB_DIR",
    "PROJETO_ROOT",
    "mes_ano",
    "_MESES",
    "validar_documento",
]
