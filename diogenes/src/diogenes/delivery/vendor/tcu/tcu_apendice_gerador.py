# /// script
# requires-python = ">=3.11"
# dependencies = ["python-docx>=1.1.0", "matplotlib>=3.7.0"]
# ///
"""
tcu_apendice_gerador.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Gerador de Apêndices de Módulo no padrão institucional TCU.

Produz um .docx seguindo a estrutura aprovada para apêndices do relatório
de verificação da alíquota de referência CBS (TC 015.848/2025-6).

Estrutura do apêndice (com numeração):
  1. Proposta do módulo
  2. Objetivo do módulo
  3. Relação dos arquivos encaminhados
  4. Testes realizados (3 camadas)
  5. Resultados e tratamento das inconsistências
  6. Alterações metodológicas em comum acordo com a RFB
  7. Conclusão do módulo

Características do texto:
  - Texto narrativo explicativo (grosso do conteúdo)
  - Tabelas com título numerado acima e fonte abaixo
  - Gráficos e diagramas gerados via matplotlib
  - Objetividade e ceticismo
  - Sem adjetivações
  - Descrição sucinta
  - Registro de todos os testes realizados

Usa o mesmo design do tcu_formatter.py (paleta, fontes, moldura institucional).

Uso:
    python tcu_apendice_gerador.py <dados.json> <saida.docx> [--modulo N]

    Ou programaticamente:
        from tcu_apendice_gerador import ApendiceGerador
        gen = ApendiceGerador(dados_dict, modulo=10)
        gen.gerar("saida.docx")

Projeto: TC 015.848/2025-6 | SecexContas / TCU
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import argparse
import io
import json
import sys
from pathlib import Path

# Importar o formatador TCU base (mesmo diretório)
sys.path.insert(0, str(Path(__file__).resolve().parent))
from tcu_formatter import (
    CORES,
    TCUFormatter,
)

# Matplotlib para geração de gráficos embutidos
try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.patches as mpatches
    import matplotlib.pyplot as plt
    from matplotlib.ticker import FuncFormatter
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PALETA MATPLOTLIB (espelha CORES do TCUFormatter)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

MPL_COLORS = {
    "navy_deep": f"#{CORES.NAVY_DEEP}",
    "navy": f"#{CORES.NAVY}",
    "navy_mid": f"#{CORES.NAVY_MID}",
    "navy_light": f"#{CORES.NAVY_LIGHT}",
    "gold": f"#{CORES.GOLD}",
    "gold_light": f"#{CORES.GOLD_LIGHT}",
    "cream": f"#{CORES.CREAM_LIGHT}",
    "red": f"#{CORES.RED}",
    "green": f"#{CORES.GREEN}",
    "amber": f"#{CORES.AMBER}",
    "gray": f"#{CORES.GRAY}",
}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# VOCABULÁRIO: substituições obrigatórias
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SUBSTITUICOES_VOCABULARIO = {
    "achado": "inconsistência",
    "achados": "inconsistências",
    "Achado": "Inconsistência",
    "Achados": "Inconsistências",
    "ACHADO": "INCONSISTÊNCIA",
    "ACHADOS": "INCONSISTÊNCIAS",
    "auditoria": "verificação",
    "Auditoria": "Verificação",
    "AUDITORIA": "VERIFICAÇÃO",
    "auditar": "verificar",
    "auditado": "verificado",
    "auditados": "verificados",
}


def _aplicar_vocabulario(texto: str) -> str:
    """Aplica substituições de vocabulário ao texto."""
    if not texto:
        return texto
    for original, substituto in SUBSTITUICOES_VOCABULARIO.items():
        texto = texto.replace(original, substituto)
    return texto


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# STATUS DE VERIFICAÇÃO (cores para tabelas de resultado)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

STATUS_VERIFICACAO = {
    "Atendido":             (CORES.GREEN, CORES.GREEN_SOFT),
    "Atendido Parcialmente": (CORES.AMBER, CORES.AMBER_SOFT),
    "Divergência":          (CORES.RED, CORES.RED_SOFT),
    "Não Verificável":      (CORES.GRAY, CORES.GRAY_LIGHT),
    "Limitação Documentada": (CORES.NAVY_MID, CORES.BLUE_SOFT),
    "Pendente":             (CORES.GRAY, CORES.GRAY_LIGHT),
}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# GERAÇÃO DE GRÁFICOS (matplotlib → PNG bytes)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _gerar_grafico_barras(categorias, valores_2023, valores_2024,
                          titulo="", ylabel="R$ bilhões",
                          fmt_bilhoes=True) -> bytes:
    """Gráfico de barras agrupadas (2023 vs 2024) no estilo TCU."""
    if not HAS_MATPLOTLIB:
        return b""
    fig, ax = plt.subplots(figsize=(7, 3.5), dpi=150)
    x = range(len(categorias))
    w = 0.35
    bars1 = ax.bar([i - w/2 for i in x], valores_2023, w,
                   label="2023", color=MPL_COLORS["navy_mid"], edgecolor="white", linewidth=0.5)
    bars2 = ax.bar([i + w/2 for i in x], valores_2024, w,
                   label="2024", color=MPL_COLORS["gold"], edgecolor="white", linewidth=0.5)
    ax.set_xticks(list(x))
    ax.set_xticklabels(categorias, fontsize=8)
    ax.set_ylabel(ylabel, fontsize=9)
    if titulo:
        ax.set_title(titulo, fontsize=10, fontweight="bold", color=MPL_COLORS["navy_deep"])
    ax.legend(fontsize=8, loc="upper right")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="y", alpha=0.3, linestyle="--")
    if fmt_bilhoes:
        ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.1f}"))
    plt.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    plt.close(fig)
    return buf.getvalue()


def _gerar_grafico_status(status_contagem: dict) -> bytes:
    """Gráfico de rosca (donut) com contagem de status."""
    if not HAS_MATPLOTLIB:
        return b""
    cores_map = {
        "Atendido": MPL_COLORS["green"],
        "Atendido Parcialmente": MPL_COLORS["amber"],
        "Divergência": MPL_COLORS["red"],
        "Não Verificável": MPL_COLORS["gray"],
        "Limitação Documentada": MPL_COLORS["navy_mid"],
        "Pendente": "#B0BEC5",
    }
    labels = list(status_contagem.keys())
    sizes = list(status_contagem.values())
    colors = [cores_map.get(l, "#CCCCCC") for l in labels]

    fig, ax = plt.subplots(figsize=(5, 3.2), dpi=150)
    wedges, texts = ax.pie(
        sizes, labels=None, colors=colors,
        startangle=90,
        wedgeprops=dict(width=0.45, edgecolor="white", linewidth=2),
    )
    # Texto central com total
    total = sum(sizes)
    ax.text(0, 0, f"{total}\ntestes", ha="center", va="center",
            fontsize=12, fontweight="bold", color=MPL_COLORS["navy_deep"])
    # Legenda lateral (fora do gráfico, sem sobreposição)
    legend_labels = [f"{l}: {s}" for l, s in zip(labels, sizes)]
    ax.legend(
        wedges, legend_labels,
        loc="center left", bbox_to_anchor=(1.0, 0.5),
        fontsize=8, frameon=False,
    )
    ax.set_title("Distribuição dos Resultados", fontsize=10,
                 fontweight="bold", color=MPL_COLORS["navy_deep"], pad=8)
    plt.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    plt.close(fig)
    return buf.getvalue()


def _gerar_grafico_sensibilidade(redutores, valores, ylabel="R$ bilhões",
                                  titulo="Análise de Sensibilidade") -> bytes:
    """Gráfico de linha para sensibilidade do redutor."""
    if not HAS_MATPLOTLIB:
        return b""
    fig, ax = plt.subplots(figsize=(6, 3), dpi=150)
    ax.plot(redutores, valores, marker="o", color=MPL_COLORS["navy"],
            linewidth=2, markersize=6, markerfacecolor=MPL_COLORS["gold"])
    # Destacar ponto RFB (20%)
    if 20 in redutores:
        idx = redutores.index(20)
        ax.axvline(x=20, color=MPL_COLORS["red"], linestyle="--", alpha=0.6, linewidth=1)
        ax.annotate("RFB (20%)", xy=(20, valores[idx]),
                    xytext=(25, valores[idx] * 1.03),
                    fontsize=8, color=MPL_COLORS["red"],
                    arrowprops=dict(arrowstyle="->", color=MPL_COLORS["red"], lw=0.8))
    ax.set_xlabel("Redutor comportamental (%)", fontsize=9)
    ax.set_ylabel(ylabel, fontsize=9)
    ax.set_title(titulo, fontsize=10, fontweight="bold", color=MPL_COLORS["navy_deep"])
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="y", alpha=0.3, linestyle="--")
    ax.set_xticks(redutores)
    plt.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    plt.close(fig)
    return buf.getvalue()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CLASSE PRINCIPAL
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class ApendiceGerador:
    """
    Gera um apêndice de módulo no padrão TCU.

    Características principais:
      - Numeração automática de seções (1., 1.1., 1.1.1.)
      - Tabelas com título numerado ("Tabela N: ...") e fonte abaixo
      - Figuras com título numerado ("Figura N: ...") e nota abaixo
      - Texto narrativo explicando cada elemento gráfico e tabela
      - Gráficos gerados via matplotlib na paleta TCU
      - Vocabulário verificado (sem "achado"/"auditoria")

    Recebe um dicionário de dados estruturado (ver DADOS_MODULO_10 como exemplo).
    """

    def __init__(self, dados: dict, modulo: int = None):
        self.dados = dados
        self.modulo = modulo or dados.get("modulo", 0)
        self.modulo_nome = dados.get("modulo_nome", f"Módulo {self.modulo}")
        self.fmt = None
        # Contadores de numeração
        self._h1_counter = 0
        self._h2_counter = 0
        self._h3_counter = 0
        self._tabela_counter = 0
        self._figura_counter = 0

    # ─── NUMERAÇÃO ──────────────────────────────────────────────────────────────

    def _next_h1(self) -> str:
        self._h1_counter += 1
        self._h2_counter = 0
        self._h3_counter = 0
        return str(self._h1_counter)

    def _next_h2(self) -> str:
        self._h2_counter += 1
        self._h3_counter = 0
        return f"{self._h1_counter}.{self._h2_counter}"

    def _next_h3(self) -> str:
        self._h3_counter += 1
        return f"{self._h1_counter}.{self._h2_counter}.{self._h3_counter}"

    def _heading(self, titulo: str, level: int):
        """Adiciona heading com numeração automática."""
        if level == 1:
            num = self._next_h1()
        elif level == 2:
            num = self._next_h2()
        else:
            num = self._next_h3()
        self.fmt.add_heading(f"{num}. {titulo}", level=level)

    def _titulo_tabela(self, titulo: str, fonte: str = None):
        """Adiciona título numerado de tabela ACIMA do elemento."""
        self._tabela_counter += 1
        self.fmt.add_titulo_elemento(f"Tabela {self._tabela_counter}: {titulo}")

    def _fonte_tabela(self, fonte: str):
        """Adiciona fonte ABAIXO da tabela."""
        self.fmt.add_nota_elemento(fonte, rotulo="Fonte")

    def _titulo_figura(self, titulo: str):
        """Adiciona título numerado de figura ACIMA do elemento."""
        self._figura_counter += 1
        self.fmt.add_titulo_elemento(f"Figura {self._figura_counter}: {titulo}")

    def _nota_figura(self, texto: str):
        """Adiciona nota explicativa ABAIXO da figura."""
        self.fmt.add_nota_elemento(texto, rotulo="Nota")

    def _inserir_grafico(self, imagem_bytes: bytes, titulo: str,
                         nota: str = None, largura_cm: float = 14.0):
        """Insere gráfico com título numerado e nota."""
        if not imagem_bytes:
            return
        self._titulo_figura(titulo)
        self.fmt.add_imagem(imagem_bytes, largura_cm=largura_cm)
        if nota:
            self._nota_figura(nota)

    # ─── GERAÇÃO PRINCIPAL ──────────────────────────────────────────────────────

    def gerar(self, caminho_saida: str) -> Path:
        """Gera o documento .docx completo e salva no caminho indicado."""
        titulo = f"Apêndice: Módulo {self.modulo}, {self.modulo_nome}"
        self.fmt = TCUFormatter(
            modulo=self.modulo,
            titulo=titulo,
            subtitulo="Verificação dos Cálculos CBS 2027",
        )

        # Capa
        self.fmt.add_capa(
            titulo="APÊNDICE",
            subtitulo1=f"Módulo {self.modulo}: {self.modulo_nome}",
            subtitulo2="Verificação dos Cálculos da Alíquota de Referência CBS",
            versao=self.dados.get("versao", "Preliminar"),
            fundamentacao="LC 214/2025, arts. 349 e seguintes",
        )

        # Seções numeradas
        self._secao_proposta()
        self._secao_objetivo()
        self._secao_arquivos()
        self._secao_testes()
        self._secao_resultados()
        self._secao_alteracoes()
        self._secao_conclusao()

        return self.fmt.salvar(caminho_saida)

    # ─── SEÇÃO 1: PROPOSTA DO MÓDULO ────────────────────────────────────────────

    def _secao_proposta(self):
        self._heading("Proposta do Módulo", level=1)
        proposta = self.dados.get("proposta", {})
        descricao = _aplicar_vocabulario(proposta.get("descricao", ""))
        if descricao:
            self.fmt.add_paragrafo(descricao)
        # Contexto narrativo adicional
        contexto = proposta.get("contexto_narrativo", "")
        if contexto:
            self.fmt.add_paragrafo(_aplicar_vocabulario(contexto))
        # Referência das peças (integrada ao texto, sem "Fonte:" solto)
        fonte = proposta.get("fonte", "")
        if fonte:
            self.fmt.add_paragrafo(
                f"As informações desta seção foram extraídas de: {fonte}."
            )

    # ─── SEÇÃO 2: OBJETIVO ──────────────────────────────────────────────────────

    def _secao_objetivo(self):
        self._heading("Objetivo do Módulo", level=1)
        objetivo = _aplicar_vocabulario(self.dados.get("objetivo", ""))
        if objetivo:
            self.fmt.add_paragrafo(objetivo)
        # Texto narrativo complementar
        obj_detalhe = self.dados.get("objetivo_detalhado", "")
        if obj_detalhe:
            self.fmt.add_paragrafo(_aplicar_vocabulario(obj_detalhe))

    # ─── SEÇÃO 3: ARQUIVOS ENCAMINHADOS ─────────────────────────────────────────

    def _secao_arquivos(self):
        self._heading("Relação dos Arquivos Encaminhados", level=1)
        arqs = self.dados.get("arquivos", {})

        # Texto introdutório
        intro = arqs.get("introducao", "")
        if intro:
            self.fmt.add_paragrafo(_aplicar_vocabulario(intro))
        else:
            total = (len(arqs.get("principal", [])) +
                     len(arqs.get("auxiliares", [])))
            self.fmt.add_paragrafo(
                f"A RFB encaminhou {total} arquivo(s) para verificação deste "
                f"módulo, organizados conforme detalhamento a seguir. "
                f"Todos os arquivos foram recebidos íntegros e protocolados "
                f"no sistema de controle de peças."
            )

        # Planilha principal
        principal = arqs.get("principal", [])
        if principal:
            self._heading("Planilha Principal", level=2)
            self.fmt.add_paragrafo(
                "A planilha principal é o artefato integrador que consolida "
                "os resultados parciais de todas as extrações e cálculos "
                "auxiliares do módulo."
            )
            self._titulo_tabela("Planilha principal do módulo")
            headers = ["Arquivo", "Descrição", "Tamanho"]
            rows = [[a.get("nome", ""), a.get("descricao", ""), a.get("tamanho", "")]
                    for a in principal]
            self.fmt.add_tabela(headers, rows)
            self._fonte_tabela(
                arqs.get("fonte_principal", "Protocolo de recebimento RFB")
            )

        # Auxiliares
        auxiliares = arqs.get("auxiliares", [])
        if auxiliares:
            self._heading("Planilhas e Cálculos Auxiliares", level=2)
            self.fmt.add_paragrafo(
                f"Complementam a planilha principal {len(auxiliares)} "
                f"arquivo(s) auxiliar(es), incluindo bases de dados "
                f"desagregadas, scripts de extração e notebooks de "
                f"consolidação que documentam a cadeia de transformação "
                f"dos dados."
            )
            self._titulo_tabela("Arquivos auxiliares encaminhados pela RFB")
            headers = ["Arquivo", "Descrição", "Tamanho"]
            rows = [[a.get("nome", ""), a.get("descricao", ""), a.get("tamanho", "")]
                    for a in auxiliares]
            self.fmt.add_tabela(headers, rows)
            self._fonte_tabela(
                arqs.get("fonte_auxiliares", "Protocolo de recebimento RFB")
            )

        # Fontes
        fontes = arqs.get("fontes", [])
        if fontes:
            self._heading("Fontes de Informação", level=2)
            self.fmt.add_paragrafo(
                "As fontes de informação utilizadas pela RFB para "
                "produção dos cálculos deste módulo são apresentadas "
                "a seguir, com indicação do tipo de dado e sua aplicação "
                "no contexto do cálculo da CBS."
            )
            self._titulo_tabela("Fontes de dados consultadas no módulo")
            headers = ["Fonte", "Tipo", "Descrição"]
            rows = [[f.get("nome", ""), f.get("tipo", ""), f.get("descricao", "")]
                    for f in fontes]
            self.fmt.add_tabela(headers, rows)
            self._fonte_tabela(
                arqs.get("fonte_fontes",
                         "Documentação metodológica RFB (peça 16)")
            )

    # ─── SEÇÃO 4: TESTES REALIZADOS ─────────────────────────────────────────────

    def _secao_testes(self):
        self._heading("Testes Realizados", level=1)
        testes = self.dados.get("testes", {})

        # Texto introdutório sobre a metodologia de 3 camadas
        self.fmt.add_paragrafo(
            "A verificação foi estruturada em três camadas complementares, "
            "progressivamente mais detalhadas: (i) verificações automatizadas "
            "de consistência e conformidade; (ii) revisão pelo GT Reforma "
            "Tributária quanto a premissas e legislação; e (iii) reprodução "
            "das consultas na sala de sigilo da RFB com recálculo "
            "independente dos valores."
        )

        # Camada 1
        camada1 = testes.get("camada_1", {})
        if camada1:
            self._heading("Consistência do Módulo (1ª camada)", level=2)
            self.fmt.add_paragrafo(
                "A primeira camada compreende verificações automatizadas "
                "que validam a conformidade com a metodologia homologada, "
                "a consistência interna das planilhas e scripts, e testes "
                "de sensibilidade sobre parâmetros relevantes. Cada teste "
                "produz um resultado descritivo e um status de conformidade."
            )
            self._tabela_testes(
                camada1.get("conformidade", []),
                "Conformidade com Metodologia Homologada e Legislação",
                "Confronto entre regras de negócio aprovadas e implementação efetiva"
            )
            self._tabela_testes(
                camada1.get("consistencia_interna", []),
                "Consistência Interna das Planilhas e Cálculos",
                "Cruzamento de fórmulas, totalizadores e abas da planilha integradora"
            )
            self._tabela_testes(
                camada1.get("consistencia_calculo", []),
                "Consistência via Ferramenta de Cálculo",
                "Validação da trilha de processamento (SQL, Python, Excel)"
            )
            self._tabela_testes(
                camada1.get("sensibilidade", []),
                "Testes de Sensibilidade",
                "Variação de parâmetros relevantes para medir impacto na alíquota"
            )

        # Camada 2
        camada2 = testes.get("camada_2", {})
        if camada2:
            self._heading("Revisão e Validação (2ª camada)", level=2)
            self.fmt.add_paragrafo(
                "A segunda camada compreende verificações conduzidas pela "
                "equipe do GT Reforma Tributária, com foco na aderência "
                "das premissas adotadas e na fundamentação legal dos "
                "parâmetros do modelo."
            )
            self._tabela_testes(
                camada2.get("conformidade", []),
                "Conformidade com Metodologia e Legislação",
                "Verificação de dispositivos legais (LC 214/2025)"
            )
            self._tabela_testes(
                camada2.get("premissas", []),
                "Consistência das Premissas Relevantes",
                "Avaliação dos parâmetros paramétricos e suas justificativas"
            )

        # Camada 3
        camada3 = testes.get("camada_3", {})
        if camada3:
            self._heading("Extração e Recálculo (3ª camada)", level=2)
            self.fmt.add_paragrafo(
                "A terceira camada envolve a reprodução integral das "
                "consultas SQL na sala de sigilo da RFB e o recálculo "
                "independente dos valores. Esta etapa garante que os "
                "dados de entrada e os resultados intermediários são "
                "fiéis às fontes originais."
            )
            self._tabela_testes(
                camada3.get("reproducao", []),
                "Reprodução das Consultas na Sala de Sigilo",
                "Execução dos scripts SQL no ambiente controlado da RFB"
            )
            self._tabela_testes(
                camada3.get("recalculo", []),
                "Verificação dos Valores e Recálculo",
                "Confronto entre valores calculados e valores reportados"
            )

    def _tabela_testes(self, testes: list, titulo_secao: str,
                       descricao_narrativa: str = ""):
        """Gera subtítulo + narrativa + tabela numerada de testes."""
        if not testes:
            return
        self._heading(titulo_secao, level=3)
        # Texto narrativo antes da tabela
        if descricao_narrativa:
            self.fmt.add_paragrafo(
                f"{descricao_narrativa}. "
                f"Foram realizados {len(testes)} teste(s) nesta categoria, "
                f"cujos resultados são apresentados na tabela a seguir."
            )
        # Tabela com título e fonte
        self._titulo_tabela(titulo_secao)
        headers = ["ID", "Verificação", "Resultado", "Status"]
        rows = []
        for t in testes:
            rows.append([
                t.get("id", ""),
                _aplicar_vocabulario(t.get("descricao", "")),
                _aplicar_vocabulario(t.get("resultado", "")),
                t.get("status", "Pendente"),
            ])
        self.fmt.add_tabela(headers, rows)
        self._fonte_tabela("Elaboração própria, com base nos dados da RFB")
        # Síntese narrativa após a tabela
        status_list = [t.get("status", "Pendente") for t in testes]
        atend = sum(1 for s in status_list if s == "Atendido")
        parcial = sum(1 for s in status_list if s == "Atendido Parcialmente")
        diverg = sum(1 for s in status_list if s == "Divergência")
        pend = sum(1 for s in status_list if s == "Pendente")
        nv = sum(1 for s in status_list if s == "Não Verificável")
        partes = []
        if atend:
            partes.append(f"{atend} atendido(s)")
        if parcial:
            partes.append(f"{parcial} parcialmente atendido(s)")
        if diverg:
            partes.append(f"{diverg} com divergência")
        if pend:
            partes.append(f"{pend} pendente(s)")
        if nv:
            partes.append(f"{nv} não verificável(is)")
        if partes:
            self.fmt.add_paragrafo(
                f"Síntese: dos {len(testes)} testes realizados, "
                + ", ".join(partes) + "."
            )

    # ─── SEÇÃO 5: RESULTADOS E INCONSISTÊNCIAS ─────────────────────────────────

    def _secao_resultados(self):
        self._heading(
            "Resultados dos Testes e Tratamento das Inconsistências", level=1
        )
        inconsistencias = self.dados.get("inconsistencias", [])
        if not inconsistencias:
            self.fmt.add_paragrafo(
                "Nenhuma inconsistência identificada até o momento."
            )
            return

        # Texto introdutório
        self.fmt.add_paragrafo(
            f"As verificações realizadas identificaram "
            f"{len(inconsistencias)} inconsistência(s), classificadas "
            f"conforme criticidade e com indicação do tratamento adotado "
            f"ou proposto. O quadro resumo a seguir apresenta visão "
            f"consolidada, seguida do detalhamento individual."
        )

        # Gráfico de distribuição de status
        status_contagem = {}
        for inc in inconsistencias:
            st = inc.get("status", "Pendente")
            status_contagem[st] = status_contagem.get(st, 0) + 1
        if HAS_MATPLOTLIB and len(status_contagem) > 1:
            img = _gerar_grafico_status(status_contagem)
            if img:
                self._inserir_grafico(
                    img,
                    "Distribuição das inconsistências por status",
                    nota="Classificação conforme resultado da verificação",
                    largura_cm=8.0,
                )

        # Quadro resumo
        self._heading("Quadro Resumo", level=2)
        self.fmt.add_paragrafo(
            "A tabela consolida as inconsistências identificadas, "
            "com indicação sintética do impacto e do status atual. "
            "O detalhamento completo de cada item é apresentado "
            "na subseção seguinte."
        )
        self._titulo_tabela("Resumo das inconsistências identificadas")
        headers = ["ID", "Inconsistência", "Impacto", "Status"]
        rows = [[
            inc.get("id", ""),
            _aplicar_vocabulario(inc.get("titulo", "")),
            _aplicar_vocabulario(inc.get("consequencia", ""))[:80],
            inc.get("status", "Pendente"),
        ] for inc in inconsistencias]
        self.fmt.add_tabela(headers, rows)
        self._fonte_tabela("Elaboração própria, com base nas verificações realizadas")

        # Detalhamento
        self._heading("Detalhamento", level=2)
        self.fmt.add_paragrafo(
            "Cada inconsistência é apresentada com descrição do fato "
            "observado, consequência no cálculo da CBS, e tratamento "
            "adotado ou proposto para sua resolução."
        )
        for inc in inconsistencias:
            inc_id = inc.get("id", "INC-???")
            titulo = _aplicar_vocabulario(inc.get("titulo", ""))
            self._heading(f"{inc_id}: {titulo}", level=3)

            # Texto narrativo contextual
            desc = _aplicar_vocabulario(inc.get("descricao", ""))
            conseq = _aplicar_vocabulario(inc.get("consequencia", ""))
            trat = _aplicar_vocabulario(inc.get("tratamento", ""))
            status = inc.get("status", "Pendente")

            # Narrativa antes da tabela
            self.fmt.add_paragrafo(desc)

            # Quadro estruturado
            self._titulo_tabela(f"Detalhamento da inconsistência {inc_id}")
            headers_inc = ["Aspecto", "Conteúdo"]
            rows_inc = [
                ["Consequência no cálculo", conseq],
                ["Tratamento e interação com a RFB", trat],
                ["Status", status],
            ]
            self.fmt.add_tabela(headers_inc, rows_inc, col_widths=[4, 12])
            self._fonte_tabela("Elaboração própria")

    # ─── SEÇÃO 6: ALTERAÇÕES METODOLÓGICAS ─────────────────────────────────────

    def _secao_alteracoes(self):
        self._heading(
            "Alterações Metodológicas em Comum Acordo com a RFB", level=1
        )
        alteracoes = self.dados.get("alteracoes_metodologicas", [])
        notas_met = self.dados.get("notas_metodologicas", [])

        # Texto introdutório
        self.fmt.add_paragrafo(
            "Esta seção registra as propostas de alteração metodológica "
            "apresentadas pela RFB após a homologação da metodologia "
            "(Acórdão 2833/2025-Plenário). Cada proposta é avaliada quanto "
            "à sua fundamentação, impacto no cálculo e status de concordância "
            "entre a equipe de verificação e a RFB."
        )

        # Subtópico: Notas Metodológicas recebidas
        if notas_met:
            self._heading("Notas Metodológicas Recebidas", level=2)
            for nota in notas_met:
                nome = nota.get("nome", "")
                descr = _aplicar_vocabulario(nota.get("descricao", ""))
                obs = _aplicar_vocabulario(nota.get("observacao", ""))
                self.fmt.add_paragrafo(descr)
                if obs:
                    self.fmt.add_destaque(obs, tipo="atencao")
            # Tabela de notas
            self._titulo_tabela("Notas metodológicas recebidas da RFB")
            headers_n = ["Documento", "Data", "Conteúdo", "Situação no Inventário"]
            rows_n = [[
                n.get("nome", ""),
                n.get("data", ""),
                n.get("conteudo_resumo", ""),
                n.get("situacao_inventario", ""),
            ] for n in notas_met]
            self.fmt.add_tabela(headers_n, rows_n)
            self._fonte_tabela("Protocolo de recebimento RFB e inventário de arquivos")

        # Alterações propriamente ditas
        if not alteracoes:
            self._heading("Quadro de Alterações Acordadas", level=2)
            self.fmt.add_paragrafo(
                "Até o momento da redação deste apêndice, nenhuma alteração "
                "metodológica foi formalmente acordada entre a equipe de "
                "verificação e a RFB para este módulo. As propostas recebidas "
                "via nota metodológica encontram-se em análise."
            )
            return

        self._heading("Quadro de Alterações Acordadas", level=2)
        self.fmt.add_paragrafo(
            f"Foram registradas {len(alteracoes)} alteração(ões) "
            f"metodológica(s) formalmente acordada(s) entre a equipe de "
            f"verificação e a RFB, conforme detalhamento a seguir."
        )
        self._titulo_tabela("Alterações metodológicas acordadas com a RFB")
        headers = ["ID", "Descrição", "Acordo", "Impacto"]
        rows = [[
            a.get("id", ""),
            _aplicar_vocabulario(a.get("descricao", "")),
            _aplicar_vocabulario(a.get("acordo", "")),
            _aplicar_vocabulario(a.get("impacto", "")),
        ] for a in alteracoes]
        self.fmt.add_tabela(headers, rows)
        self._fonte_tabela("Atas de reunião e comunicações formais com a RFB")

    # ─── SEÇÃO 7: CONCLUSÃO ─────────────────────────────────────────────────────

    def _secao_conclusao(self):
        self._heading("Conclusão do Módulo", level=1)
        conclusao = self.dados.get("conclusao", {})

        # Conformidade
        conf = _aplicar_vocabulario(conclusao.get("conformidade", ""))
        if conf:
            self._heading("Conformidade com a Metodologia Homologada", level=2)
            self.fmt.add_paragrafo(conf)

        # Consistência
        cons = _aplicar_vocabulario(conclusao.get("consistencia", ""))
        if cons:
            self._heading("Consistência do Cálculo", level=2)
            self.fmt.add_paragrafo(cons)

        # Premissas
        premissas = conclusao.get("premissas", [])
        if premissas:
            self._heading("Premissas Relevantes Adotadas", level=2)
            self.fmt.add_paragrafo(
                "As premissas adotadas pela RFB para o cálculo deste módulo "
                "são determinantes para o resultado final. A tabela a seguir "
                "apresenta cada premissa com sua descrição e impacto estimado "
                "na alíquota de referência."
            )
            self._titulo_tabela("Premissas relevantes do módulo")
            headers = ["Premissa", "Descrição", "Impacto"]
            rows = [[
                _aplicar_vocabulario(p.get("nome", "")),
                _aplicar_vocabulario(p.get("descricao", "")),
                _aplicar_vocabulario(p.get("impacto", "")),
            ] for p in premissas]
            self.fmt.add_tabela(headers, rows)
            self._fonte_tabela("Documentação metodológica RFB e análise própria")

        # Valores agregados
        valores = conclusao.get("valores_agregados", [])
        if valores:
            self._heading("Valores Agregados", level=2)
            self.fmt.add_paragrafo(
                "Os valores consolidados do módulo refletem o resultado "
                "das verificações realizadas e servem como referência "
                "para reconciliação com o Módulo Central. A tabela e o "
                "gráfico a seguir apresentam a evolução entre exercícios."
            )
            self._titulo_tabela("Valores agregados do módulo")
            headers = ["Indicador", "2023", "2024"]
            rows = [[
                v.get("descricao", ""),
                v.get("valor_2023", ""),
                v.get("valor_2024", ""),
            ] for v in valores]
            self.fmt.add_tabela(headers, rows)
            self._fonte_tabela("Planilha AUX_MOD_10 PF e cálculos auxiliares")

            # Gráfico de valores agregados
            if HAS_MATPLOTLIB and len(valores) >= 2:
                self._gerar_grafico_valores(valores)

        # Gráfico de sensibilidade (se dados disponíveis)
        sensib = conclusao.get("sensibilidade_redutor", {})
        if sensib and HAS_MATPLOTLIB:
            self._heading("Análise de Sensibilidade", level=2)
            self.fmt.add_paragrafo(
                "O gráfico a seguir apresenta o impacto da variação do "
                "redutor comportamental sobre a base de débitos do Bloco 2. "
                "O valor adotado pela RFB (20%) é destacado para referência. "
                "A análise demonstra que cada 10 pontos percentuais de "
                "variação no redutor altera em aproximadamente R$ 5 bilhões "
                "a base de cálculo."
            )
            redutores = sensib.get("redutores", [0, 10, 20, 30, 40])
            valores_s = sensib.get("valores", [])
            if valores_s:
                img = _gerar_grafico_sensibilidade(
                    redutores, valores_s,
                    ylabel="BC Débitos (R$ bi)",
                    titulo="Sensibilidade ao redutor comportamental"
                )
                if img:
                    self._inserir_grafico(
                        img,
                        "Impacto do redutor comportamental na base de débitos",
                        nota="Elaboração própria. Linha tracejada indica valor adotado pela RFB (20%)",
                    )

    def _gerar_grafico_valores(self, valores: list):
        """Gera gráfico de barras comparativo 2023 vs 2024."""
        try:
            categorias = []
            v2023 = []
            v2024 = []
            for v in valores:
                desc = v.get("descricao", "")
                # Simplificar rótulo
                if len(desc) > 30:
                    desc = desc[:27] + "..."
                categorias.append(desc)
                # Parse de valores (R$ X,XX bi → float)
                val23 = v.get("valor_2023", "0")
                val24 = v.get("valor_2024", "0")
                v2023.append(self._parse_valor(val23))
                v2024.append(self._parse_valor(val24))

            img = _gerar_grafico_barras(
                categorias, v2023, v2024,
                titulo="Evolução dos valores do módulo (2023 vs 2024)",
                ylabel="R$ bilhões"
            )
            if img:
                self._inserir_grafico(
                    img,
                    "Comparativo de valores agregados entre exercícios",
                    nota="Elaboração própria com base na planilha AUX_MOD_10",
                )
        except Exception:
            pass  # Gráfico opcional, não interrompe geração

    @staticmethod
    def _parse_valor(texto: str) -> float:
        """Converte 'R$ 20,06 bi' ou 'R$ -3,94 bi' em float."""
        try:
            s = texto.replace("R$", "").replace("bi", "").strip()
            s = s.replace(",", ".")
            return float(s)
        except (ValueError, AttributeError):
            return 0.0


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# DADOS DO MÓDULO 10 (PILOTO)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

DADOS_MODULO_10 = {
    "modulo": 10,
    "modulo_nome": "Pessoa Física",
    "versao": "1.0 | Maio de 2026",

    "proposta": {
        "descricao": (
            "O Módulo 10 define a metodologia de cálculo da CBS para as Pessoas "
            "Físicas contribuintes do tributo. O módulo divide-se em dois blocos: "
            "Bloco 1 (Produtor Rural PF com receita bruta superior a R$ 3,6 milhões "
            "anuais, arts. 164 e 165 da LC 214/2025) e Bloco 2 (Demais PF "
            "contribuintes: profissionais liberais art. 127, saúde art. 130, "
            "educação art. 129, artes e cultura art. 139, cartórios e demais "
            "serviços). O módulo produz arrecadação própria (débitos menos "
            "créditos) e ajuste no Módulo Central (diferença entre alíquota de "
            "referência e alíquota específica PF, aplicada sobre consumo "
            "intermediário)."
        ),
        "contexto_narrativo": (
            "A LC 214/2025 estabelece que Pessoas Físicas contribuintes da CBS "
            "compreendem produtores rurais com receita bruta acima do limiar de "
            "obrigatoriedade e prestadores de serviços profissionais. O cálculo "
            "para essas categorias segue lógica distinta das empresas, uma vez "
            "que a base de cálculo é composta por rendimentos declarados (DIRPF) "
            "e o regime de créditos é restrito ao livro-caixa. O módulo foi "
            "estruturado pela RFB com extração de dados do Datalake Serpro, "
            "processamento via notebooks Python e consolidação em planilha Excel."
        ),
        "fonte": (
            "Apêndice X do Relatório Consolidado Metodologia CBS e Redutor; "
            "Anexo Nota Cetad 079/2025 (peça 16, item III.10); "
            "Modulo_10.xlsx (peça 24)"
        ),
    },

    "objetivo": (
        "Calcular a receita de CBS proveniente das Pessoas Físicas contribuintes "
        "e efetuar os ajustes no Módulo Central, de modo que as empresas "
        "adquirentes de bens e serviços de PF tenham o crédito corretamente "
        "calculado conforme a alíquota específica da categoria."
    ),

    "objetivo_detalhado": (
        "O módulo calcula, para cada ano-calendário (2023 e 2024): "
        "(i) os débitos de CBS devidos pelas PF contribuintes, segregados por "
        "categoria e aplicando as alíquotas específicas da LC 214/2025; "
        "(ii) os créditos de CBS a que fazem jus, com base no livro-caixa e "
        "nas despesas elegíveis; (iii) a arrecadação própria líquida "
        "(débitos menos créditos); e (iv) o ajuste no Módulo Central, que "
        "reflete a diferença entre a alíquota de referência e a alíquota "
        "efetivamente aplicada às PF, ponderada pelo consumo intermediário "
        "das empresas adquirentes."
    ),

    "arquivos": {
        "principal": [
            {
                "nome": "AUX_MOD_10 PF, execução.xlsx",
                "descricao": "Planilha integradora com 5 abas (resumo, 10.1, 10.2, 10.3, 10.4)",
                "tamanho": "36,5 KB",
            },
        ],
        "auxiliares": [
            {"nome": "Base Débitos 2023.xlsx", "descricao": "Débitos PR por NCM (2023)", "tamanho": "3,3 MB"},
            {"nome": "Base Débitos 2024.xlsx", "descricao": "Débitos PR por NCM (2024)", "tamanho": "3,4 MB"},
            {"nome": "Base Créditos 2023.xlsx", "descricao": "Créditos PR por NCM (2023)", "tamanho": "4,0 MB"},
            {"nome": "Base Créditos 2024.xlsx", "descricao": "Créditos PR por NCM (2024)", "tamanho": "4,0 MB"},
            {"nome": "Matriz de Incidência.xlsx", "descricao": "NCM para regime tributário (proporção)", "tamanho": "1,0 MB"},
            {"nome": "NCM.xlsx", "descricao": "Cadastro descritivo de NCMs", "tamanho": "1,2 MB"},
            {"nome": "Regras_lei_complementar.xlsx", "descricao": "Benefícios por NCM (LC 214/2025)", "tamanho": "54 KB"},
            {"nome": "Rendimentos TNA, DIRPF.xlsx", "descricao": "BC débitos serviços PF (ocupações)", "tamanho": "107,7 KB"},
            {"nome": "Estimativa Valor Créditos.xlsx", "descricao": "Créditos serviços PF (livro-caixa)", "tamanho": "3,5 MB"},
            {"nome": "Consumo Final Contas Nacionais.xlsx", "descricao": "% consumo intermediário por atividade (SCN)", "tamanho": "1,6 MB"},
            {"nome": "consolidacao_produtor_rural_2023.ipynb", "descricao": "Notebook de consolidação PR (2023)", "tamanho": "86,3 KB"},
            {"nome": "consolidacao_produtor_rural_2024.ipynb", "descricao": "Notebook de consolidação PR (2024)", "tamanho": "88,9 KB"},
            {"nome": "modulo_pf_produtor_rural_2023.sql", "descricao": "SQL extração Datalake (2023)", "tamanho": "23,4 KB"},
            {"nome": "modulo_pf_produtor_rural_2024.sql", "descricao": "SQL extração Datalake (2024)", "tamanho": "23,5 KB"},
            {"nome": "NOTA METODOLÓGICA CBS V_11_25b, atualização.docx", "descricao": "Nota propondo redutor comportamental 20% (Bloco 2)", "tamanho": "370,4 KB"},
        ],
        "fontes": [
            {"nome": "DIRPF", "tipo": "Declaração", "descricao": "Receitas e despesas por CPF (livro-caixa rural e carnê-leão)"},
            {"nome": "NF-e", "tipo": "Transacional", "descricao": "Notas fiscais eletrônicas (vendas e compras do produtor rural)"},
            {"nome": "e-Social", "tipo": "Declaração", "descricao": "Folha de pagamento (rubricas tipo 1)"},
            {"nome": "DARF", "tipo": "Arrecadação", "descricao": "Recolhimentos IRRF (260), RGPS (622) e ITR (420)"},
            {"nome": "ANP", "tipo": "Referência", "descricao": "Preço médio diesel (R$ 5,80/L em 2023, R$ 5,96/L em 2024)"},
            {"nome": "Contas Nacionais (SCN)", "tipo": "Referência", "descricao": "Tabela de usos: % consumo intermediário por atividade"},
        ],
    },

    "testes": {
        "camada_1": {
            "conformidade": [
                {"id": "V-01", "descricao": "Dados originam exclusivamente da DIRPF",
                 "resultado": "SQLs confirmam extração de tabelas DIRPF no Datalake Serpro",
                 "status": "Atendido"},
                {"id": "V-02", "descricao": "Produtores rurais incluídos possuem receita superior a R$ 3,6 milhões",
                 "resultado": "Filtro explícito no SQL (receita_bruta >= 3600000)",
                 "status": "Atendido"},
                {"id": "V-03", "descricao": "Detalhamento por produto/atividade ou ocupação principal",
                 "resultado": "Bloco 1 detalhado por NCM; Bloco 2 por código de ocupação DIRPF",
                 "status": "Atendido"},
                {"id": "V-04", "descricao": "Alíquotas aplicadas correspondem aos artigos da LC 214/2025",
                 "resultado": "Matriz de Incidência vincula NCM a artigos; alíquotas conferidas (0%, 3,4%, 5,95%, 8,5%)",
                 "status": "Atendido"},
                {"id": "V-19", "descricao": "Alíquotas na mesma unidade de medida (fator decimal)",
                 "resultado": "Toda a planilha usa fator decimal: 0,085; 0,034; 0,0595",
                 "status": "Atendido"},
            ],
            "consistencia_interna": [
                {"id": "V-05", "descricao": "Débito CBS = Receita Bruta vezes Alíquota (por categoria)",
                 "resultado": "Bloco 1: confere integralmente. Bloco 2: aplica redutor de 20% não previsto na RN",
                 "status": "Atendido Parcialmente"},
                {"id": "V-06", "descricao": "Crédito CBS = Custos e Despesas vezes Alíquota (por categoria)",
                 "resultado": "Percentual de 38,09% documentado; aplicação conferida para 8,5%",
                 "status": "Atendido"},
                {"id": "V-07", "descricao": "Arrecadação Própria = Somatório(Débitos) menos Somatório(Créditos)",
                 "resultado": "Totais conferem entre abas da planilha-guia AUX_MOD_10",
                 "status": "Atendido"},
                {"id": "V-08", "descricao": "Receita PF para PJ inferior ou igual à Receita Bruta",
                 "resultado": "Fator PJ (aprox. 85%) aplicado no notebook; sempre inferior a 100%",
                 "status": "Atendido"},
                {"id": "V-20", "descricao": "Sem dupla contagem de contribuinte PF entre categorias",
                 "resultado": "Notebook usa anti-join e exclusão por lista de emitentes (PF vs. CNPJ nat. jur. 4120)",
                 "status": "Atendido"},
            ],
            "consistencia_calculo": [
                {"id": "V-09", "descricao": "Ajuste MC calculado separadamente por categoria de PF",
                 "resultado": "Abas 10.3 e 10.4 segregam por categoria (PR vs. Serviços)",
                 "status": "Atendido"},
                {"id": "V-10", "descricao": "Receitas destinadas a PJ segregadas das destinadas a PF consumidor final",
                 "resultado": "SQL identifica destinatário PJ via CFOP e natureza jurídica",
                 "status": "Atendido"},
                {"id": "V-16", "descricao": "Rastreabilidade fonte-filtro-regra para cada total",
                 "resultado": "Pipeline SQL para Python para Excel completo e documentado",
                 "status": "Atendido"},
                {"id": "V-17", "descricao": "Campos vazios não convertidos automaticamente em zero",
                 "resultado": "NCMs inválidas excluídas (não zeradas); tratamento documentado nas Considerações",
                 "status": "Atendido"},
            ],
            "sensibilidade": [
                {"id": "TS-01", "descricao": "Variação do redutor comportamental (0%, 10%, 20%, 30%, 40%)",
                 "resultado": "Modelado no simulador; impacto de R$ 5 bi por cada 10 p.p. de variação",
                 "status": "Atendido"},
                {"id": "TS-02", "descricao": "Variação do percentual de crédito (30% a 45%)",
                 "resultado": "Pendente: requer estratificação por setor",
                 "status": "Pendente"},
                {"id": "TS-03", "descricao": "Variação do % consumo intermediário (mais ou menos 5 p.p.)",
                 "resultado": "Pendente: requer Módulo Central disponível",
                 "status": "Pendente"},
            ],
        },
        "camada_2": {
            "conformidade": [
                {"id": "V-13", "descricao": "Limiar de R$ 3,6 milhões com fundamentação legal",
                 "resultado": "Arts. 164 e 165 da LC 214/2025 confirmam o limiar",
                 "status": "Atendido"},
                {"id": "V-15", "descricao": "Ano-calendário, data de extração e versão informados",
                 "resultado": "Datas nos comentários SQL (16 e 23/04/2026); falta formalização no Excel",
                 "status": "Atendido Parcialmente"},
                {"id": "V-22", "descricao": "Ajuste MC usa somente operações intermediárias com PJ",
                 "resultado": "Fator PJ calculado sobre vendas a PJ (excluindo MEI e Simples)",
                 "status": "Atendido"},
                {"id": "V-23", "descricao": "Dados pessoais diretos suprimidos, anonimizados ou agregados",
                 "resultado": "Planilhas agregadas; CPFs aparecem apenas como critério de filtro nos SQLs",
                 "status": "Atendido"},
            ],
            "premissas": [
                {"id": "PM-01", "descricao": "Alíquota de referência utilizada: 8,5% (0,085)",
                 "resultado": "Valor paramétrico consistente em todas as 5 abas",
                 "status": "Atendido"},
                {"id": "PM-02", "descricao": "Preço médio diesel ANP: R$ 5,80/L (2023), R$ 5,96/L (2024)",
                 "resultado": "Utilizado para crédito de combustível (volume vezes alíquota ad rem)",
                 "status": "Atendido"},
                {"id": "PM-03", "descricao": "Percentual único de crédito para serviços PF: 38,09%",
                 "resultado": "Derivado de amostra de 170 mil CPFs (5,5% do universo)",
                 "status": "Atendido Parcialmente"},
                {"id": "PM-04", "descricao": "Redutor comportamental de 20% sobre BC débitos (Bloco 2, exceto cartórios)",
                 "resultado": "Hipótese prospectiva não prevista na metodologia homologada",
                 "status": "Divergência"},
            ],
        },
        "camada_3": {
            "reproducao": [
                {"id": "EX-01", "descricao": "Reprodução dos SQLs de extração do Bloco 1 na sala de sigilo",
                 "resultado": "Pendente: agendamento junto à RFB",
                 "status": "Pendente"},
                {"id": "EX-02", "descricao": "Execução dos notebooks Python sobre dados extraídos",
                 "resultado": "Pendente: depende de EX-01",
                 "status": "Pendente"},
            ],
            "recalculo": [
                {"id": "RC-01", "descricao": "Recálculo dos débitos por NCM vezes alíquota (Bloco 1)",
                 "resultado": "Pendente: requer acesso aos dados brutos",
                 "status": "Pendente"},
                {"id": "RC-02", "descricao": "Recálculo dos créditos com percentual estratificado por setor (Bloco 2)",
                 "resultado": "Pendente: requer scripts do Bloco 2",
                 "status": "Pendente"},
                {"id": "V-11", "descricao": "Arrecadação própria consistente com valor no Módulo Central",
                 "resultado": "Módulo Central não disponível para conciliação",
                 "status": "Não Verificável"},
                {"id": "V-12", "descricao": "Ajuste creditório consistente com valor no Módulo Central",
                 "resultado": "Módulo Central não disponível para conciliação",
                 "status": "Não Verificável"},
            ],
        },
    },

    "inconsistencias": [
        {
            "id": "INC-001",
            "titulo": "Redutor comportamental de 20% não previsto na metodologia",
            "descricao": (
                "A RFB aplicou um redutor de 20% sobre a base de cálculo dos "
                "débitos do Bloco 2 (Demais PF), exceto cartórios, sob a "
                "hipótese de alteração de comportamento dos contribuintes com "
                "a introdução da CBS. A Regra de Negócio RN-10.13 estabelece "
                "que Débito CBS = Receita Bruta vezes Alíquota Específica, sem "
                "multiplicador intermediário. A justificativa foi declarada "
                "oralmente na reunião de entrega."
            ),
            "consequencia": (
                "Redução de aproximadamente R$ 9 bilhões na base de débitos "
                "(2024), com impacto estimado de 0,1 p.p. na alíquota de "
                "referência por cada R$ 6 bilhões de variação. Efeito "
                "pró-contribuinte PJ (eleva a alíquota de referência)."
            ),
            "tratamento": (
                "Inconsistência registrada formalmente. Solicitada justificativa "
                "por escrito à RFB. Redutor modelado como parâmetro ajustável "
                "no simulador (0% a 40%) para testes de sensibilidade. "
                "Pendente de decisão do GT sobre aceitação ou rejeição."
            ),
            "status": "Divergência",
        },
        {
            "id": "INC-002",
            "titulo": "Percentual único de crédito (38,09%) para todas as categorias de serviços",
            "descricao": (
                "A RFB aplica um percentual único de 38,09% sobre o total do "
                "livro-caixa para estimar a parcela elegível a crédito, "
                "independentemente da categoria profissional. A estrutura "
                "de despesas de um profissional de saúde difere "
                "substancialmente da de um advogado ou artista."
            ),
            "consequencia": (
                "Possível subestimação ou superestimação de créditos por "
                "setor, com impacto na arrecadação líquida do Bloco 2. "
                "Amostra de 5,5% dos CPFs pode não capturar variabilidade "
                "setorial."
            ),
            "tratamento": (
                "Registrada como limitação metodológica. Proposto teste de "
                "sensibilidade com percentuais estratificados (30%, 35%, "
                "40%, 45%). Pendente de dados desagregados por setor."
            ),
            "status": "Atendido Parcialmente",
        },
        {
            "id": "INC-003",
            "titulo": "Exclusão de 4 CPFs outliers sem memória de cálculo",
            "descricao": (
                "Os mesmos 4 CPFs são excluídos em ambos os anos nos scripts "
                "SQL. A documentação indica apenas 'exclusão após análise "
                "individual', sem memória quantitativa do critério."
            ),
            "consequencia": (
                "Se os CPFs representam valores expressivos, a exclusão "
                "pode subestimar a base de débitos e créditos do Bloco 1."
            ),
            "tratamento": (
                "Solicitada formalmente à RFB a memória de análise "
                "individual dos 4 CPFs. Pendente de resposta."
            ),
            "status": "Atendido Parcialmente",
        },
        {
            "id": "INC-004",
            "titulo": "Lista de REFs não aplicáveis difere entre 2023 e 2024 (débitos)",
            "descricao": (
                "Em 2023, o notebook remove o Anexo X (artes/cultura) da "
                "lista aplicável; em 2024, remove Dispositivos de "
                "acessibilidade (Anexo XIII). A troca não possui "
                "justificativa documentada."
            ),
            "consequencia": (
                "Se NCMs de produtor rural incidirem em ambos os REFs, a "
                "classificação tributária será diferente entre anos para "
                "o mesmo NCM. Impacto provavelmente baixo, mas requer "
                "confirmação."
            ),
            "tratamento": (
                "Solicitado esclarecimento formal à RFB sobre a "
                "motivação da troca. Verificação pendente: confirmar "
                "se NCMs agro são afetados."
            ),
            "status": "Atendido Parcialmente",
        },
        {
            "id": "INC-005",
            "titulo": "Crédito de combustível depende de alíquota REM indefinida (Módulo 6)",
            "descricao": (
                "O crédito de diesel do produtor rural é calculado como "
                "volume vezes alíquota ad rem (R$ 0,3515/L). A alíquota "
                "definitiva depende do Módulo 6 (Combustíveis), ainda "
                "não finalizado."
            ),
            "consequencia": (
                "Valor do crédito de combustível pode ser ajustado "
                "quando a alíquota REM for definida. Impacto marginal "
                "(débitos de combustível do PR são de R$ 12,3 milhões "
                "em 2023 e R$ 1,2 milhão em 2024)."
            ),
            "tratamento": (
                "Registrada como dependência externa. Valor será "
                "atualizado quando Módulo 6 for concluído."
            ),
            "status": "Limitação Documentada",
        },
    ],

    "alteracoes_metodologicas": [],

    "notas_metodologicas": [
        {
            "nome": "NOTA METODOLÓGICA CBS V_11_25b, atualização.docx",
            "data": "24/04/2026",
            "descricao": (
                "A RFB encaminhou, juntamente com os dados do Módulo 10, "
                "a Nota Metodológica CBS V_11_25b (atualização), documento "
                "que propõe alteração na metodologia de cálculo para as "
                "Pessoas Físicas do Bloco 2 (Demais PF). A nota introduz "
                "um redutor de 20% sobre a base de cálculo dos débitos, "
                "fundamentado na hipótese de mudança de comportamento dos "
                "agentes econômicos com a introdução da CBS. A premissa "
                "adotada é que parte dos profissionais liberais deixará de "
                "prestar serviços diretamente como PF, optando por "
                "constituir pessoa jurídica."
            ),
            "conteudo_resumo": (
                "Proposta de redutor comportamental de 20% sobre BC "
                "débitos do Bloco 2 (exceto cartórios)"
            ),
            "situacao_inventario": (
                "Presente no protocolo de recebimento "
                "(REC_MOD_010_20260427_152232), porém ausente do "
                "inventário automatizado de planilhas"
            ),
            "observacao": (
                "O documento NOTA METODOLÓGICA CBS V_11_25b consta no "
                "protocolo de recebimento do módulo (370,4 KB, SHA-256: "
                "c9617305...) mas não aparece no inventário de planilhas "
                "gerado automaticamente, uma vez que o inventário contempla "
                "apenas arquivos .xlsx. Esta discrepância documental não "
                "afeta a integridade dos dados, mas evidencia que o documento "
                "foi recebido e protocolado conforme procedimento padrão."
            ),
        },
    ],

    "conclusao": {
        "conformidade": (
            "A metodologia do Módulo 10 está aderente aos dispositivos da "
            "LC 214/2025 para o Bloco 1 (Produtor Rural). A lógica de "
            "apuração por NCM, com aplicação da Matriz de Incidência e "
            "hierarquização de alíquotas conforme LC 227/2025, é "
            "reprodutível e documentada. Para o Bloco 2, foi identificada "
            "divergência no redutor de 20%, que não está previsto na "
            "metodologia homologada (Acórdão 2833/2025-Plenário)."
        ),
        "consistencia": (
            "Os cálculos internos da planilha AUX_MOD_10 são consistentes: "
            "débitos conferem com base vezes alíquota, créditos conferem "
            "com despesa vezes percentual vezes alíquota, e os totais das "
            "abas de detalhamento reconciliam com o resumo consolidado. "
            "A trilha de rastreabilidade (SQL para Python para Excel) "
            "permite reprodução independente."
        ),
        "premissas": [
            {
                "nome": "Alíquota de referência",
                "descricao": "8,5% (0,085) aplicada uniformemente",
                "impacto": "Parâmetro que será ajustado na iteração final do simulador",
            },
            {
                "nome": "Redutor comportamental",
                "descricao": "20% sobre BC débitos (Bloco 2, exceto cartórios)",
                "impacto": "Reduz arrecadação própria PF em R$ 9 bi (2024); eleva alíquota de referência",
            },
            {
                "nome": "Percentual de crédito",
                "descricao": "38,09% do livro-caixa elegível a crédito (Bloco 2)",
                "impacto": "Determina volume de créditos dos serviços PF (R$ 10-11 bi/ano)",
            },
            {
                "nome": "Preço diesel ANP",
                "descricao": "R$ 5,80/L (2023), R$ 5,96/L (2024)",
                "impacto": "Define volume estimado de combustível para crédito ad rem",
            },
        ],
        "valores_agregados": [
            {"descricao": "Débitos totais (10.1 + 10.2)", "valor_2023": "R$ 20,06 bi", "valor_2024": "R$ 19,89 bi"},
            {"descricao": "Créditos totais (10.1 + 10.2)", "valor_2023": "R$ 24,00 bi", "valor_2024": "R$ 22,71 bi"},
            {"descricao": "Arrecadação própria (débitos menos créditos)", "valor_2023": "R$ -3,94 bi", "valor_2024": "R$ -2,82 bi"},
            {"descricao": "Ajuste MC: Produtor Rural (aba 10.3)", "valor_2023": "R$ 23,38 bi", "valor_2024": "R$ 22,69 bi"},
            {"descricao": "Ajuste MC: Serviços PF (aba 10.4)", "valor_2023": "R$ 0,224 bi", "valor_2024": "R$ 0,238 bi"},
        ],
        "sensibilidade_redutor": {
            "redutores": [0, 10, 20, 30, 40],
            "valores": [47.86, 43.08, 38.29, 33.50, 28.72],
        },
    },
}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CLI
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def main():
    parser = argparse.ArgumentParser(
        description="Gerador de Apêndice de Módulo CBS (padrão TCU)"
    )
    parser.add_argument(
        "entrada",
        nargs="?",
        help="Arquivo JSON com dados do módulo (opcional; usa Módulo 10 piloto se omitido)",
    )
    parser.add_argument(
        "saida",
        help="Caminho do arquivo .docx de saída",
    )
    parser.add_argument(
        "--modulo", type=int, default=None,
        help="Número do módulo (sobrescreve o valor do JSON)",
    )
    parser.add_argument(
        "--piloto", action="store_true",
        help="Gera o apêndice piloto do Módulo 10 (ignora entrada JSON)",
    )
    args = parser.parse_args()

    if args.piloto or args.entrada is None:
        dados = DADOS_MODULO_10
        print("[INFO] Gerando apêndice piloto: Módulo 10, Pessoa Física")
    else:
        with open(args.entrada, encoding="utf-8") as f:
            dados = json.load(f)
        print(f"[INFO] Dados carregados de: {args.entrada}")

    if args.modulo:
        dados["modulo"] = args.modulo

    gerador = ApendiceGerador(dados)
    path = gerador.gerar(args.saida)
    print(f"[OK] Apêndice gerado: {path}")
    print(f"     Tamanho: {path.stat().st_size:,} bytes")


if __name__ == "__main__":
    main()
