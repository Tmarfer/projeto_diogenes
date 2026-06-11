---
documento: PRD — Adendo v0.2 — Homologação por Formato e Rodada Real MOD_010
projeto: DVA-CBS | Projeto Diógenes
processo: TC 015.848/2025-6
unidade: SecexContas — Tribunal de Contas da União
versao: 0.2
data: 2026-06-10
uso: Interno Restrito
referencia: PRD_Piloto_Diogenes_v01.md (base) + PRD_adendo_v01_fase_entrega.md
---

# **PRD — Adendo v0.2 — Homologação por Formato e Rodada Real MOD_010**

## Propósito deste adendo

O PRD v0.1 valida o piloto com um único módulo sintético (`MOD_SINT_001`, centrado em
planilhas). A massa real do MOD_010 contém **seis formatos de arquivo analisáveis**
(xlsx, sql, ipynb, md, pdf→md, docx→md) e o piloto demonstrou que a qualidade da análise
depende do parser e do andaime de prompt **por formato** — o MOD_SINT_SQL v1 teve Watson
3/3 e Sherlock 0/3 apenas porque faltava a âncora metodológica no pacote.

Este adendo formaliza: (a) a homologação formato-a-formato com gabaritos de conformidade;
(b) a decisão de pré-conversão de formatos opacos para Markdown; (c) os critérios de
aceitação da primeira rodada real completa do MOD_010.

---

## Bloco 1 — Homologação por Formato (`RF-HF-*`)

**RF-HF-01.** O sistema deve dispor de um módulo sintético mínimo por formato analisável
(`MOD_SINT_SQL`, `MOD_SINT_IPYNB`, `MOD_SINT_MD`, `MOD_SINT_PDF`, `MOD_SINT_DOCX`,
`MOD_SINT_TXT`), gerado deterministicamente a partir de fontes versionadas
(`scripts/massa_fontes/`), cada um com protocolo de recebimento e inventário com hashes
reais, período de referência e data de geração.

**RF-HF-02.** Cada módulo sintético deve conter inconsistências plantadas documentadas em
gabarito de uso restrito (`docs/conformidade/gabarito_mod_sint_*.md`), **nunca exposto aos
agentes**, com ao menos: uma divergência normativa operacionalizada (severidade CRÍTICO),
uma aplicação sem comprovação documental (ATENÇÃO) e um verdadeiro negativo.

**RF-HF-03.** Todo módulo sintético deve incluir a metodologia comum
(`Metodologia_CBS_SINT.md`) que ancora normativamente a validação de Sherlock — a ausência
de metodologia no pacote invalida a medição (lição do MOD_SINT_SQL v1).

**RF-HF-04.** Critério de homologação por formato: **MET-04 ≥ 70%** (detecção) e
**MET-05 < 15%** (falsos positivos), medidos contra o gabarito, com fundamentação média
**MET-07 ≥ 1,5**. Falsos positivos comprovadamente causados por defeito da massa são
corrigidos na massa e excluídos da contagem (registrados no histórico do gabarito).

**RF-HF-05.** Cada ciclo de homologação deve registrar a medição no histórico do gabarito
correspondente (data, configuração de modelo, MET-04/05/07, análise das falhas e correções
aplicadas) — o gabarito é a memória de calibração do formato.

## Bloco 2 — Pré-conversão para Markdown (`RF-CV-*`)

**RF-CV-01.** Formatos opacos (docx, pdf, txt) serão convertidos deterministicamente para
`.md` **antes** de entrar no Departamento de Validação (conversor:
`scripts/converter_md.py`, sem LLM). Os nativos pré-conversão são preservados fora de
`workspace/input/` (em `_fontes_originais/`) para auditoria de fidelidade.

**RF-CV-02.** A homologação dos formatos PDF/DOCX/TXT valida a **fidelidade da conversão**
(a inconsistência plantada no nativo deve sobreviver ao `.md` e ser detectada), não o
parser do formato nativo.

## Bloco 3 — Pré-Atendimento e Ata da Reunião (`RF-PA-*`)

**RF-PA-01.** O Relatório de Pré-Atendimento é gerado **sempre** na Fase de Entrega; o
Bloco 1 (transcrição da ata) é omitido quando a ata não for localizada — a ausência da ata
não suprime o batimento das inconsistências (Bloco 2).

**RF-PA-02.** A localização da ata em `inputs/` usa correspondência por **token inteiro**
do caminho relativo (`ata`, `reuniao`, `entrega`, `atendimento`; normalização de acentos),
nunca substring — `CATALOGO.md` não é ata. O arquivo escolhido é registrado nos avisos da
entrega para auditoria.

## Bloco 4 — Rodada Real Completa MOD_010 (gate da Fase D)

A primeira execução real completa (toda a massa do MOD_010, ~130 arquivos, overnight,
`diogenes autorun --auto-seal`) é o critério de saída do piloto para a Fase D. Critérios
de aceitação (detalhados em `docs/plano_rodada_noturna_MOD_010.md`):

| # | Critério |
|---|----------|
| 1 | Ciclo termina `ENCERRADO_CHANCELADO` (ou chancela manual com doc LIMPO) sem intervenção |
| 2 | 100% dos arquivos analisáveis com análise individual de Watson (zero perdas silenciosas) |
| 3 | Alertas CRITICA de Watson dominados por achados materiais, não por metadados ausentes |
| 4 | Ocorrências de Sherlock individualizadas, com fundamento canônico e número de Watson |
| 5 | Entrega completa (9 artefatos `Modulo10`), pré-atendimento com a ata real da reunião |
| 6 | QA de entrega (Mycroft `avaliar_entrega`) = APROVADO |

---

## Resolução de tensões com o PRD v0.1

- **Massa de validação:** o PRD v0.1 previa apenas `MOD_SINT_001`. Este adendo **estende**
  (não substitui): `MOD_SINT_001` permanece o módulo de regressão de planilhas; os módulos
  de formato cobrem o restante da superfície de parsing.
- **Aceitação por métrica:** MET-04/05/07 do PRD v0.1 ganham medição **por formato**, com
  gabaritos versionados como instrumento de medida.

---
*DVA-CBS | Projeto Diógenes | TC 015.848/2025-6 | Uso Interno Restrito*
