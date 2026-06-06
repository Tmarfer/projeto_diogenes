# /// script
# requires-python = ">=3.11"
# dependencies = ["python-docx>=1.1.0"]
# ///
"""
tcu_formatter.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Formatador unificado TCU. Aceita .md OU .docx como entrada e produz um .docx
no padrão institucional do projeto 4-CalculoCBS2027 (TC 015.848/2025-6,
Acórdão 2833/2025-Plenário).

Princípios:
- Não altera o conteúdo textual (preserva exatamente o que o usuário escreveu).
- Não remove imagens.
- Aplica capa, header (com logo, se disponível), rodapé com paginação.
- Converte títulos detectados por padrão regex em Heading 1/2/3.
- Converte bullets em estilo nativo "List Bullet" do Word.
- Remove numeração manual no início de parágrafos ("1. ", "12) ").
- Aplica fonte Aptos, idioma pt-BR, margens TCU.
- Suporta caixas semânticas:
    * add_alerta(criticidade=Crítica|Alta|Média) — para regras de negócio
    * add_destaque(tipo=atencao|positivo|info) — para texto narrativo

Uso:
    python tcu_formatter.py <entrada.md|entrada.docx> <saida.docx> \\
        [--titulo "Título do documento"] [--modulo 10]

Projeto: TC 015.848/2025-6 | SecexContas / TCU
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import argparse
import io
import json
import re
import sys
import unicodedata
from datetime import datetime
from pathlib import Path

_MESES_PT = {
    1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril",
    5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
    9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro",
}


def _mes_ano_pt():
    """Retorna mês e ano em português (ex: 'Maio de 2026')."""
    now = datetime.now()
    return f"{_MESES_PT[now.month]} de {now.year}"

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls, qn
from docx.shared import Cm, Pt, RGBColor

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PALETA TCU (replicada de tcu_docx_lib.py para autonomia)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class CORES:
    NAVY_DEEP = "0B1E2D"
    NAVY_DARK = "162A3A"
    NAVY = "1B3A4B"
    NAVY_MID = "2A5068"
    NAVY_LIGHT = "3D6E8A"
    GOLD = "B8963E"
    GOLD_LIGHT = "D4AE56"
    GOLD_PALE = "EDD98A"
    WHITE = "FFFFFF"
    GRAY = "5A6A74"
    GRAY_LIGHT = "E8EDF0"
    GRAY_MID = "B0BEC5"
    CREAM_LIGHT = "FAF7F0"
    RED = "B83232"
    RED_SOFT = "FEF0EE"
    RED_BORDER = "E8B4AE"
    GREEN = "27604A"
    GREEN_SOFT = "EAF5F0"
    GREEN_BORDER = "A8D5C0"
    AMBER = "9C6E1A"
    AMBER_SOFT = "FDF3DC"
    AMBER_BORDER = "DFC07A"
    BLUE_SOFT = "EAF1F7"
    BLUE_BORDER = "B5CCE0"


CRITICIDADE_COR = {
    "Crítica": CORES.RED,
    "Alta": CORES.AMBER,
    "Média": CORES.NAVY_MID,
}

COR_FUNDO = {
    CORES.RED: CORES.RED_SOFT,
    CORES.AMBER: CORES.AMBER_SOFT,
    CORES.GREEN: CORES.GREEN_SOFT,
    CORES.NAVY_MID: CORES.BLUE_SOFT,
}

DESTAQUE_TIPO = {
    # tipo -> (cor_borda, cor_fundo, rotulo_padrao)
    "atencao":  (CORES.AMBER,    CORES.AMBER_SOFT, "Atenção"),
    "positivo": (CORES.GREEN,    CORES.GREEN_SOFT, "Positivo"),
    "info":     (CORES.NAVY_MID, CORES.BLUE_SOFT,  "Observação"),
}

FONT_NAME = "Aptos"
FONT_MONO = "Aptos Mono"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# STATUS DE AUDITORIA (coloração automática em coluna "Status" de tabelas)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Palavra-chave normalizada → (cor_texto, cor_fundo)
STATUS_KEYWORDS = {
    "DIVERGENCIA":            (CORES.RED,      CORES.RED_SOFT),
    "DIVERGENTE":             (CORES.RED,      CORES.RED_SOFT),
    "ATENDIDO":               (CORES.GREEN,    CORES.GREEN_SOFT),
    "ATENDIDO_PARCIAL":       (CORES.AMBER,    CORES.AMBER_SOFT),
    "ATENDIDO_PARCIALMENTE":  (CORES.AMBER,    CORES.AMBER_SOFT),
    "PARCIAL":                (CORES.AMBER,    CORES.AMBER_SOFT),
    "ATENCAO":                (CORES.AMBER,    CORES.AMBER_SOFT),
    "LIMITACAO":              (CORES.NAVY_MID, CORES.BLUE_SOFT),
    "LIMITACAO_DOCUMENTADA":  (CORES.NAVY_MID, CORES.BLUE_SOFT),
    "NAO_VERIFICAVEL":        (CORES.GRAY,     CORES.GRAY_LIGHT),
    "NAO_VERIFICADO":         (CORES.GRAY,     CORES.GRAY_LIGHT),
}


def _normalizar_status(texto: str) -> str:
    """Normaliza texto para comparação com STATUS_KEYWORDS:
    remove acentos, troca espaços/hífens por _, maiúsculas."""
    if not texto:
        return ""
    s = unicodedata.normalize("NFD", texto)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = s.strip().upper()
    s = re.sub(r"[\s\-]+", "_", s)
    return s


def _classificar_status(texto: str):
    """Retorna (cor_texto, cor_fundo) se o texto bater em alguma palavra-chave
    de status, senão None. Aceita variações ('Atendido Parcialmente', etc.)."""
    if not texto:
        return None
    chave = _normalizar_status(texto)
    if chave in STATUS_KEYWORDS:
        return STATUS_KEYWORDS[chave]
    # Fallback: primeiro token (ex.: "DIVERGENCIA - alta")
    primeiro = chave.split("_")[0] if chave else ""
    if primeiro in STATUS_KEYWORDS:
        return STATUS_KEYWORDS[primeiro]
    return None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# VARIÁVEIS DE TEMPLATE ({{chave}} → valor)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

RE_VARIAVEL = re.compile(r"\{\{\s*([\w\.]+)\s*\}\}")

# Inline markdown: **bold** ou *italic* (não captura ** dentro de palavras)
RE_INLINE_MD = re.compile(r"(\*\*[^*\n]+\*\*|\*[^*\n]+\*)")


def _tokenizar_inline_md(texto: str):
    """Quebra texto em lista de (segmento, bold, italic).
    Reconhece **bold** e *italic*. Texto sem marcadores vira um único token."""
    if not texto or "*" not in texto:
        return [(texto, False, False)]
    tokens = []
    pos = 0
    for m in RE_INLINE_MD.finditer(texto):
        if m.start() > pos:
            tokens.append((texto[pos:m.start()], False, False))
        seg = m.group(0)
        if seg.startswith("**") and seg.endswith("**") and len(seg) >= 4:
            tokens.append((seg[2:-2], True, False))
        elif seg.startswith("*") and seg.endswith("*") and len(seg) >= 2:
            tokens.append((seg[1:-1], False, True))
        else:
            tokens.append((seg, False, False))
        pos = m.end()
    if pos < len(texto):
        tokens.append((texto[pos:], False, False))
    return tokens


def _add_runs_inline_md(p, texto, *, font_name=None, font_size=None,
                        base_bold=False, color_hex=None):
    """Adiciona runs ao parágrafo `p` interpretando **bold** e *italic*.
    Devolve a lista de runs criados (útil para depuração/test)."""
    runs = []
    for seg, bold, italic in _tokenizar_inline_md(texto or ""):
        if not seg:
            continue
        r = p.add_run(seg)
        if font_name:
            r.font.name = font_name
        if font_size is not None:
            r.font.size = font_size
        r.font.bold = bool(base_bold or bold)
        if italic:
            r.font.italic = True
        if color_hex:
            r.font.color.rgb = RGBColor.from_string(color_hex)
        runs.append(r)
    return runs

VARIAVEIS_PADRAO = {
    "processo":     "TC 015.848/2025-6",
    "acordao":      "2833/2025-Plenário",
    "relator":      "Ministro Vital do Rêgo",
    "unidade":      "SecexContas / TCU",
    "lei":          "LC 214/2025",
    "tributo":      "CBS",
    "prazo_rfb":    "30 de junho de 2026",
    "modulo":       "",
    "modulo_nome":  "",
    "reuniao":      "",
}


def _aplicar_variaveis(texto: str, variaveis):
    """Substitui {{chave}} pelo valor correspondente em `variaveis` (dict).
    Chaves não encontradas permanecem intactas (não levantam erro)."""
    if not texto or not variaveis:
        return texto

    def _resolver(match):
        chave = match.group(1)
        valor = variaveis.get(chave)
        if valor is None:
            return match.group(0)
        return str(valor)

    return RE_VARIAVEL.sub(_resolver, texto)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# DETECÇÃO DE TÍTULOS POR REGEX
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# H1: "Bloco 1:", "Capítulo 2:", "PARTE I", "1. Objetivo" no nível mais alto
RE_H1_BLOCO    = re.compile(r"^(?:Bloco|Capítulo|Parte|PARTE)\s+[IVX0-9]+\s*[:\.\-–]?\s*", re.IGNORECASE)
RE_H1_NUM      = re.compile(r"^\s*[0-9]{1,2}\.\s+[A-ZÁÉÍÓÚÂÊÔÃÕÇ]")
# H2: "1.1 Texto", "10.2. Texto", "A.1 Texto" (apêndice)
RE_H2          = re.compile(r"^\s*(?:[0-9]{1,2}\.[0-9]{1,2}|[A-Z]\.[0-9]{1,2})\.?\s+\S")
# H3: "1.1.1 Texto", "A.1.1 Texto"
RE_H3          = re.compile(r"^\s*(?:[0-9]{1,2}\.[0-9]{1,2}\.[0-9]{1,2}|[A-Z]\.[0-9]{1,2}\.[0-9]{1,2})\.?\s+\S")

# Numeração manual no início — "1. ", "12) ", "(3) "
RE_NUMERACAO_MANUAL = re.compile(r"^\s*(?:\(?\d{1,3}[\.\)]\s+)")

# Bullets em texto bruto (markdown ou copiado)
RE_BULLET_PREFIX = re.compile(r"^\s*[•\-\*◦‣]\s+")

# Regra de negócio: "RN-10.01 ", "RG-3.2 "
RE_REGRA_ID = re.compile(r"^\s*((?:RN|RG|RT|RC|RP)[-–—]?\s*[0-9\.]+)\s+(.*)$")


def detectar_nivel_heading(texto: str) -> int:
    """Retorna 1, 2, 3 ou 0 (não é heading)."""
    s = texto.strip()
    if not s or len(s) > 200:
        return 0
    if RE_H3.match(s):
        return 3
    if RE_H2.match(s):
        return 2
    if RE_H1_BLOCO.match(s):
        return 1
    return 0


def detectar_nivel_heading_para(para, texto: str) -> int:
    """
    Detecta heading combinando regex + estilo nativo + tamanho de fonte.
    Cobre o caso de títulos de seção sem prefixo numérico (ex.: "Leilão e Outorga ...").
    """
    nivel = detectar_nivel_heading(texto)
    if nivel:
        return nivel
    if not texto or len(texto) > 150:
        return 0
    # Estilo nativo do Word
    try:
        nome = para.style.name if para.style else ""
        if nome in ("Heading 1", "Title"):
            return 1
        if nome == "Heading 2":
            return 2
        if nome == "Heading 3":
            return 3
    except Exception:
        pass
    # Heurística de tamanho de fonte
    sz_max = 0
    for r in para.runs:
        if r.font.size:
            try:
                sz_max = max(sz_max, r.font.size.pt)
            except Exception:
                pass
    # Bold ajuda a confirmar
    bold_any = any(r.font.bold for r in para.runs)
    if sz_max >= 16 and len(texto) <= 120:
        return 1
    if sz_max >= 14 and len(texto) <= 100 and bold_any:
        return 2
    if sz_max >= 13 and len(texto) <= 80 and bold_any:
        return 3
    return 0


def _eh_lista_nativa(para) -> bool:
    """True se o parágrafo é item de lista nativa (estilo List* ou w:numPr)."""
    try:
        if para.style and para.style.name and "List" in para.style.name:
            return True
    except Exception:
        pass
    pPr = para._p.find(qn('w:pPr'))
    if pPr is not None and pPr.find(qn('w:numPr')) is not None:
        return True
    return False


def _extrair_shading_celula(cell):
    """Retorna a cor de fundo (HEX uppercase, sem #) ou None."""
    try:
        tcPr = cell._tc.find(qn('w:tcPr'))
        if tcPr is None:
            return None
        shd = tcPr.find(qn('w:shd'))
        if shd is None:
            return None
        fill = shd.get(qn('w:fill'))
        if fill and fill.lower() != 'auto':
            return fill.upper()
    except Exception:
        pass
    return None


# Mapa exato (paleta TCU suave) — primeiro nível de detecção.
COR_PARA_TIPO_DESTAQUE = {
    CORES.RED_SOFT.upper():    "atencao",
    CORES.AMBER_SOFT.upper():  "atencao",
    CORES.GREEN_SOFT.upper():  "positivo",
    CORES.BLUE_SOFT.upper():   "info",
    CORES.CREAM_LIGHT.upper(): "info",
    CORES.GRAY_LIGHT.upper():  "info",
}


def _classificar_cor_por_familia(cor_hex):
    """
    Classifica uma cor HEX (sem #) por família de matiz para mapear a
    caixas semânticas. Cobre cores saturadas usadas em DOCX externos
    (ex.: BA7517 laranja, D85A30 vermelho, 1D9E75 verde, 534AB7 roxo,
    26215C navy escuro).

    Retorna "atencao" | "positivo" | "info" | None.
    """
    if not cor_hex or len(cor_hex) != 6:
        return None
    try:
        r = int(cor_hex[0:2], 16)
        g = int(cor_hex[2:4], 16)
        b = int(cor_hex[4:6], 16)
    except ValueError:
        return None
    # Cores praticamente brancas/cinzas neutras → info (caixa neutra)
    max_c = max(r, g, b)
    min_c = min(r, g, b)
    if max_c - min_c < 20 and max_c > 220:
        return "info"  # quase branco
    if max_c - min_c < 20:
        return "info"  # cinza neutro
    # Verde dominante (atendido/positivo)
    if g > r + 15 and g > b + 5:
        return "positivo"
    # Vermelho/laranja/âmbar dominante (atenção)
    if r > g + 15 and r > b + 15:
        return "atencao"
    # Azul/roxo/navy dominante (info)
    if b >= r - 10 and b > g:
        return "info"
    # Amarelo (R≈G alto, B baixo) → atencao
    if r > 150 and g > 120 and b < 100 and abs(r - g) < 60:
        return "atencao"
    return None


def _eh_caixa_destaque(tabela_src):
    """
    Heurística: tabela com 1-2 linhas e poucas células, cuja primeira célula
    tem fundo colorido, é tratada como caixa narrativa (e não como dado
    tabular). Retorna (tipo, texto) ou None.

    Detecção em duas camadas:
    1. Mapa exato da paleta TCU suave (COR_PARA_TIPO_DESTAQUE).
    2. Classificação por família de matiz (R/G/B dominante) para cobrir
       caixas com cores saturadas vindas de outros templates.
    """
    rows = list(tabela_src.rows)
    if not rows or len(rows) > 2:
        return None
    total_celulas = sum(len(r.cells) for r in rows)
    if total_celulas > 4:
        return None
    primeira = rows[0].cells[0]
    cor = _extrair_shading_celula(primeira)
    if not cor:
        return None
    tipo = COR_PARA_TIPO_DESTAQUE.get(cor)
    if not tipo:
        tipo = _classificar_cor_por_familia(cor)
    if not tipo:
        return None
    partes = []
    for row in rows:
        for cell in row.cells:
            t = cell.text.strip()
            if t and t not in partes:
                partes.append(t)
    texto = " ".join(partes).strip()
    if not texto:
        return None
    return (tipo, texto)


# Detecta linhas de data isoladas que pertencem à capa
RE_DATA_CAPA = re.compile(
    r"^\s*(?:"
    r"(?:janeiro|fevereiro|mar[çc]o|abril|maio|junho|julho|agosto|"
    r"setembro|outubro|novembro|dezembro)\s+(?:de\s+)?\d{4}"
    r"|"
    r"\d{1,2}\s*/\s*\d{4}"
    r"|"
    r"\d{1,2}\s+de\s+(?:janeiro|fevereiro|mar[çc]o|abril|maio|junho|julho|"
    r"agosto|setembro|outubro|novembro|dezembro)\s+de\s+\d{4}"
    r")\s*$",
    re.IGNORECASE,
)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# UTILITÁRIOS DE CÉLULAS (tabelas)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _set_cell_shading(cell, color_hex):
    shading = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{color_hex}" w:val="clear"/>')
    cell._tc.get_or_add_tcPr().append(shading)


def _set_cell_font(cell, text, font_name=FONT_NAME, size=Pt(11), bold=False,
                   color_hex=None, alignment=WD_ALIGN_PARAGRAPH.LEFT):
    cell.text = ""
    p = cell.paragraphs[0]
    p.alignment = alignment
    pf = p.paragraph_format
    pf.space_before = Pt(3)
    pf.space_after = Pt(3)
    pf.line_spacing_rule = WD_LINE_SPACING.SINGLE
    pf.left_indent = Cm(0)
    pf.first_line_indent = Cm(0)
    _add_runs_inline_md(
        p, str(text),
        font_name=font_name, font_size=size,
        base_bold=bold, color_hex=color_hex,
    )


def _set_cell_margins(cell, top=40, bottom=40, left=80, right=80):
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    tcMar = parse_xml(
        f'<w:tcMar {nsdecls("w")}>'
        f'  <w:top w:w="{top}" w:type="dxa"/>'
        f'  <w:bottom w:w="{bottom}" w:type="dxa"/>'
        f'  <w:left w:w="{left}" w:type="dxa"/>'
        f'  <w:right w:w="{right}" w:type="dxa"/>'
        f'</w:tcMar>'
    )
    tcPr.append(tcMar)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CLASSE PRINCIPAL: TCUFormatter
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TCUFormatter:
    """
    Construtor de DOCX no padrão TCU. Pode ser usado:
    - Programaticamente: instanciar e chamar add_*
    - Como reformatador: format_docx(input, output) ou format_md(input, output)
    """

    def __init__(self, modulo=None, texto_footer=None, logo_path=None,
                 titulo=None, processo="TC 015.848/2025-6", subtitulo=None):
        self.document = Document()
        self._modulo = modulo
        self._texto_footer = texto_footer
        self._subtitulo = subtitulo
        self._logo_path = Path(logo_path) if logo_path else None
        if not self._logo_path:
            # Buscar logo em locais conhecidos do projeto (cross-platform)
            _candidatos_logo = [
                Path(__file__).resolve().parent / "logo_tcu_extracted.png",
                Path("/mnt/workspace/output/logo_tcu_extracted.png"),
            ]
            # Tentar detectar raiz do projeto para caminho padrão
            _curr = Path(__file__).resolve().parent
            for _ in range(10):
                _logo_proj = _curr / "8-TEMPLATES_DESIGN" / "COMPONENTES_DOCX" / "src" / "assets" / "logo_tcu.png"
                if _logo_proj.exists():
                    _candidatos_logo.insert(0, _logo_proj)
                    break
                _logo_motor = _curr / "8-TEMPLATES_DESIGN" / "COMPONENTES_DOCX" / "motor_python" / "motor_python" / "logo_tcu_extracted.png"
                if _logo_motor.exists():
                    _candidatos_logo.insert(0, _logo_motor)
                    break
                if _curr.parent == _curr:
                    break
                _curr = _curr.parent
            for _cand in _candidatos_logo:
                if _cand.exists():
                    self._logo_path = _cand
                    break
        self._titulo = titulo
        self._processo = processo

        self._configurar_estilos()
        self._configurar_margens()
        self._adicionar_header()
        self._adicionar_footer()
        self._garantir_estilos_lista()

    # ─── CONFIGURAÇÃO INICIAL ──────────────────────────────────────────────────

    def _configurar_estilos(self):
        style = self.document.styles['Normal']
        font = style.font
        font.name = FONT_NAME
        font.size = Pt(12)
        pf = style.paragraph_format
        pf.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        pf.line_spacing_rule = WD_LINE_SPACING.SINGLE
        pf.space_before = Pt(6)
        pf.space_after = Pt(0)
        pf.first_line_indent = Cm(0)
        pf.left_indent = Cm(0)

        rpr = style.element.get_or_add_rPr()
        lang_elem = parse_xml(
            f'<w:lang {nsdecls("w")} w:val="pt-BR" w:eastAsia="pt-BR" w:bidi="pt-BR"/>'
        )
        rpr.append(lang_elem)

        for hlevel in ['Heading 1', 'Heading 2', 'Heading 3']:
            if hlevel in self.document.styles:
                h_rpr = self.document.styles[hlevel].element.get_or_add_rPr()
                h_lang = parse_xml(
                    f'<w:lang {nsdecls("w")} w:val="pt-BR" w:eastAsia="pt-BR" w:bidi="pt-BR"/>'
                )
                h_rpr.append(h_lang)

        settings_elem = self.document.settings.element
        theme_lang = settings_elem.find(qn('w:themeFontLang'))
        if theme_lang is None:
            theme_lang = parse_xml(f'<w:themeFontLang {nsdecls("w")} w:val="pt-BR"/>')
            settings_elem.append(theme_lang)
        else:
            theme_lang.set(qn('w:val'), 'pt-BR')

    def _configurar_margens(self):
        section = self.document.sections[0]
        section.left_margin = Cm(3)
        section.right_margin = Cm(2.54)
        section.top_margin = Cm(2.54)
        section.bottom_margin = Cm(2.54)

    def _adicionar_header(self):
        """Header no padrão do exemplo: tabela 1x2 (logo + texto) + linha gold."""
        from docx.table import Table as DocxTable

        section = self.document.sections[0]
        header = section.header

        for p in list(header.paragraphs):
            header._element.remove(p._p)

        tem_logo = self._logo_path and Path(self._logo_path).exists()
        if not tem_logo:
            import warnings
            warnings.warn(
                "LOGO TCU NÃO ENCONTRADO. O logo é premissa inegociável do "
                "padrão institucional. Verifique se o arquivo "
                "'logo_tcu.png' ou 'logo_tcu_extracted.png' está disponível "
                "no projeto (8-TEMPLATES_DESIGN/COMPONENTES_DOCX/).",
                stacklevel=2,
            )

        # Tabela invisível: logo (col 1) + texto institucional (col 2)
        tbl_xml = (
            f'<w:tbl {nsdecls("w")}>'
            f'  <w:tblPr>'
            f'    <w:tblW w:w="0" w:type="auto"/>'
            f'    <w:tblBorders>'
            f'      <w:top w:val="none" w:sz="0" w:space="0" w:color="auto"/>'
            f'      <w:left w:val="none" w:sz="0" w:space="0" w:color="auto"/>'
            f'      <w:bottom w:val="none" w:sz="0" w:space="0" w:color="auto"/>'
            f'      <w:right w:val="none" w:sz="0" w:space="0" w:color="auto"/>'
            f'      <w:insideH w:val="none" w:sz="0" w:space="0" w:color="auto"/>'
            f'      <w:insideV w:val="none" w:sz="0" w:space="0" w:color="auto"/>'
            f'    </w:tblBorders>'
            f'  </w:tblPr>'
            f'  <w:tblGrid>'
            f'    <w:gridCol w:w="1200"/>'
            f'    <w:gridCol w:w="7800"/>'
            f'  </w:tblGrid>'
            f'  <w:tr>'
            f'    <w:tc>'
            f'      <w:tcPr><w:tcW w:w="1200" w:type="dxa"/></w:tcPr>'
            f'      <w:p><w:pPr><w:jc w:val="center"/></w:pPr></w:p>'
            f'    </w:tc>'
            f'    <w:tc>'
            f'      <w:tcPr><w:tcW w:w="7800" w:type="dxa"/></w:tcPr>'
            f'      <w:p/>'
            f'    </w:tc>'
            f'  </w:tr>'
            f'</w:tbl>'
        )
        tbl_element = parse_xml(tbl_xml)
        header._element.append(tbl_element)
        tbl = DocxTable(tbl_element, header)

        # Coluna 1: logo
        cell_logo = tbl.rows[0].cells[0]
        p_logo = cell_logo.paragraphs[0]
        p_logo.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_logo.paragraph_format.space_after = Pt(0)
        if tem_logo:
            try:
                run_img = p_logo.add_run()
                run_img.add_picture(str(self._logo_path), width=Cm(1.4))
            except Exception:
                pass

        # Coluna 2: texto institucional
        cell_text = tbl.rows[0].cells[1]
        p_inst = cell_text.paragraphs[0]
        p_inst.paragraph_format.space_after = Pt(0)
        p_inst.paragraph_format.space_before = Pt(2)
        run_titulo = p_inst.add_run("TRIBUNAL DE CONTAS DA UNIÃO")
        run_titulo.font.name = FONT_NAME
        run_titulo.font.size = Pt(11)
        run_titulo.font.bold = True
        run_titulo.font.color.rgb = RGBColor.from_string(CORES.NAVY_DEEP)

        p_seg = cell_text.add_paragraph()
        p_seg.paragraph_format.space_before = Pt(0)
        p_seg.paragraph_format.space_after = Pt(0)
        run_seg = p_seg.add_run("Secretaria Geral de Controle Externo")
        run_seg.font.name = FONT_NAME
        run_seg.font.size = Pt(9)
        run_seg.font.color.rgb = RGBColor.from_string(CORES.GRAY)

        p_sec = cell_text.add_paragraph()
        p_sec.paragraph_format.space_before = Pt(0)
        p_sec.paragraph_format.space_after = Pt(0)
        run_sec = p_sec.add_run("Secretaria de Controle Externo de Contas Públicas")
        run_sec.font.name = FONT_NAME
        run_sec.font.size = Pt(9)
        run_sec.font.color.rgb = RGBColor.from_string(CORES.GRAY)

        # Linha gold
        p_div_xml = parse_xml(
            f'<w:p {nsdecls("w")}>'
            f'  <w:pPr>'
            f'    <w:spacing w:before="80" w:after="0"/>'
            f'    <w:pBdr>'
            f'      <w:bottom w:val="single" w:sz="8" w:space="1" w:color="{CORES.GOLD}"/>'
            f'    </w:pBdr>'
            f'  </w:pPr>'
            f'</w:p>'
        )
        header._element.append(p_div_xml)

    def _adicionar_footer(self):
        # Prioridade: texto explícito > título do documento > módulo simples > fallback.
        # Padrão alinhado ao motor v3 ("GT Reforma Tributária – Módulo 8: Simples Nacional").
        # Normaliza o prefixo institucional para "GT Reforma Tributária" (caixa
        # canônica), ainda que o título da capa esteja em CAPSLOCK.
        PREFIXO = "GT Reforma Tributária"
        footer_text = self._texto_footer or ""
        if not footer_text and self._titulo:
            titulo_rodape = str(self._titulo).strip()
            tit_low = titulo_rodape.lower()
            # Se o título do documento é apenas o nome institucional, usa o
            # subtítulo como complemento (ex.: "GT Reforma Tributária –
            # Estratégia Integrada de Validação da CBS").
            if tit_low in ("gt reforma tributária", "gt reforma tributaria"):
                sub = (self._subtitulo or "").strip()
                if sub:
                    footer_text = f"{PREFIXO} – {sub}"
                else:
                    footer_text = PREFIXO
            elif tit_low.startswith("gt reforma tribut"):
                # Título já contém prefixo institucional: remove e recompõe
                # com a caixa canônica + restante do título original.
                resto = titulo_rodape[len(PREFIXO):].lstrip(" -–—:")
                footer_text = f"{PREFIXO} – {resto}" if resto else PREFIXO
            else:
                footer_text = f"{PREFIXO} – {titulo_rodape}"
        if not footer_text and self._modulo:
            footer_text = f"{PREFIXO} – Módulo {self._modulo}"
        if not footer_text:
            footer_text = PREFIXO

        section = self.document.sections[0]
        footer = section.footer

        for p in list(footer.paragraphs):
            footer._element.remove(p._p)

        p_border_xml = parse_xml(
            f'<w:p {nsdecls("w")}>'
            f'  <w:pPr>'
            f'    <w:spacing w:before="0" w:after="40"/>'
            f'    <w:pBdr>'
            f'      <w:top w:val="single" w:sz="6" w:space="1" w:color="{CORES.GOLD}"/>'
            f'    </w:pBdr>'
            f'  </w:pPr>'
            f'</w:p>'
        )
        footer._element.append(p_border_xml)

        footer_p_xml = parse_xml(
            f'<w:p {nsdecls("w")}>'
            f'  <w:pPr>'
            f'    <w:spacing w:before="0" w:after="0"/>'
            f'    <w:tabs>'
            f'      <w:tab w:val="right" w:pos="9072"/>'
            f'    </w:tabs>'
            f'    <w:rPr>'
            f'      <w:rFonts w:ascii="{FONT_NAME}" w:hAnsi="{FONT_NAME}"/>'
            f'      <w:sz w:val="16"/>'
            f'      <w:color w:val="{CORES.GRAY}"/>'
            f'    </w:rPr>'
            f'  </w:pPr>'
            f'  <w:r>'
            f'    <w:rPr>'
            f'      <w:rFonts w:ascii="{FONT_NAME}" w:hAnsi="{FONT_NAME}"/>'
            f'      <w:sz w:val="16"/>'
            f'      <w:color w:val="{CORES.GRAY}"/>'
            f'    </w:rPr>'
            f'    <w:t xml:space="preserve">{footer_text}</w:t>'
            f'  </w:r>'
            f'  <w:r>'
            f'    <w:rPr>'
            f'      <w:rFonts w:ascii="{FONT_NAME}" w:hAnsi="{FONT_NAME}"/>'
            f'      <w:sz w:val="16"/>'
            f'      <w:color w:val="{CORES.GRAY}"/>'
            f'    </w:rPr>'
            f'    <w:tab/>'
            f'  </w:r>'
            f'  <w:r>'
            f'    <w:rPr>'
            f'      <w:rFonts w:ascii="{FONT_NAME}" w:hAnsi="{FONT_NAME}"/>'
            f'      <w:sz w:val="16"/>'
            f'      <w:color w:val="{CORES.GRAY}"/>'
            f'    </w:rPr>'
            f'    <w:t xml:space="preserve">Página </w:t>'
            f'  </w:r>'
            f'  <w:r>'
            f'    <w:rPr>'
            f'      <w:rFonts w:ascii="{FONT_NAME}" w:hAnsi="{FONT_NAME}"/>'
            f'      <w:sz w:val="16"/>'
            f'      <w:color w:val="{CORES.GRAY}"/>'
            f'    </w:rPr>'
            f'    <w:fldChar w:fldCharType="begin"/>'
            f'  </w:r>'
            f'  <w:r>'
            f'    <w:rPr>'
            f'      <w:rFonts w:ascii="{FONT_NAME}" w:hAnsi="{FONT_NAME}"/>'
            f'      <w:sz w:val="16"/>'
            f'      <w:color w:val="{CORES.GRAY}"/>'
            f'    </w:rPr>'
            f'    <w:instrText xml:space="preserve"> PAGE </w:instrText>'
            f'  </w:r>'
            f'  <w:r>'
            f'    <w:rPr>'
            f'      <w:rFonts w:ascii="{FONT_NAME}" w:hAnsi="{FONT_NAME}"/>'
            f'      <w:sz w:val="16"/>'
            f'      <w:color w:val="{CORES.GRAY}"/>'
            f'    </w:rPr>'
            f'    <w:fldChar w:fldCharType="separate"/>'
            f'  </w:r>'
            f'  <w:r>'
            f'    <w:rPr>'
            f'      <w:rFonts w:ascii="{FONT_NAME}" w:hAnsi="{FONT_NAME}"/>'
            f'      <w:sz w:val="16"/>'
            f'      <w:color w:val="{CORES.GRAY}"/>'
            f'    </w:rPr>'
            f'    <w:t>1</w:t>'
            f'  </w:r>'
            f'  <w:r>'
            f'    <w:rPr>'
            f'      <w:rFonts w:ascii="{FONT_NAME}" w:hAnsi="{FONT_NAME}"/>'
            f'      <w:sz w:val="16"/>'
            f'      <w:color w:val="{CORES.GRAY}"/>'
            f'    </w:rPr>'
            f'    <w:fldChar w:fldCharType="end"/>'
            f'  </w:r>'
            f'</w:p>'
        )
        footer._element.append(footer_p_xml)

    def _garantir_estilos_lista(self):
        """Garante que List Bullet e List Number existam com a fonte correta."""
        for nome in ('List Bullet', 'List Number'):
            if nome in self.document.styles:
                st = self.document.styles[nome]
                st.font.name = FONT_NAME
                st.font.size = Pt(12)

    # ─── CAPA ──────────────────────────────────────────────────────────────────

    def add_capa(self, titulo=None, subtitulo1=None, subtitulo2=None,
                 processo=None, acordao="2833/2025-Plenário",
                 versao=None, fundamentacao=None, data=None,
                 rotulo_fundamentacao="Fundamentação",
                 incluir_legenda_criticidade=False,
                 capa_classica=False):
        """
        Capa institucional no padrão dos exemplos RegraDeNegocio_Modulo10 e
        Metodologia_Foco_10.

        Alinhada à esquerda, com tipografia hierárquica:
        - Título principal:    28pt, bold, navy_deep
        - Subtítulo principal: 18pt, navy
        - Subtítulo secundário: 13pt, navy_mid
        - Linha gold mais grossa (abaixo do subtítulo)
        - Bloco institucional: TCU (11pt bold) + SecexContas (10pt cinza)
        - Bloco processo:      "Processo: / Acórdão: / Versão: ..." (10pt cinza)
        - Fundamentação OU Fonte: linha única, 10pt cinza, SEM bold
        - Legenda de criticidade (opcional): bloco 9pt

        capa_classica=False (padrão): comportamento institucional atual —
            título em CAPSLOCK, blocos institucional/referências agrupados em
            um único parágrafo (quebra leve), versão com sufixo "| Mês de Ano"
            e fundamentação em itálico.
        capa_classica=True: reproduz o padrão original (pré-29/05/2026) usado
            no protocolo de recebimento — título preservando a caixa original,
            cada linha (Tribunal, SecexContas, Processo, Acórdão, Versão) em
            parágrafo próprio, versão sem sufixo e fundamentação sem itálico.
        """
        titulo = titulo or self._titulo or "Documento técnico"
        processo = processo or self._processo

        def _para_left(space_before=0, space_after=0):
            p = self.document.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            pf = p.paragraph_format
            pf.space_before = Pt(space_before)
            pf.space_after = Pt(space_after)
            pf.left_indent = Cm(0)
            pf.first_line_indent = Cm(0)
            return p

        def _run(p, texto, *, size, bold=False, color=CORES.NAVY_DEEP):
            r = p.add_run(texto)
            r.font.name = FONT_NAME
            r.font.size = Pt(size)
            r.font.bold = bold
            r.font.color.rgb = RGBColor.from_string(color)
            return r

        # 1. Título principal (28pt, bold, navy_deep) — CAPSLOCK por padrão
        # (padrão institucional do motor de regras: "REGRAS DE NEGÓCIO").
        # Com capa_classica=True preserva a caixa original do título.
        p1 = _para_left(space_before=48, space_after=4)
        titulo_render = str(titulo) if capa_classica else str(titulo).upper()
        _run(p1, titulo_render, size=28, bold=True, color=CORES.NAVY_DEEP)

        # 2. Subtítulo principal (18pt, navy) — letra normal, NÃO uppercase
        if subtitulo1:
            p2 = _para_left(space_before=0, space_after=2)
            _run(p2, subtitulo1, size=18, color=CORES.NAVY)

        # 3. Subtítulo secundário (13pt, navy_mid) — letra normal
        if subtitulo2:
            p3 = _para_left(space_before=0, space_after=4)
            _run(p3, subtitulo2, size=13, color=CORES.NAVY_MID)

        # 3b. Data da capa (12pt, navy_mid) — logo abaixo do(s) subtítulo(s)
        if data:
            p_data = _para_left(space_before=0, space_after=4)
            _run(p_data, data, size=12, color=CORES.NAVY_MID)

        # 3c. Linha gold como parágrafo SEPARADO (padrão motor v3).
        # Borda no TOPO do parágrafo vazio, com space_after generoso para
        # distanciar visualmente do bloco "Tribunal de Contas da União".
        gold_line = _para_left(space_before=0, space_after=18)
        pPr_gl = gold_line._p.get_or_add_pPr()
        borders_gold = parse_xml(
            f'<w:pBdr {nsdecls("w")}>'
            f'  <w:top w:val="single" w:sz="16" w:space="1" w:color="{CORES.GOLD}"/>'
            f'</w:pBdr>'
        )
        pPr_gl.append(borders_gold)

        # 4. Bloco institucional — TCU + SecexContas.
        # Padrão atual: MESMO parágrafo separados por quebra leve (\n).
        # Clássico: cada linha em parágrafo próprio (padrão do protocolo).
        if capa_classica:
            p_inst1 = _para_left(space_before=18, space_after=0)
            _run(p_inst1, "Tribunal de Contas da União",
                 size=11, bold=True, color=CORES.NAVY_DEEP)
            p_inst2 = _para_left(space_before=14, space_after=0)
            _run(p_inst2,
                 "SecexContas: Secretaria de Controle Externo de Contas Públicas",
                 size=10, color=CORES.GRAY)
        else:
            meta = _para_left(space_before=0, space_after=4)
            _run(meta, "Tribunal de Contas da União",
                 size=11, bold=True, color=CORES.NAVY_DEEP)
            meta.add_run("\n")
            _run(meta,
                 "SecexContas: Secretaria de Controle Externo de Contas Públicas",
                 size=10, color=CORES.GRAY)

        # 5. Bloco de referências — Processo + Acórdão + Versão.
        # Padrão atual: MESMO parágrafo (quebra leve), versão com sufixo
        # " | Mês de Ano". Clássico: cada linha em parágrafo próprio e versão
        # sem sufixo automático.
        versao_str = str(versao) if versao else "Preliminar"
        if not capa_classica and " | " not in versao_str and versao:
            versao_str = f"{versao_str} | {_mes_ano_pt()}"

        if capa_classica:
            p_proc = _para_left(space_before=18, space_after=0)
            _run(p_proc, "Processo: ", size=10, bold=True, color=CORES.GRAY)
            _run(p_proc, str(processo), size=10, color=CORES.GRAY)
            if acordao:
                p_acord = _para_left(space_before=2, space_after=0)
                _run(p_acord, "Acórdão: ", size=10, bold=True, color=CORES.GRAY)
                _run(p_acord, str(acordao), size=10, color=CORES.GRAY)
            p_vers = _para_left(space_before=2, space_after=0)
            _run(p_vers, "Versão: ", size=10, bold=True, color=CORES.GRAY)
            _run(p_vers, versao_str, size=10, color=CORES.GRAY)
        else:
            ref = _para_left(space_before=12, space_after=4)
            _run(ref, "Processo: ", size=10, bold=True, color=CORES.GRAY)
            _run(ref, str(processo), size=10, color=CORES.GRAY)
            if acordao:
                ref.add_run("\n")
                _run(ref, "Acórdão: ", size=10, bold=True, color=CORES.GRAY)
                _run(ref, str(acordao), size=10, color=CORES.GRAY)
            ref.add_run("\n")
            _run(ref, "Versão: ", size=10, bold=True, color=CORES.GRAY)
            _run(ref, versao_str, size=10, color=CORES.GRAY)

        # 6. Fundamentação ou Fonte (linha única, 10pt cinza).
        # Padrão atual: itálico. Clássico: sem itálico.
        if fundamentacao:
            p_fund = _para_left(space_before=8 if not capa_classica else 6,
                                space_after=0)
            rotulo = (rotulo_fundamentacao or "Fundamentação").strip().rstrip(":")
            r_fund = _run(p_fund, f"{rotulo}: {fundamentacao}",
                          size=10, color=CORES.GRAY)
            if not capa_classica:
                r_fund.font.italic = True

        # 7. Legenda de criticidade (opcional)
        if incluir_legenda_criticidade:
            _para_left(space_before=4, space_after=0)
            p_l = _para_left(space_before=0, space_after=2)
            _run(p_l, "LEGENDA DE CRITICIDADE", size=9, bold=True, color=CORES.NAVY_DEEP)

            for rotulo, descr, cor in [
                ("Criticidade Crítica: ",
                 "Falha que invalida o módulo. Exige correção obrigatória antes da aceitação dos dados.",
                 CORES.RED),
                ("Criticidade Alta: ",
                 "Inconsistência relevante que deve ser justificada formalmente pela RFB ou corrigida antes do aceite.",
                 CORES.AMBER),
                ("Criticidade Média: ",
                 "Ponto de atenção a ser documentado. Não impede a aceitação, mas deve constar no relatório de validação.",
                 CORES.NAVY_MID),
            ]:
                p_c = _para_left(space_before=0, space_after=0)
                _run(p_c, rotulo, size=9, bold=True, color=cor)
                _run(p_c, descr, size=9, color=CORES.NAVY)

        self.document.add_page_break()

    # ─── ELEMENTOS DE CORPO ────────────────────────────────────────────────────

    def add_heading(self, texto, level=1):
        """Título padrão TCU: navy + borda dourada (H1) + outlineLvl explícito.
        O outlineLvl garante que o Word exiba a setinha de recolher/expandir
        conteúdo sob o título (Heading 1→0, Heading 2→1, Heading 3→2)."""
        h = self.document.add_heading(texto, level=level)
        for run in h.runs:
            run.font.name = FONT_NAME
            run.font.color.rgb = RGBColor.from_string(
                CORES.NAVY_DEEP if level == 1
                else CORES.NAVY if level == 2
                else CORES.NAVY_MID
            )
        hf = h.paragraph_format
        hf.space_before = Pt(18 if level == 1 else 12)
        hf.space_after = Pt(6)
        hf.left_indent = Cm(0)
        hf.first_line_indent = Cm(0)

        pPr = h._p.get_or_add_pPr()

        # outlineLvl explícito — habilita a setinha de recolher no Word
        outline_val = max(0, min(level - 1, 8))
        for existing in pPr.findall(qn("w:outlineLvl")):
            pPr.remove(existing)
        outline = parse_xml(f'<w:outlineLvl {nsdecls("w")} w:val="{outline_val}"/>')
        pPr.append(outline)

        # Borda inferior dourada para H1
        if level == 1:
            borders = parse_xml(
                f'<w:pBdr {nsdecls("w")}>'
                f'  <w:bottom w:val="single" w:sz="8" w:space="1" w:color="{CORES.GOLD}"/>'
                f'</w:pBdr>'
            )
            pPr.append(borders)
        return h

    def add_paragrafo(self, texto, bold_prefix=None):
        """Parágrafo justificado, SEM numeração manual."""
        p = self.document.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        pf = p.paragraph_format
        pf.line_spacing_rule = WD_LINE_SPACING.SINGLE
        pf.space_before = Pt(6)
        pf.space_after = Pt(0)
        pf.left_indent = Cm(0)
        pf.first_line_indent = Cm(0)
        if bold_prefix:
            bp = p.add_run(bold_prefix)
            bp.font.name = FONT_NAME
            bp.font.size = Pt(12)
            bp.font.bold = True
        _add_runs_inline_md(p, texto, font_name=FONT_NAME, font_size=Pt(12))
        return p

    def add_bullet(self, texto, bold_prefix=None):
        """Bullet usando estilo nativo List Bullet do Word."""
        try:
            p = self.document.add_paragraph(style='List Bullet')
        except KeyError:
            p = self.document.add_paragraph()
        pf = p.paragraph_format
        pf.line_spacing_rule = WD_LINE_SPACING.SINGLE
        pf.space_before = Pt(3)
        pf.space_after = Pt(0)
        pf.left_indent = Cm(1.25)
        pf.first_line_indent = Cm(-0.5)
        if bold_prefix:
            bp = p.add_run(bold_prefix)
            bp.font.name = FONT_NAME
            bp.font.size = Pt(12)
            bp.font.bold = True
        _add_runs_inline_md(p, texto, font_name=FONT_NAME, font_size=Pt(12))
        return p

    def add_alerta(self, prefixo, texto, criticidade="Alta"):
        """Caixa de regra de negócio com borda esquerda colorida (Crítica/Alta/Média).
        Apenas borda lateral esquerda grossa, sem moldura completa."""
        color_hex = CRITICIDADE_COR.get(criticidade, CORES.AMBER)
        bg = COR_FUNDO.get(color_hex, CORES.CREAM_LIGHT)

        p = self.document.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        pf = p.paragraph_format
        pf.line_spacing_rule = WD_LINE_SPACING.SINGLE
        pf.space_before = Pt(3)
        pf.space_after = Pt(3)
        pf.left_indent = Cm(0.5)
        pf.first_line_indent = Cm(0)

        pPr = p._p.get_or_add_pPr()
        borders = parse_xml(
            f'<w:pBdr {nsdecls("w")}>'
            f'  <w:left w:val="single" w:sz="30" w:space="8" w:color="{color_hex}"/>'
            f'</w:pBdr>'
        )
        pPr.append(borders)
        shading = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{bg}" w:val="clear"/>')
        pPr.append(shading)

        run_prefix = p.add_run(prefixo)
        run_prefix.font.name = FONT_MONO
        run_prefix.font.size = Pt(10)
        run_prefix.font.bold = True
        run_prefix.font.color.rgb = RGBColor.from_string(color_hex)

        run_text = p.add_run(f"  {texto}")
        run_text.font.name = FONT_NAME
        run_text.font.size = Pt(11)
        return p

    def add_destaque(self, texto, tipo="info", rotulo=None):
        """Caixa de destaque narrativo (atenção/positivo/info).
        Apenas borda lateral esquerda grossa, sem moldura top/bottom/right,
        colada ao texto para integração visual."""
        cor_borda, cor_fundo, rotulo_padrao = DESTAQUE_TIPO.get(
            tipo, DESTAQUE_TIPO["info"]
        )
        rotulo = rotulo or rotulo_padrao

        p = self.document.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        pf = p.paragraph_format
        pf.line_spacing_rule = WD_LINE_SPACING.SINGLE
        pf.space_before = Pt(3)
        pf.space_after = Pt(3)
        pf.left_indent = Cm(0.3)
        pf.right_indent = Cm(0)
        pf.first_line_indent = Cm(0)

        pPr = p._p.get_or_add_pPr()
        borders = parse_xml(
            f'<w:pBdr {nsdecls("w")}>'
            f'  <w:left w:val="single" w:sz="30" w:space="6" w:color="{cor_borda}"/>'
            f'</w:pBdr>'
        )
        pPr.append(borders)
        shading = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{cor_fundo}" w:val="clear"/>')
        pPr.append(shading)

        run_rot = p.add_run(f"{rotulo}: ")
        run_rot.font.name = FONT_NAME
        run_rot.font.size = Pt(11)
        run_rot.font.bold = True
        run_rot.font.color.rgb = RGBColor.from_string(cor_borda)

        run_t = p.add_run(texto)
        run_t.font.name = FONT_NAME
        run_t.font.size = Pt(11)
        return p

    def add_titulo_elemento(self, texto):
        """Título de tabela ou figura: centralizado, fonte 11, ACIMA do elemento."""
        p = self.document.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        pf = p.paragraph_format
        pf.space_before = Pt(8)
        pf.space_after = Pt(2)
        pf.left_indent = Cm(0)
        pf.first_line_indent = Cm(0)
        run = p.add_run(texto)
        run.font.name = FONT_NAME
        run.font.size = Pt(11)
        run.font.color.rgb = RGBColor.from_string(CORES.NAVY)
        return p

    def add_nota_elemento(self, texto, rotulo="Nota"):
        """Nota abaixo do elemento: alinhada à esquerda, fonte 10, formato limpo."""
        p = self.document.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        pf = p.paragraph_format
        pf.space_before = Pt(2)
        pf.space_after = Pt(8)
        pf.left_indent = Cm(0)
        pf.first_line_indent = Cm(0)
        run_label = p.add_run(f"{rotulo}: ")
        run_label.font.name = FONT_NAME
        run_label.font.size = Pt(10)
        run_label.font.italic = False
        run_label.font.bold = False
        run_text = p.add_run(texto)
        run_text.font.name = FONT_NAME
        run_text.font.size = Pt(10)
        run_text.font.italic = False
        run_text.font.bold = False
        return p

    def add_nota_elemento_custom(self, rotulo, texto):
        return self.add_nota_elemento(texto, rotulo=rotulo)

    def add_tabela(self, headers, rows, col_widths=None):
        """Tabela institucional: header navy/gold, listras, bordas cinza.

        Se houver coluna cujo header normalize para 'STATUS', as células
        dessa coluna são pintadas automaticamente conforme STATUS_KEYWORDS
        (ATENDIDO/DIVERGENCIA/PARCIAL/LIMITACAO/NAO_VERIFICAVEL...).
        """
        table = self.document.add_table(rows=1 + len(rows), cols=max(1, len(headers)))
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        table.autofit = True

        # Identificar colunas Status (pode haver mais de uma)
        cols_status = {
            i for i, h in enumerate(headers)
            if _normalizar_status(str(h)) == "STATUS"
        }

        for i, header in enumerate(headers):
            cell = table.rows[0].cells[i]
            _set_cell_shading(cell, CORES.NAVY_DEEP)
            _set_cell_font(cell, header, bold=True, size=Pt(11),
                           color_hex=CORES.GOLD_LIGHT,
                           alignment=WD_ALIGN_PARAGRAPH.CENTER)
            _set_cell_margins(cell)

        for r_idx, row_data in enumerate(rows):
            bg = CORES.WHITE if r_idx % 2 == 0 else CORES.CREAM_LIGHT
            for c_idx, cell_text in enumerate(row_data):
                if c_idx >= len(table.rows[r_idx + 1].cells):
                    continue
                cell = table.rows[r_idx + 1].cells[c_idx]
                texto_celula = str(cell_text)

                cor_status = None
                if c_idx in cols_status:
                    cor_status = _classificar_status(texto_celula)

                if cor_status is not None:
                    cor_texto, cor_fundo = cor_status
                    _set_cell_shading(cell, cor_fundo)
                    _set_cell_font(cell, texto_celula, size=Pt(11),
                                   bold=True, color_hex=cor_texto,
                                   alignment=WD_ALIGN_PARAGRAPH.CENTER)
                else:
                    _set_cell_shading(cell, bg)
                    _set_cell_font(cell, texto_celula, size=Pt(11))
                _set_cell_margins(cell)

        tbl = table._tbl
        tblPr = tbl.tblPr if tbl.tblPr is not None else parse_xml(
            f'<w:tblPr {nsdecls("w")}/>'
        )
        borders = parse_xml(
            f'<w:tblBorders {nsdecls("w")}>'
            f'  <w:top w:val="single" w:sz="4" w:space="0" w:color="{CORES.GRAY_LIGHT}"/>'
            f'  <w:left w:val="single" w:sz="4" w:space="0" w:color="{CORES.GRAY_LIGHT}"/>'
            f'  <w:bottom w:val="single" w:sz="4" w:space="0" w:color="{CORES.GRAY_LIGHT}"/>'
            f'  <w:right w:val="single" w:sz="4" w:space="0" w:color="{CORES.GRAY_LIGHT}"/>'
            f'  <w:insideH w:val="single" w:sz="4" w:space="0" w:color="{CORES.GRAY_LIGHT}"/>'
            f'  <w:insideV w:val="single" w:sz="4" w:space="0" w:color="{CORES.GRAY_LIGHT}"/>'
            f'</w:tblBorders>'
        )
        tblPr.append(borders)

        if col_widths:
            for i, width in enumerate(col_widths):
                for row in table.rows:
                    if i < len(row.cells):
                        row.cells[i].width = Cm(width)
        return table

    def add_imagem(self, image_blob: bytes, largura_cm: float = 14.0, legenda: str = None):
        """Insere imagem centralizada."""
        p = self.document.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run()
        try:
            run.add_picture(io.BytesIO(image_blob), width=Cm(largura_cm))
        except Exception:
            return None
        if legenda:
            self.add_nota_elemento(legenda)
        return p

    def add_quebra_pagina(self):
        self.document.add_page_break()

    # ─── SALVAR ────────────────────────────────────────────────────────────────

    def salvar(self, caminho):
        path = Path(caminho)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.document.save(str(path))
        return path


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# REFORMATADOR DE DOCX EXISTENTE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _extrair_imagens_por_paragrafo(doc):
    """
    Mapeia ID do parágrafo (índice em doc.paragraphs) -> lista de blobs de imagem.
    Cobre apenas imagens inline. Retorna dict {idx_par: [blob, ...]}.
    """
    mapa = {}
    for idx, p in enumerate(doc.paragraphs):
        blobs = []
        for run in p.runs:
            for drawing in run._element.iter(qn('w:drawing')):
                blips = drawing.findall('.//' + qn('a:blip')) or \
                        list(drawing.iter('{http://schemas.openxmlformats.org/drawingml/2006/main}blip'))
                for blip in blips:
                    rid = blip.get(qn('r:embed')) or \
                          blip.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed')
                    if rid:
                        try:
                            part = doc.part.related_parts[rid]
                            blobs.append(part.blob)
                        except Exception:
                            pass
        if blobs:
            mapa[idx] = blobs
    return mapa


def _detectar_titulo_documento(doc):
    """Tenta achar título e subtítulos entre os primeiros parágrafos do corpo.

    Heurística: percorre parágrafos até encontrar o primeiro heading detectável
    (Bloco N:, X.Y) ou parágrafo com estilo Heading. Os parágrafos não vazios
    com fonte ≥ 16pt são candidatos a título; os subsequentes são subtítulos.

    Retorna dict {"titulo", "subtitulo1", "subtitulo2"} ou None.
    """
    candidatos = []
    data_capa = None
    for p in doc.paragraphs[:30]:
        texto = p.text.strip()
        if not texto:
            continue
        # Parar quando encontrar um heading do corpo
        nivel = detectar_nivel_heading(texto)
        if nivel:
            break
        try:
            if p.style and 'Heading' in p.style.name:
                break
        except Exception:
            pass
        # Tamanho de fonte: pegar a maior do parágrafo
        sz_max = 0
        for r in p.runs:
            if r.font.size:
                sz_max = max(sz_max, r.font.size.pt)
        # Captura linha de data (ex.: "Abril 2026", "abril de 2026")
        if data_capa is None and RE_DATA_CAPA.match(texto):
            data_capa = texto
            continue
        candidatos.append((sz_max, texto, p))
        if len(candidatos) >= 5:
            break

    # Filtrar candidatos com fonte grande (>= 12)
    grandes = [(s, t) for s, t, _ in candidatos if s >= 12]
    if not grandes and not data_capa:
        return None
    # Ordenar pela ordem do documento, mantendo só os 3 primeiros
    grandes = grandes[:3]
    out = {}
    if grandes:
        out["titulo"] = grandes[0][1]
    if len(grandes) >= 2:
        out["subtitulo1"] = grandes[1][1]
    if len(grandes) >= 3:
        out["subtitulo2"] = grandes[2][1]
    if data_capa:
        out["data"] = data_capa
    return out if out else None


def _limpar_numeracao_manual(texto: str) -> str:
    """Remove '1. ', '12) ', '(3) ' do início. Preserva texto restante intacto."""
    return RE_NUMERACAO_MANUAL.sub("", texto, count=1)


# Substituições para "o mesmo" como pronome → ele/ela/eles/elas
_RE_O_MESMO  = re.compile(r"\b[Oo] mesmo\b")
_RE_A_MESMA  = re.compile(r"\b[Aa] mesma\b")
_RE_OS_MESMOS = re.compile(r"\b[Oo]s mesmos\b")
_RE_AS_MESMAS = re.compile(r"\b[Aa]s mesmas\b")


def _limpar_texto(texto: str, limpar_travessoes: bool = False,
                  limpar_o_mesmo: bool = False,
                  variaveis: dict = None) -> str:
    """
    Aplica saneamento textual conforme regras .copilot.md:
    - variaveis: substitui {{chave}} pelos valores fornecidos (combinados com
      VARIAVEIS_PADRAO). Aplicado ANTES das demais transformações para que
      travessões eventualmente injetados via variável também sejam tratados.
    - --limpar-travessoes: substitui — (em-dash) e – (en-dash) por ", " ou ":".
      Heurística simples: travessão entre espaços vira vírgula com espaço.
    - --limpar-o-mesmo: substitui "o mesmo"/"a mesma"/"os mesmos"/"as mesmas"
      por "ele"/"ela"/"eles"/"elas".
    """
    if not texto:
        return texto
    if variaveis:
        texto = _aplicar_variaveis(texto, variaveis)
    if limpar_travessoes:
        # Travessão com espaços ao redor → vírgula
        texto = re.sub(r"\s+[—–]\s+", ", ", texto)
        # Travessão restante (colado) → dois-pontos
        texto = texto.replace("—", ":").replace("–", "-")
    if limpar_o_mesmo:
        def _preserva_caixa(match, repl_lower, repl_capital):
            grupo = match.group(0)
            return repl_capital if grupo[0].isupper() else repl_lower

        texto = _RE_O_MESMO.sub(
            lambda m: "Ele" if m.group(0)[0] == "O" else "ele", texto)
        texto = _RE_A_MESMA.sub(
            lambda m: "Ela" if m.group(0)[0] == "A" else "ela", texto)
        texto = _RE_OS_MESMOS.sub(
            lambda m: "Eles" if m.group(0)[0] == "O" else "eles", texto)
        texto = _RE_AS_MESMAS.sub(
            lambda m: "Elas" if m.group(0)[0] == "A" else "elas", texto)
    return texto


# Padrões para labels e notas associadas a tabelas/figuras
RE_LABEL_TABELA = re.compile(r"^\s*(Tabela|Quadro)\s+\d+\s*[:\-–.]", re.IGNORECASE)
RE_LABEL_FIGURA = re.compile(r"^\s*(Figura|Gráfico|Imagem|Diagrama)\s+\d+\s*[:\-–.]", re.IGNORECASE)
RE_NOTA_PREFIX  = re.compile(r"^\s*Nota\s*[:\-–]", re.IGNORECASE)
RE_FONTE_PREFIX = re.compile(r"^\s*Fonte\s*[:\-–]", re.IGNORECASE)
RE_APENDICE     = re.compile(r"^\s*(?:Ap[eê]ndice|Anexo)\b", re.IGNORECASE)

# Apêndice/Anexo com captura do identificador (A, B, I, 1...) e título.
RE_APENDICE_HEADING = re.compile(
    r"^\s*(?:Ap[eê]ndice|Anexo)\s+([A-Z0-9IVX]+)\s*[:\.\-–]?\s*(.*)$",
    re.IGNORECASE,
)


# Heurísticas de supressão de tabelas de capa (compartilhadas md/docx)
CAMPOS_CAPA_METADADOS = {
    "processo", "acórdão", "acordao", "versão", "versao",
    "fundamentação", "fundamentacao", "unidade", "referência",
    "referencia", "relator", "base legal", "data", "uso",
    "órgão", "orgao", "responsável", "responsavel",
}


def _eh_tabela_header_institucional(linhas):
    """Tabela 1-3 linhas com 'TRIBUNAL DE CONTAS DA UNIÃO' → header institucional."""
    if not linhas or len(linhas) > 3:
        return False
    txt = " ".join(" ".join(l) for l in linhas).upper()
    return "TRIBUNAL DE CONTAS DA UNIÃO" in txt


def _eh_tabela_metadados_capa(linhas):
    """Tabela 2 colunas com rótulos típicos de capa (Processo, Acórdão, etc.)."""
    if not linhas or not linhas[0] or len(linhas[0]) != 2:
        return False
    rotulos = [(l[0] if l else "").strip().lower() for l in linhas]
    acertos = sum(1 for r in rotulos if r in CAMPOS_CAPA_METADADOS)
    return acertos >= max(2, len(linhas) // 2)


def _rotulo_tabela(contador_corpo, contador_apendice, apendice_id, descricao):
    """Constrói rótulo de tabela conforme estiver no corpo ou em apêndice."""
    desc = (descricao or "dados").strip()
    if apendice_id:
        return f"Tabela {contador_apendice}-Apêndice{apendice_id}: {desc}"
    return f"Tabela {contador_corpo}: {desc}"


# ─── Detecção de metadados de capa ────────────────────────────────────────────

RE_META_PROCESSO = re.compile(r"^\s*Processo\s*[:\-]\s*(.+?)\s*$", re.IGNORECASE)
RE_META_ACORDAO  = re.compile(r"^\s*Ac[óo]rd[ãa]o\s*[:\-]\s*(.+?)\s*$", re.IGNORECASE)
RE_META_VERSAO   = re.compile(r"^\s*Vers[ãa]o\s*[:\-]\s*(.+?)\s*$", re.IGNORECASE)
RE_META_FUND     = re.compile(r"^\s*(Fundamenta[çc][ãa]o|Fonte)\s*[:\-]\s*(.+?)\s*$",
                              re.IGNORECASE)


def _extrair_metadados_capa(linhas):
    """A partir de uma lista de strings (parágrafos/linhas) próximas do início
    do documento, devolve dict com qualquer metadado de capa detectado:
        {processo, acordao, versao, fundamentacao, rotulo_fundamentacao}.
    Chaves ausentes ficam fora do dict."""
    out = {}
    for linha in linhas:
        if not linha:
            continue
        # Quebrar parágrafos com várias linhas internas (caso do docx)
        for sub in str(linha).splitlines():
            sub = sub.strip()
            if not sub:
                continue
            if "processo" not in out.get("_consumido", set()) and \
                    (m := RE_META_PROCESSO.match(sub)):
                out["processo"] = m.group(1).strip()
                continue
            if (m := RE_META_ACORDAO.match(sub)):
                out["acordao"] = m.group(1).strip()
                continue
            if (m := RE_META_VERSAO.match(sub)):
                out["versao"] = m.group(1).strip()
                continue
            if (m := RE_META_FUND.match(sub)):
                rot_raw = m.group(1).strip()
                # Normaliza acentuação para o rótulo final
                if rot_raw.lower().startswith("fonte"):
                    out["rotulo_fundamentacao"] = "Fonte"
                else:
                    out["rotulo_fundamentacao"] = "Fundamentação"
                out["fundamentacao"] = m.group(2).strip()
                continue
    return out


# ─── Geração do CheckList ─────────────────────────────────────────────────────

def _gerar_checklist(stats, ok, erros, avisos, output_path,
                     entrada_path, modo, opcoes_aplicadas):
    """
    Cria um arquivo `<saida_stem>_CheckList.md` ao lado do .docx, listando
    todas as transformações aplicadas e o resultado da validação. O usuário
    deve revisar manualmente cada item e marcar como conferido.

    Retorna o Path do arquivo gerado.
    """
    output_path = Path(output_path)
    checklist_path = output_path.with_name(f"{output_path.stem}_CheckList.md")

    def _it(label, valor):
        return f"- [ ] **{label}:** {valor}"

    linhas = []
    linhas.append(f"# Checklist de Conferência: {output_path.name}")
    linhas.append("")
    linhas.append(f"**Arquivo gerado:** `{output_path.name}`  ")
    linhas.append(f"**Arquivo de origem:** `{Path(entrada_path).name}`  ")
    linhas.append(f"**Modo:** {modo}  ")
    linhas.append(f"**Tamanho:** {output_path.stat().st_size:,} bytes  ")
    linhas.append("")
    linhas.append("> Marque cada item após abrir o `.docx` no Word e conferir "
                  "visualmente. Itens em vermelho devem ser revistos antes do uso "
                  "institucional.")
    linhas.append("")

    # ── Conferência manual obrigatória (vem primeiro: é o uso prático do checklist) ──
    linhas.append("## 1. Conferência manual obrigatória")
    linhas.append("")
    linhas.append("Abrir o `.docx` no Word/Google Docs e confirmar:")
    linhas.append("")
    linhas.append("- [ ] Capa visualmente fiel ao padrão SecexContas (alinhamento à esquerda, "
                  "linha gold visível abaixo do subtítulo).")
    linhas.append("- [ ] Logo TCU presente no header de todas as páginas.")
    linhas.append("- [ ] Paginação aparece no rodapé.")
    linhas.append("- [ ] Apêndices iniciam em página própria (quebra automática).")
    linhas.append("- [ ] Tabelas com listras (linhas pares brancas, ímpares creme).")
    linhas.append("- [ ] Coluna “Status” colorida (Atendido verde, Divergência vermelho, "
                  "Parcial âmbar, …).")
    linhas.append("- [ ] Nenhuma numeração manual (“1. ”, “12) ”) sobrou no início dos parágrafos.")
    linhas.append("- [ ] Texto sem fabricação: nomes, números, citações e datas conferem com a fonte.")
    linhas.append("")

    # ── Capa ──
    linhas.append("## 2. Capa institucional")
    linhas.append("")
    linhas.append(_it("Título principal", f"`{stats.get('capa_titulo','(não definido)')}` "
                                          "(28pt, bold, navy)"))
    if stats.get("capa_subtitulo1"):
        linhas.append(_it("Subtítulo principal",
                          f"`{stats['capa_subtitulo1']}` (18pt navy)"))
    if stats.get("capa_subtitulo2"):
        linhas.append(_it("Subtítulo secundário",
                          f"`{stats['capa_subtitulo2']}` (13pt navy_mid)"))
    if stats.get("capa_data"):
        linhas.append(_it("Data da capa", f"`{stats['capa_data']}` (12pt navy_mid)"))
    linhas.append(_it("Linha gold abaixo do subtítulo", "espessura 18 dxa, cor #B8963E"))
    linhas.append(_it("Bloco institucional",
                      "“Tribunal de Contas da União” (11pt bold) + "
                      "SecexContas (10pt cinza)"))
    linhas.append(_it("Bloco processo",
                      f"Processo: `{stats.get('capa_processo','—')}`, "
                      f"Acórdão: `{stats.get('capa_acordao','—')}`, "
                      f"Versão: `{stats.get('capa_versao','—')}` (10pt cinza)"))
    if stats.get("capa_fundamentacao"):
        rot = stats.get("capa_rotulo_fundamentacao", "Fundamentação")
        linhas.append(_it(f"Rótulo: {rot}",
                          f"`{stats['capa_fundamentacao']}` (10pt cinza, sem bold)"))
    linhas.append("")

    # ── Estrutura ──
    linhas.append("## 3. Estrutura do corpo")
    linhas.append("")
    linhas.append(_it("Headings de nível 1",
                      f"{stats.get('headings_1', 0)} (com linha gold abaixo)"))
    linhas.append(_it("Headings de nível 2", str(stats.get('headings_2', 0))))
    linhas.append(_it("Headings de nível 3", str(stats.get('headings_3', 0))))
    apend = stats.get('apendices', 0)
    if apend:
        linhas.append(_it("Apêndices/Anexos",
                          f"{apend} (cada um com quebra de página antes)"))
    linhas.append(_it("Tabelas", f"{stats.get('tabelas', 0)} "
                                  "(header navy/gold, listras, bordas cinza)"))
    if stats.get('tabelas_apendice'):
        linhas.append(_it("Tabelas em apêndice",
                          f"{stats['tabelas_apendice']} "
                          "(rotuladas `Tabela N-ApêndiceX`)"))
    linhas.append(_it("Bullets",
                      f"{stats.get('bullets', 0)} (estilo nativo `List Bullet`)"))
    if stats.get('regras'):
        linhas.append(_it("Regras de negócio (RN-/RG-)",
                          f"{stats['regras']} (caixa de alerta com criticidade)"))
    if stats.get('alertas'):
        linhas.append(_it("Caixas de alerta", str(stats['alertas'])))
    if stats.get('destaques'):
        linhas.append(_it("Caixas de destaque",
                          f"{stats['destaques']} (atenção/positivo/info)"))
    if stats.get('imagens'):
        linhas.append(_it("Imagens preservadas", str(stats['imagens'])))
    linhas.append("")

    # ── Moldura ──
    linhas.append("## 4. Moldura institucional")
    linhas.append("")
    linhas.append(_it("Header com logo TCU",
                      "logo + “Tribunal de Contas da União” + Secretaria-Geral "
                      "+ SecexContas + linha gold"))
    linhas.append(_it("Footer com paginação",
                      "linha gold superior + “GT Reforma Tributária” + Página N"))
    linhas.append(_it("Fonte Aptos no estilo Normal", "12pt"))
    linhas.append(_it("Idioma pt-BR no estilo Normal", "configurado em themeFontLang"))
    linhas.append(_it("Margens TCU",
                      "esquerda 3 cm, demais 2,54 cm"))
    linhas.append("")

    # ── Limpezas / variáveis ──
    if opcoes_aplicadas:
        linhas.append("## 5. Limpezas e variáveis aplicadas")
        linhas.append("")
        for k, v in opcoes_aplicadas.items():
            linhas.append(_it(k, v))
        linhas.append("")

    # ── Validação ──
    linhas.append("## 6. Validação automática")
    linhas.append("")
    if ok and not avisos:
        linhas.append("- [x] **Documento aprovado:** nenhum erro ou aviso.")
    elif ok:
        linhas.append("- [x] **Sem erros bloqueantes.**")
        linhas.append(f"- [ ] Revisar {len(avisos)} aviso(s) abaixo:")
        for a in avisos:
            linhas.append(f"  - {a}")
    else:
        linhas.append(f"- [ ] **{len(erros)} erro(s) bloqueante(s) — corrigir antes do uso:**")
        for e in erros:
            linhas.append(f"  - {e}")
        if avisos:
            linhas.append(f"- [ ] Revisar {len(avisos)} aviso(s):")
            for a in avisos:
                linhas.append(f"  - {a}")
    linhas.append("")

    linhas.append("---")
    linhas.append("")
    linhas.append("_Checklist gerado automaticamente por `tcu_formatter.py`_")
    linhas.append("")

    checklist_path.write_text("\n".join(linhas), encoding="utf-8")
    return checklist_path


def format_docx(input_path: Path, output_path: Path,
                titulo: str = None, modulo: int = None,
                logo_path: str = None,
                processo: str = "TC 015.848/2025-6",
                acordao: str = "2833/2025-Plenário",
                versao: str = None,
                fundamentacao: str = None,
                rotulo_fundamentacao: str = "Fundamentação",
                gerar_capa: bool = True,
                validar: bool = True,
                gerar_checklist: bool = True,
                limpar_travessoes: bool = False,
                limpar_o_mesmo: bool = False,
                variaveis: dict = None) -> Path:
    """
    Lê um .docx e regrava no padrão TCU.

    - Detecta headings por regex (Bloco N → H1; X.Y → H2; X.Y.Z → H3).
    - Converte bullets em estilo nativo List Bullet.
    - Remove numeração manual no início dos parágrafos.
    - Detecta regras (RN-X.Y, RG-X.Y) e aplica caixa de alerta.
    - Preserva tabelas (recriadas com header navy/gold) e imagens inline.
    - "Tabela N: ..." imediatamente antes de uma tabela vira label
      centralizado fonte 11.
    - "Nota: ..." imediatamente após uma tabela/figura vira nota
      esquerda fonte 10 cinza.
    - Headings que comecem com "Apêndice" ou "Anexo" recebem quebra
      de página antes.
    """
    src = Document(str(input_path))
    img_map = _extrair_imagens_por_paragrafo(src)

    # Combina variáveis padrão do projeto com as fornecidas pelo usuário
    vars_efetivas = dict(VARIAVEIS_PADRAO)
    if modulo is not None:
        vars_efetivas["modulo"] = str(modulo)
    if variaveis:
        vars_efetivas.update({k: ("" if v is None else str(v))
                              for k, v in variaveis.items()})

    info_capa = _detectar_titulo_documento(src) or {}
    titulo_final = titulo or info_capa.get("titulo") or input_path.stem
    titulo_final = _aplicar_variaveis(titulo_final, vars_efetivas)
    subt1 = info_capa.get("subtitulo1")
    subt2 = info_capa.get("subtitulo2")

    # Auto-detectar metadados de capa (Processo, Acórdão, Versão, Fundamentação/Fonte)
    primeiros_paragrafos = [p.text for p in src.paragraphs[:30]]
    meta_detectada = _extrair_metadados_capa(primeiros_paragrafos)
    processo_eff      = meta_detectada.get("processo")      or processo
    acordao_eff       = meta_detectada.get("acordao")       or acordao
    versao_eff        = meta_detectada.get("versao")        or versao
    fund_eff          = meta_detectada.get("fundamentacao") or fundamentacao
    rot_fund_eff      = meta_detectada.get("rotulo_fundamentacao") or rotulo_fundamentacao
    textos_meta_capa  = {
        v.strip().upper() for v in meta_detectada.values() if v and v != rot_fund_eff
    }

    fmt = TCUFormatter(
        modulo=modulo,
        logo_path=logo_path,
        titulo=titulo_final,
        processo=processo_eff,
        subtitulo=subt1,
    )

    data_capa = info_capa.get("data")

    if gerar_capa:
        fmt.add_capa(
            titulo=titulo_final,
            subtitulo1=subt1,
            subtitulo2=subt2,
            processo=processo_eff,
            acordao=acordao_eff,
            versao=versao_eff,
            fundamentacao=fund_eff,
            rotulo_fundamentacao=rot_fund_eff,
            data=data_capa,
        )

    stats = {
        "capa_titulo": titulo_final,
        "capa_subtitulo1": subt1,
        "capa_subtitulo2": subt2,
        "capa_data": data_capa,
        "capa_processo": processo_eff,
        "capa_acordao": acordao_eff,
        "capa_versao": versao_eff,
        "capa_fundamentacao": fund_eff,
        "capa_rotulo_fundamentacao": rot_fund_eff,
        "headings_1": 0, "headings_2": 0, "headings_3": 0,
        "apendices": 0, "tabelas": 0, "tabelas_apendice": 0,
        "bullets": 0, "regras": 0, "alertas": 0,
        "destaques": 0, "imagens": 0,
    }

    # Conjunto de textos da capa (para suprimir do corpo)
    textos_capa = {titulo_final.strip().upper()}
    if subt1:
        textos_capa.add(subt1.strip().upper())
    if subt2:
        textos_capa.add(subt2.strip().upper())
    if data_capa:
        textos_capa.add(data_capa.strip().upper())

    # Linearizar corpo na ordem original
    body_children = list(src.element.body.iterchildren())
    sequencia = []
    p_idx = 0
    t_idx = 0
    for child in body_children:
        if child.tag == qn('w:p'):
            sequencia.append(('p', src.paragraphs[p_idx], p_idx))
            p_idx += 1
        elif child.tag == qn('w:tbl'):
            sequencia.append(('t', src.tables[t_idx], t_idx))
            t_idx += 1

    # Pré-passada: identificar índices de "Tabela N:" antes de tabelas,
    # "Figura N:" antes de parágrafos com imagem, e "Nota:" depois.
    label_antes_tabela = {}   # idx_seq da tabela -> texto do label
    label_antes_figura = {}   # idx_seq do parágrafo-com-imagem -> texto do label
    nota_apos_elemento = {}   # idx_seq do parágrafo -> "label" | "nota"

    def _eh_para_imagem(seq_item):
        if seq_item[0] != 'p':
            return False
        return seq_item[2] in img_map

    for i, item in enumerate(sequencia):
        eh_tabela = item[0] == 't'
        eh_imagem = _eh_para_imagem(item)
        if not (eh_tabela or eh_imagem):
            continue

        # Label nos parágrafos imediatamente anteriores (ignorando vazios)
        j = i - 1
        while j >= 0 and sequencia[j][0] == 'p' and not sequencia[j][1].text.strip():
            j -= 1
        if j >= 0 and sequencia[j][0] == 'p':
            txt = sequencia[j][1].text.strip()
            if eh_tabela and RE_LABEL_TABELA.match(txt):
                label_antes_tabela[i] = txt
                nota_apos_elemento[j] = "label"
            elif eh_imagem and RE_LABEL_FIGURA.match(txt):
                label_antes_figura[i] = txt
                nota_apos_elemento[j] = "label"

        # Nota:/Fonte: nos parágrafos imediatamente seguintes
        j = i + 1
        while j < len(sequencia) and sequencia[j][0] == 'p' and \
              not sequencia[j][1].text.strip() and \
              sequencia[j][2] not in img_map:
            j += 1
        if j < len(sequencia) and sequencia[j][0] == 'p':
            txt = sequencia[j][1].text.strip()
            if RE_NOTA_PREFIX.match(txt) or RE_FONTE_PREFIX.match(txt):
                nota_apos_elemento[j] = "nota"

    # Renderizar
    titulo_consumido = {"titulo": False, "sub1": False, "sub2": False}
    contador_tabela = 0
    contador_figura = 0
    apendice_atual = None        # identificador do apêndice corrente ("A", "B"...)
    contador_tabela_apendice = 0  # contador reiniciado a cada apêndice
    ultimo_heading_curto = None  # texto do último heading (sem prefixo numérico)

    def _limpar_prefixo_heading(s):
        # Remove "1.3 ", "Bloco 2: ", "PARTE I:", "A.2 " etc. para virar descrição limpa
        s = re.sub(r"^(?:Bloco|Capítulo|Parte|PARTE)\s+[IVX0-9]+\s*[:\.\-–]?\s*", "", s, flags=re.IGNORECASE)
        s = re.sub(r"^(?:Ap[eê]ndice|Anexo)\s+[A-Z0-9]+\s*[:\.\-–]?\s*", "", s, flags=re.IGNORECASE)
        s = re.sub(r"^\s*(?:[0-9]{1,2}|[A-Z])(?:\.[0-9]{1,2}){0,2}\.?\s+", "", s)
        return s.strip()

    for i, item in enumerate(sequencia):
        tipo = item[0]

        if tipo == 't':
            tabela_src = item[1]

            # Caixa de destaque (1×1 ou 1×2 com fundo colorido) → add_destaque
            destaque = _eh_caixa_destaque(tabela_src)
            if destaque is not None:
                tipo_dest, texto_dest = destaque
                texto_dest = _limpar_texto(texto_dest, limpar_travessoes,
                                           limpar_o_mesmo, vars_efetivas)
                fmt.add_destaque(texto_dest, tipo=tipo_dest)
                stats["destaques"] += 1
                continue

            linhas = []
            for row in tabela_src.rows:
                linhas.append([cell.text.strip() for cell in row.cells])
            if not linhas:
                continue
            # Suprimir tabela de cabeçalho institucional e tabela de metadados da capa
            if _eh_tabela_header_institucional(linhas):
                continue
            if _eh_tabela_metadados_capa(linhas):
                continue

            # Label acima: explícito se existir; senão gerar automático
            if i in label_antes_tabela:
                # Label explícito não é remunerado; ainda assim atualiza contadores
                # para que tabelas seguintes sigam a sequência correta.
                if apendice_atual:
                    contador_tabela_apendice += 1
                else:
                    contador_tabela += 1
                fmt.add_titulo_elemento(label_antes_tabela[i])
            else:
                desc = ultimo_heading_curto or "dados do bloco"
                if apendice_atual:
                    contador_tabela_apendice += 1
                    rot = _rotulo_tabela(contador_tabela, contador_tabela_apendice,
                                         apendice_atual, desc)
                else:
                    contador_tabela += 1
                    rot = _rotulo_tabela(contador_tabela, contador_tabela_apendice,
                                         None, desc)
                fmt.add_titulo_elemento(rot)
            headers = linhas[0]
            rows = linhas[1:] if len(linhas) > 1 else []
            fmt.add_tabela(headers=headers, rows=rows)
            stats["tabelas"] += 1
            if apendice_atual:
                stats["tabelas_apendice"] += 1
            continue

        # tipo == 'p'
        para = item[1]
        idx_par = item[2]
        texto = para.text.strip()

        # Imagens
        if idx_par in img_map:
            for k_img, blob in enumerate(img_map[idx_par]):
                contador_figura += 1
                if k_img == 0 and i in label_antes_figura:
                    fmt.add_titulo_elemento(label_antes_figura[i])
                else:
                    desc = ultimo_heading_curto or "ilustração"
                    fmt.add_titulo_elemento(f"Figura {contador_figura}: {desc}")
                fmt.add_imagem(blob, largura_cm=14.0)
                stats["imagens"] += 1
            if not texto:
                continue

        if not texto:
            continue

        # Marcado como label de tabela já emitido — pular
        if nota_apos_elemento.get(i) == "label":
            continue

        # Marcado como nota — formatar como nota (prioridade sobre supressão
        # de metadados, pois "Fonte:" no corpo não é metadado de capa)
        if nota_apos_elemento.get(i) == "nota":
            texto = _limpar_texto(texto, limpar_travessoes, limpar_o_mesmo,
                                  vars_efetivas)
            # Remover prefixo "Nota:" / "Fonte:" duplicado pelo método
            corpo = re.sub(r"^\s*Nota\s*[:\-–]\s*", "", texto, flags=re.IGNORECASE)
            if corpo == texto:
                corpo = re.sub(r"^\s*Fonte\s*[:\-–]\s*", "", texto, flags=re.IGNORECASE)
                fmt.add_nota_elemento_custom("Fonte", corpo)
            else:
                fmt.add_nota_elemento(corpo)
            continue

        # Suprimir linhas de metadados de capa (Processo:, Acórdão:, Versão:,
        # Fundamentação:). "Fonte:" só é suprimida na região da capa (antes do
        # primeiro heading renderizado), pois no corpo indica nota de elemento.
        if RE_META_PROCESSO.match(texto) or RE_META_ACORDAO.match(texto) or \
           RE_META_VERSAO.match(texto):
            continue
        if RE_META_FUND.match(texto) and stats["headings_1"] == 0:
            continue

        # "Fonte:" no corpo (não detectada na pré-passada): renderizar como nota
        if stats["headings_1"] > 0 and RE_FONTE_PREFIX.match(texto):
            texto = _limpar_texto(texto, limpar_travessoes, limpar_o_mesmo,
                                  vars_efetivas)
            corpo = re.sub(r"^\s*Fonte\s*[:\-–]\s*", "", texto, flags=re.IGNORECASE)
            fmt.add_nota_elemento_custom("Fonte", corpo)
            continue

        # Suprimir títulos da capa (não duplicar)
        texto_upper = texto.upper()
        if not titulo_consumido["titulo"] and texto_upper == titulo_final.strip().upper():
            titulo_consumido["titulo"] = True
            continue
        if subt1 and not titulo_consumido["sub1"] and texto_upper == subt1.strip().upper():
            titulo_consumido["sub1"] = True
            continue
        if subt2 and not titulo_consumido["sub2"] and texto_upper == subt2.strip().upper():
            titulo_consumido["sub2"] = True
            continue
        # Suprimir linha de data da capa
        if data_capa and texto_upper == data_capa.strip().upper():
            continue

        # Saneamento textual + substituição de {{chave}}
        texto = _limpar_texto(texto, limpar_travessoes, limpar_o_mesmo,
                              vars_efetivas)

        # Regra de negócio?
        m_regra = RE_REGRA_ID.match(texto)
        if m_regra:
            prefixo, resto = m_regra.group(1), m_regra.group(2)
            fmt.add_alerta(prefixo, resto, criticidade="Alta")
            stats["regras"] += 1
            stats["alertas"] += 1
            continue

        # Bullet em lista nativa do Word (estilo List* ou w:numPr)
        if _eh_lista_nativa(para):
            texto_bullet = RE_BULLET_PREFIX.sub("", texto, count=1)
            fmt.add_bullet(texto_bullet)
            stats["bullets"] += 1
            continue

        # Heading? (regex + estilo nativo + heurística de fonte)
        nivel = detectar_nivel_heading_para(para, texto)
        # Apêndice/Anexo com quebra de página antes + reset de contador de tabela
        m_ap = RE_APENDICE_HEADING.match(texto)
        if m_ap and (nivel or len(texto) < 120):
            fmt.add_quebra_pagina()
            fmt.add_heading(texto, level=1)
            ultimo_heading_curto = _limpar_prefixo_heading(texto)
            apendice_atual = (m_ap.group(1) or "").upper() or "A"
            contador_tabela_apendice = 0
            stats["apendices"] += 1
            stats["headings_1"] += 1
            continue

        if nivel:
            fmt.add_heading(texto, level=nivel)
            ultimo_heading_curto = _limpar_prefixo_heading(texto)
            stats[f"headings_{nivel}"] += 1
            continue

        if RE_BULLET_PREFIX.match(texto):
            texto_limpo = RE_BULLET_PREFIX.sub("", texto, count=1)
            fmt.add_bullet(texto_limpo)
            stats["bullets"] += 1
            continue

        texto_sem_num = _limpar_numeracao_manual(texto)
        fmt.add_paragrafo(texto_sem_num)

    fmt.salvar(output_path)
    ok, erros, avisos = (True, [], [])
    if validar:
        ok, erros, avisos = validar_documento(output_path)
        _imprimir_validacao(output_path, ok, erros, avisos)
    if gerar_checklist:
        opcoes = {}
        if limpar_travessoes:
            opcoes["Limpar travessões"] = "— e – substituídos por vírgula/dois-pontos"
        if limpar_o_mesmo:
            opcoes["Limpar 'o mesmo'"] = "substituído por ele/ela/eles/elas"
        if variaveis:
            opcoes["Variáveis injetadas"] = ", ".join(
                f"{{{{ {k} }}}}={v}" for k, v in variaveis.items()
            )
        cl_path = _gerar_checklist(stats, ok, erros, avisos, output_path,
                                   input_path, "DOCX → DOCX", opcoes)
        print(f"[CHECKLIST] {cl_path}")
    return output_path


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# VALIDAÇÃO DE DOCUMENTO GERADO (autocontido)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def validar_documento(caminho):
    """
    Valida um arquivo DOCX existente contra as regras de design e escrita TCU.

    Checagens:
    - Ausência de travessões (— e –)
    - Palavras sem acento (padrões conhecidos)
    - Padrões proibidos ("o mesmo" como pronome, gerundismo)
    - Vocabulário de auditoria proibido ("auditoria/auditor/achado")
    - Idioma pt-BR no estilo Normal
    - Fonte Aptos no estilo Normal
    - Header com conteúdo (logo TCU esperado)
    - Footer com conteúdo (paginação esperada)
    - Tabelas sem WidthType.PERCENTAGE (quebra no Google Docs)

    Retorna: (ok: bool, erros: list[str], avisos: list[str])
    """
    from docx import Document as LoadDocument

    erros = []
    avisos = []
    doc = LoadDocument(str(caminho))
    all_text = "\n".join(p.text for p in doc.paragraphs)
    text_lower = all_text.lower()

    # 1. Travessões
    for i, para in enumerate(doc.paragraphs):
        if '—' in para.text or '–' in para.text:
            erros.append(
                f"Travessão no parágrafo {i+1}: '{para.text[:60]}...'"
            )

    # 2. Palavras sem acento
    _ACENTOS = {
        r'\barrecadacao\b': 'arrecadação',
        r'\baliquota\b': 'alíquota',
        r'\bcontribuicao\b': 'contribuição',
        r'\bpublico\b': 'público',
        r'\bmodulo\b': 'módulo',
        r'\bfuncao\b': 'função',
        r'\bquestao\b': 'questão',
        r'\borgao\b': 'órgão',
        r'\bsecao\b': 'seção',
        r'\bverificacao\b': 'verificação',
        r'\bmetodologia\b': 'metodologia',
        r'\binformacao\b': 'informação',
        r'\bdeducao\b': 'dedução',
        r'\btributaria\b': 'tributária',
        r'\bproibicao\b': 'proibição',
        r'\bespacamento\b': 'espaçamento',
        r'\bparagrafo\b': 'parágrafo',
        r'\bespecifico\b': 'específico',
        r'\bsemantico\b': 'semântico',
        r'\bcanonico\b': 'canônico',
        r'\bdivergencia\b': 'divergência',
        r'\blimitacao\b': 'limitação',
        r'\bnumero\b': 'número',
        r'\btitulo\b': 'título',
        r'\bpagina\b': 'página',
        r'\brodape\b': 'rodapé',
    }
    for pattern, correto in _ACENTOS.items():
        if re.search(pattern, text_lower):
            erros.append(f"Palavra sem acento: usar '{correto}'")

    # 3. Padrões proibidos
    if re.search(r'\bo mesmo\b', text_lower):
        avisos.append("Padrão duvidoso: 'o mesmo' (verificar se usado como pronome)")

    if re.search(r'\bvai estar \w+ndo\b', text_lower):
        erros.append("Gerundismo detectado ('vai estar ...ndo')")

    # 4. Vocabulário de auditoria (proibido pelo .copilot.md)
    for termo in (r'\bauditoria\b', r'\bauditor(?:es|a|as)?\b', r'\bachado(?:s)?\b'):
        if re.search(termo, text_lower):
            avisos.append(
                f"Vocabulário de auditoria detectado (padrão: {termo}). "
                f"Usar 'execução do cálculo', 'divergência', 'ponto de atenção', 'observação técnica'."
            )

    # 5. pt-BR no estilo Normal
    style = doc.styles['Normal']
    rpr = style.element.find(qn('w:rPr'))
    if rpr is not None:
        lang = rpr.find(qn('w:lang'))
        if lang is None or lang.get(qn('w:val')) != 'pt-BR':
            erros.append("Idioma pt-BR ausente no estilo Normal")
    else:
        erros.append("rPr ausente no estilo Normal (idioma não configurado)")

    # 6. Fonte Aptos
    if style.font.name and style.font.name != FONT_NAME:
        erros.append(f"Fonte incorreta: '{style.font.name}' (esperado: '{FONT_NAME}')")

    # 7. Header
    section = doc.sections[0]
    header_el = section.header._element
    if len(header_el) < 2:
        avisos.append("Header possivelmente vazio (sem logo TCU)")

    # 8. Footer
    footer_el = section.footer._element
    if len(footer_el) < 2:
        avisos.append("Footer possivelmente vazio (sem paginação)")

    # 9. Tabelas com largura percentual (proibido)
    for i, table in enumerate(doc.tables):
        tblPr = table._tbl.find(qn('w:tblPr'))
        if tblPr is not None:
            w_el = tblPr.find(qn('w:tblW'))
            if w_el is not None and w_el.get(qn('w:type')) == 'pct':
                erros.append(
                    f"Tabela {i+1}: usa WidthType.PERCENTAGE (proibido, quebra Google Docs)"
                )

    ok = len(erros) == 0
    return ok, erros, avisos


def _imprimir_validacao(caminho, ok, erros, avisos):
    """Imprime relatório de validação de forma estruturada."""
    print(f"\n[VALIDAÇÃO] {caminho}")
    if erros:
        print(f"  ✗ {len(erros)} erro(s):")
        for e in erros:
            print(f"    - {e}")
    if avisos:
        print(f"  ⚠ {len(avisos)} aviso(s):")
        for a in avisos:
            print(f"    - {a}")
    if ok and not avisos:
        print("  ✓ Documento aprovado: nenhum erro ou aviso.")
    elif ok:
        print("  ✓ Sem erros bloqueantes (apenas avisos).")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# REFORMATADOR DE MARKDOWN
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

RE_MD_H = re.compile(r"^(#{1,6})\s+(.*)$")
RE_MD_BULLET = re.compile(r"^\s*[\-\*\+]\s+(.*)$")
RE_MD_NUMBERED = re.compile(r"^\s*\d+\.\s+(.*)$")
RE_MD_TABLE_SEP = re.compile(r"^\s*\|?\s*[:\-]+[\s\|:\-]*$")


RE_MD_H_NAO_ESTRUTURAL = re.compile(
    r"^(?:Bloco|Capítulo|Parte|PARTE|Ap[eê]ndice|Anexo)\b",
    re.IGNORECASE,
)


def _detectar_subtitulos_md(linhas, titulo_final):
    """Identifica subtítulos da capa: parágrafos não-heading entre o H1 do
    título principal e o próximo heading (H2+) ou o próximo H1 estrutural
    (Bloco/Capítulo/Apêndice/Anexo). Retorna (subtitulo1, subtitulo2,
    indices_consumidos: set[int]) — os índices devem ser puláveis no loop."""
    subs = []
    consumidos = set()
    h1_idx = None
    for idx, l in enumerate(linhas[:80]):
        m = RE_MD_H.match(l)
        if m and len(m.group(1)) == 1 and m.group(2).strip() == titulo_final.strip():
            h1_idx = idx
            break
    if h1_idx is None:
        return (None, None, consumidos)

    j = h1_idx + 1
    while j < len(linhas) and len(subs) < 2:
        s = linhas[j].strip()
        if not s:
            j += 1
            continue
        m_h = RE_MD_H.match(linhas[j])
        if m_h:
            nivel = len(m_h.group(1))
            texto_h = m_h.group(2).strip()
            # Outro H1 estrutural ou H2+ → encerra
            if nivel >= 2 or RE_MD_H_NAO_ESTRUTURAL.match(texto_h):
                break
            # H1 não-estrutural pode também ser subtítulo
            subs.append(texto_h)
            consumidos.add(j)
            j += 1
            continue
        # Tabela ou bullet → encerra (não é subtítulo)
        if RE_MD_BULLET.match(linhas[j]) or RE_MD_NUMBERED.match(linhas[j]):
            break
        if "|" in linhas[j] and j + 1 < len(linhas) and RE_MD_TABLE_SEP.match(linhas[j+1]):
            break
        # Parágrafo curto e sem ponto final típico → subtítulo
        if len(s) <= 200:
            subs.append(s)
            consumidos.add(j)
        else:
            break
        j += 1

    sub1 = subs[0] if len(subs) >= 1 else None
    sub2 = subs[1] if len(subs) >= 2 else None
    return (sub1, sub2, consumidos)


def _extrair_linhas_tabela_md(linhas, i):
    """A partir do índice i (linha de header), extrai (headers, rows, j_final)
    se for uma tabela markdown válida. Caso contrário, retorna None."""
    if "|" not in linhas[i]:
        return None
    if i + 1 >= len(linhas) or not RE_MD_TABLE_SEP.match(linhas[i+1]):
        return None
    headers = [c.strip() for c in linhas[i].strip().strip("|").split("|")]
    j = i + 2
    rows = []
    while j < len(linhas) and "|" in linhas[j] and linhas[j].strip():
        rows.append([c.strip() for c in linhas[j].strip().strip("|").split("|")])
        j += 1
    return (headers, rows, j)


def format_md(input_path: Path, output_path: Path,
              titulo: str = None, modulo: int = None,
              logo_path: str = None,
              processo: str = "TC 015.848/2025-6",
              acordao: str = "2833/2025-Plenário",
              versao: str = None,
              fundamentacao: str = None,
              rotulo_fundamentacao: str = "Fundamentação",
              gerar_capa: bool = True,
              validar: bool = True,
              gerar_checklist: bool = True,
              limpar_travessoes: bool = False,
              limpar_o_mesmo: bool = False,
              variaveis: dict = None) -> Path:
    """Lê um arquivo .md e gera .docx no padrão TCU."""
    texto_md = Path(input_path).read_text(encoding="utf-8")
    linhas = texto_md.splitlines()

    # Combina variáveis padrão com as fornecidas pelo usuário
    vars_efetivas = dict(VARIAVEIS_PADRAO)
    if modulo is not None:
        vars_efetivas["modulo"] = str(modulo)
    if variaveis:
        vars_efetivas.update({k: ("" if v is None else str(v))
                              for k, v in variaveis.items()})

    titulo_final = titulo
    if not titulo_final:
        for linha in linhas[:30]:
            m = RE_MD_H.match(linha)
            if m and len(m.group(1)) == 1:
                titulo_final = m.group(2).strip()
                break
    titulo_final = titulo_final or Path(input_path).stem
    titulo_final = _aplicar_variaveis(titulo_final, vars_efetivas)

    # Pré-passada: detectar subtítulos da capa
    sub1, sub2, indices_subtitulos = _detectar_subtitulos_md(linhas, titulo_final)
    if sub1:
        sub1 = _aplicar_variaveis(sub1, vars_efetivas)
    if sub2:
        sub2 = _aplicar_variaveis(sub2, vars_efetivas)

    # Auto-detectar metadados de capa nas primeiras linhas
    meta_detectada = _extrair_metadados_capa(linhas[:60])
    processo_eff = meta_detectada.get("processo")      or processo
    acordao_eff  = meta_detectada.get("acordao")       or acordao
    versao_eff   = meta_detectada.get("versao")        or versao
    fund_eff     = meta_detectada.get("fundamentacao") or fundamentacao
    rot_fund_eff = meta_detectada.get("rotulo_fundamentacao") or rotulo_fundamentacao

    fmt = TCUFormatter(modulo=modulo, logo_path=logo_path,
                       titulo=titulo_final, processo=processo_eff,
                       subtitulo=sub1)
    if gerar_capa:
        fmt.add_capa(titulo=titulo_final, subtitulo1=sub1, subtitulo2=sub2,
                     processo=processo_eff, acordao=acordao_eff,
                     versao=versao_eff, fundamentacao=fund_eff,
                     rotulo_fundamentacao=rot_fund_eff)

    stats = {
        "capa_titulo": titulo_final,
        "capa_subtitulo1": sub1,
        "capa_subtitulo2": sub2,
        "capa_data": None,
        "capa_processo": processo_eff,
        "capa_acordao": acordao_eff,
        "capa_versao": versao_eff,
        "capa_fundamentacao": fund_eff,
        "capa_rotulo_fundamentacao": rot_fund_eff,
        "headings_1": 0, "headings_2": 0, "headings_3": 0,
        "apendices": 0, "tabelas": 0, "tabelas_apendice": 0,
        "bullets": 0, "regras": 0, "alertas": 0,
        "destaques": 0, "imagens": 0,
    }

    i = 0
    titulo_emitido = False
    ultimo_heading_curto = None
    contador_tabela = 0
    apendice_atual = None
    contador_tabela_apendice = 0

    def _limpar_prefixo_md(s):
        s = re.sub(r"^(?:Bloco|Capítulo|Parte|PARTE)\s+[IVX0-9]+\s*[:\.\-–]?\s*",
                   "", s, flags=re.IGNORECASE)
        s = re.sub(r"^(?:Ap[eê]ndice|Anexo)\s+[A-Z0-9]+\s*[:\.\-–]?\s*",
                   "", s, flags=re.IGNORECASE)
        s = re.sub(r"^\s*(?:[0-9]{1,2}|[A-Z])(?:\.[0-9]{1,2}){0,2}\.?\s+", "", s)
        return s.strip()

    while i < len(linhas):
        linha = linhas[i].rstrip()
        s = linha.strip()
        if not s:
            i += 1
            continue

        # Linhas marcadas como subtítulo da capa não vão pro corpo
        if i in indices_subtitulos:
            i += 1
            continue

        # Suprimir linhas de metadados de capa (Processo:, Acórdão:, Versão:,
        # Fundamentação:). "Fonte:" só é suprimida na região da capa (antes do
        # primeiro heading renderizado), pois no corpo indica nota de elemento.
        if RE_META_PROCESSO.match(s) or RE_META_ACORDAO.match(s) or \
           RE_META_VERSAO.match(s):
            i += 1
            continue
        if RE_META_FUND.match(s) and stats["headings_1"] == 0:
            i += 1
            continue

        # "Fonte:" no corpo: renderizar como nota de elemento
        if stats["headings_1"] > 0 and RE_FONTE_PREFIX.match(s):
            corpo = re.sub(r"^\s*Fonte\s*[:\-–]\s*", "", s, flags=re.IGNORECASE)
            corpo = _limpar_texto(corpo, limpar_travessoes, limpar_o_mesmo,
                                  vars_efetivas)
            fmt.add_nota_elemento_custom("Fonte", corpo)
            i += 1
            continue

        m_h = RE_MD_H.match(linha)
        if m_h:
            nivel = min(3, len(m_h.group(1)))
            texto = m_h.group(2).strip()
            if nivel == 1 and not titulo_emitido and texto == titulo_final:
                titulo_emitido = True
                i += 1
                continue
            # Apêndice/Anexo: quebra de página + reset de contador
            m_ap = RE_APENDICE_HEADING.match(texto)
            if m_ap:
                fmt.add_quebra_pagina()
                fmt.add_heading(texto, level=1)
                ultimo_heading_curto = _limpar_prefixo_md(texto)
                apendice_atual = (m_ap.group(1) or "").upper() or "A"
                contador_tabela_apendice = 0
                stats["apendices"] += 1
                stats["headings_1"] += 1
                i += 1
                continue
            fmt.add_heading(texto, level=nivel)
            ultimo_heading_curto = _limpar_prefixo_md(texto)
            stats[f"headings_{nivel}"] += 1
            i += 1
            continue

        # Tabela markdown: detecta cabeçalho seguido de separador "|---|"
        if "|" in linha and i + 1 < len(linhas) and RE_MD_TABLE_SEP.match(linhas[i+1]):
            extraido = _extrair_linhas_tabela_md(linhas, i)
            if extraido is None:
                i += 1
                continue
            headers_raw, rows_raw, j = extraido
            # Suprimir tabelas-cabeçalho/metadados da capa, antes de aplicar limpeza
            todas_linhas = [headers_raw] + rows_raw
            if _eh_tabela_header_institucional(todas_linhas) or \
               _eh_tabela_metadados_capa(todas_linhas):
                i = j
                continue

            headers = [_limpar_texto(c, limpar_travessoes, limpar_o_mesmo,
                                     vars_efetivas) for c in headers_raw]
            rows = [[_limpar_texto(c, limpar_travessoes, limpar_o_mesmo,
                                   vars_efetivas) for c in row]
                    for row in rows_raw]

            desc = ultimo_heading_curto or "dados do bloco"
            if apendice_atual:
                contador_tabela_apendice += 1
                rot = _rotulo_tabela(contador_tabela, contador_tabela_apendice,
                                     apendice_atual, desc)
            else:
                contador_tabela += 1
                rot = _rotulo_tabela(contador_tabela, contador_tabela_apendice,
                                     None, desc)
            fmt.add_titulo_elemento(rot)
            fmt.add_tabela(headers=headers, rows=rows)
            stats["tabelas"] += 1
            if apendice_atual:
                stats["tabelas_apendice"] += 1
            i = j
            continue

        m_b = RE_MD_BULLET.match(linha)
        if m_b:
            fmt.add_bullet(_limpar_texto(m_b.group(1).strip(),
                                         limpar_travessoes, limpar_o_mesmo,
                                         vars_efetivas))
            stats["bullets"] += 1
            i += 1
            continue

        m_n = RE_MD_NUMBERED.match(linha)
        if m_n:
            # Numerados em md viram parágrafos sem o número (numeração manual)
            fmt.add_paragrafo(_limpar_texto(m_n.group(1).strip(),
                                            limpar_travessoes, limpar_o_mesmo,
                                            vars_efetivas))
            i += 1
            continue

        # Parágrafo regular: agrupa linhas até linha em branco
        bloco = [s]
        j = i + 1
        while j < len(linhas) and linhas[j].strip() and \
              not RE_MD_H.match(linhas[j]) and not RE_MD_BULLET.match(linhas[j]) and \
              not RE_MD_NUMBERED.match(linhas[j]) and "|" not in linhas[j]:
            bloco.append(linhas[j].strip())
            j += 1
        fmt.add_paragrafo(_limpar_texto(" ".join(bloco),
                                        limpar_travessoes, limpar_o_mesmo,
                                        vars_efetivas))
        i = j

    fmt.salvar(output_path)
    ok, erros, avisos = (True, [], [])
    if validar:
        ok, erros, avisos = validar_documento(output_path)
        _imprimir_validacao(output_path, ok, erros, avisos)
    if gerar_checklist:
        opcoes = {}
        if limpar_travessoes:
            opcoes["Limpar travessões"] = "— e – substituídos por vírgula/dois-pontos"
        if limpar_o_mesmo:
            opcoes["Limpar 'o mesmo'"] = "substituído por ele/ela/eles/elas"
        if variaveis:
            opcoes["Variáveis injetadas"] = ", ".join(
                f"{{{{ {k} }}}}={v}" for k, v in variaveis.items()
            )
        cl_path = _gerar_checklist(stats, ok, erros, avisos, output_path,
                                   input_path, "MD → DOCX", opcoes)
        print(f"[CHECKLIST] {cl_path}")
    return output_path


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CLI
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def main():
    parser = argparse.ArgumentParser(
        description="Formatador TCU — gera .docx institucional a partir de .md ou .docx."
    )
    parser.add_argument("entrada", help="Arquivo de entrada (.md ou .docx)")
    parser.add_argument("saida", help="Arquivo de saída (.docx)")
    parser.add_argument("--titulo", default=None, help="Título do documento (capa).")
    parser.add_argument("--modulo", type=int, default=None, help="Número do módulo para o rodapé.")
    parser.add_argument("--logo", default=None, help="Caminho do logo TCU (PNG).")
    parser.add_argument("--sem-capa", action="store_true", help="Não gerar capa.")
    parser.add_argument("--sem-validacao", action="store_true",
                        help="Não executar validação automática após gerar o documento.")
    parser.add_argument("--sem-checklist", action="store_true",
                        help="Não gerar arquivo <saida>_CheckList.md ao lado do .docx.")
    parser.add_argument("--processo", default="TC 015.848/2025-6",
                        help="Número do processo (capa). Padrão: TC 015.848/2025-6.")
    parser.add_argument("--acordao", default="2833/2025-Plenário",
                        help="Acórdão de referência (capa). Padrão: 2833/2025-Plenário.")
    parser.add_argument("--versao", default=None,
                        help="Versão do documento (capa). Ex.: 'Preliminar', '1.2'.")
    parser.add_argument("--fundamentacao", default=None,
                        help="Texto da linha 'Fundamentação:' / 'Fonte:' na capa.")
    parser.add_argument("--rotulo-fundamentacao", default="Fundamentação",
                        choices=["Fundamentação", "Fonte"],
                        help="Rótulo da linha de fundamentação na capa.")
    parser.add_argument("--limpar-travessoes", action="store_true",
                        help="Substitui travessões (— e –) por vírgula/dois-pontos conforme regras .copilot.md.")
    parser.add_argument("--limpar-o-mesmo", action="store_true",
                        help="Substitui 'o mesmo' / 'a mesma' / 'os mesmos' / 'as mesmas' por ele/ela/eles/elas.")
    parser.add_argument("--var", action="append", default=[],
                        help="Variável KEY=VALUE para substituir {{KEY}} no documento. "
                             "Pode ser usado múltiplas vezes.")
    parser.add_argument("--vars", default=None,
                        help="Caminho de arquivo JSON com mapeamento chave→valor de variáveis.")
    args = parser.parse_args()

    # Monta dict de variáveis a partir de --vars (JSON) e --var KEY=VALUE.
    # --var sobrescreve --vars (linha de comando vence arquivo).
    variaveis = {}
    if args.vars:
        try:
            with open(args.vars, encoding="utf-8") as f:
                dados = json.load(f)
            if isinstance(dados, dict):
                variaveis.update({str(k): v for k, v in dados.items()})
            else:
                print(f"[AVISO] --vars: JSON em '{args.vars}' não é objeto, ignorado.")
        except Exception as exc:
            print(f"[ERRO] Falha ao ler --vars '{args.vars}': {exc}")
            sys.exit(1)
    for item in args.var or []:
        if "=" not in item:
            print(f"[AVISO] --var sem '=': '{item}' ignorado.")
            continue
        chave, valor = item.split("=", 1)
        variaveis[chave.strip()] = valor

    entrada = Path(args.entrada).resolve()
    saida = Path(args.saida).resolve()

    if not entrada.exists():
        print(f"[ERRO] Arquivo de entrada não encontrado: {entrada}")
        sys.exit(1)

    ext = entrada.suffix.lower()
    if ext == ".md":
        out = format_md(entrada, saida, titulo=args.titulo,
                        modulo=args.modulo, logo_path=args.logo,
                        processo=args.processo, acordao=args.acordao,
                        versao=args.versao, fundamentacao=args.fundamentacao,
                        rotulo_fundamentacao=args.rotulo_fundamentacao,
                        gerar_capa=not args.sem_capa,
                        validar=not args.sem_validacao,
                        gerar_checklist=not args.sem_checklist,
                        limpar_travessoes=args.limpar_travessoes,
                        limpar_o_mesmo=args.limpar_o_mesmo,
                        variaveis=variaveis or None)
    elif ext == ".docx":
        out = format_docx(entrada, saida, titulo=args.titulo,
                          modulo=args.modulo, logo_path=args.logo,
                          processo=args.processo, acordao=args.acordao,
                          versao=args.versao, fundamentacao=args.fundamentacao,
                          rotulo_fundamentacao=args.rotulo_fundamentacao,
                          gerar_capa=not args.sem_capa,
                          validar=not args.sem_validacao,
                          gerar_checklist=not args.sem_checklist,
                          limpar_travessoes=args.limpar_travessoes,
                          limpar_o_mesmo=args.limpar_o_mesmo,
                          variaveis=variaveis or None)
    else:
        print(f"[ERRO] Extensão não suportada: {ext} (use .md ou .docx)")
        sys.exit(1)

    print(f"[OK] Documento formatado: {out}")
    print(f"     Tamanho: {out.stat().st_size:,} bytes")


if __name__ == "__main__":
    main()
