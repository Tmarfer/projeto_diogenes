# Gabarito — Inconsistências Plantadas no MOD_SINT_SQL

> **Uso restrito — fora do alcance dos agentes.**
> Este arquivo NÃO deve ser adicionado à massa de entrada (`workspace/input/`), nunca
> referenciado em prompts, e nunca exposto ao Watson, Sherlock ou Mycroft.
> Massa gerada por `scripts/gerar_mod_sint_formatos.py` a partir de
> `scripts/massa_fontes/MOD_SINT_SQL/`.

## Sumário do corpus

| Campo | Valor |
|-------|-------|
| Módulo | MOD_SINT_SQL — homologação do parser SQL (`sqlparse`, teto 40k chars) |
| Arquivos analisáveis | 4 consultas `.sql` (+ protocolo + inventário) |
| Inconsistências plantadas | 3 (INC-SQL-01 a INC-SQL-03) |
| Verdadeiros negativos | 1 arquivo limpo (`consulta_exportacoes.sql`) |
| Particularidades | Sem Planilha de Verificação (não dispara `validacao_planilha_rn`); Irene pula (sem XLSX/CSV) |

## Inconsistências plantadas

### INC-SQL-01 — CBS sobre locação de bem móvel no CASE de apuração (Art. 71)

| Campo | Valor |
|-------|-------|
| **Severidade esperada** | **CRÍTICO** |
| Arquivo | `consulta_apuracao_cbs.sql` — ramo `WHEN 'LOCACAO_BEM_MOVEL' THEN nf.valor_operacao * 0.099` |
| Valores | Base R$ 45.000,00 → CBS R$ 4.455,00 (Empresa B, 04/2024) |
| Norma | LC 214/2025, Art. 71 — RFB não reconhece CBS sobre locação de bem móvel |
| Detecção esperada | Watson lê a lógica do CASE e identifica a tributação integral; Sherlock classifica CRÍTICO citando o Art. 71. O comentário final do arquivo ("sem ressalva quanto a entendimento divergente da RFB") é a pista. |

### INC-SQL-02 — Redução combustíveis aplicada sem join de comprovação NCM/ICMS-ST (Art. 39)

| Campo | Valor |
|-------|-------|
| **Severidade esperada** | **ATENÇÃO** |
| Arquivo | `consulta_reducoes_setoriais.sql` — fator `* 0.56` direto, sem join de enquadramento |
| Valores | CBS com redução R$ 65.288,32 vs. sem redução R$ 116.622,00 (Alfa, 06/2024) |
| Norma | LC 214/2025, Art. 39 — exige sujeição do NCM 2710.12.59 ao ICMS-ST |
| Detecção esperada | O comentário "Não há join com tabela de sujeição ao ICMS-ST" deve disparar o questionamento; Sherlock exige comprovação documental. |

### INC-SQL-03 — Crédito de transição truncado em hardcode sem justificativa (Art. 54 §3° II)

| Campo | Valor |
|-------|-------|
| **Severidade esperada** | **ATENÇÃO** |
| Arquivo | `consulta_creditos_transicao.sql` — `LEAST(..., 5000.00)` hardcoded |
| Valores | Disponível R$ 11.760,00 / aproveitado R$ 5.000,00 / saldo R$ 6.760,00 (Alfa, Jan/2024) |
| Norma | LC 214/2025, Art. 54 §3° II |
| Detecção esperada | Watson identifica o teto hardcoded na expressão SQL; questiona ausência de documento justificando o aproveitamento parcial. |

## Verdadeiros negativos (não marcar)

| Item | Justificativa | Norma |
|------|---------------|-------|
| `consulta_exportacoes.sql` — CBS 0,00 em CFOP 7xxx | Imunidade correta | LC 214/2025, Art. 12 §1° |

## Pontuação

- **MET-04 (detecção, meta ≥70%):** 3 pontos (1 por INC); aprovado ≥ 2/3 detectados com arquivo + quantificação + artigo.
- **MET-05 (falsos positivos, meta <15%):** FP / (FP + TP) × 100; flag em `consulta_exportacoes.sql` conta como FP.
- **MET-07 (fundamentação, meta ≥1,5):** artigo correto (1) + cita LC 214/2025 (1) + Acórdão 2833/2025 (bônus 1), média por INC detectado.

## Histórico de medições

| Ciclo | Data | Config | MET-04 | MET-05 | MET-07 | Notas |
|-------|------|--------|--------|--------|--------|-------|
| MOD_SINT_SQL_A1_20260610T190322Z | 2026-06-10 | gpt-5.5-thinking (timeout 1500s) | Watson 3/3 · Sherlock **0/3** | 2 ocorrências, ambas fora do gabarito | n/a | Massa v1 (sem metodologia, datas 2025). Ver análise. |
| MOD_SINT_SQL_A1_20260610T200355Z | 2026-06-10 | gpt-5.5-thinking (timeout 1500s) | Watson 3/3 · Sherlock **2,5/3** (INC-01 detectado mas NV) | 1 FP de massa (S004 exportações) + 1 sistêmica CRITICO (S009) | ~2,3 (Art. + LC em todas; sem Acórdão) | Massa v2 (Metodologia comum + datas 2024). **APROVA MET-04, reprova MET-05 por artefatos.** Ver análise. |

### Análise do ciclo 20260610T190322Z (massa v1)

**Parser SQL homologado no Watson:** os 3 INCs foram detectados com linha exata —
W000-004 (locação, linhas 15/25-26), W000-016 (redução por NCM sem comprovação,
linhas 15-17), W000-010 (teto fixo no crédito, linhas 8/11-12/18-19). Inclusive
flagrou o `ELSE` residual (W000-005) e a inconsistência CFOP 7xxx vs 7101 (W000-014).

**Sherlock 0/3 por falha de andaime, não de parser:** o módulo v1 não tinha
`Metodologia_*.md` — S001-NV declarou "Ausência de metodologia específica do módulo"
e a validação metodológica não desceu aos achados. S002 foi o artefato de datas
(competências 2025 vs anos-base 2023/2024).

**Correções na massa v2 (aplicadas 2026-06-10):** `Metodologia_CBS_SINT.md` comum
adicionado a todos os módulos de formato (seções 5.1-5.3 ancoram Arts. 71/39/44);
massa re-datada para competências 2024. **Re-rodar o módulo com a massa v2.**

### Análise do ciclo 20260610T200355Z (massa v2) — Metodologia comum funcionou

**MET-04 — APROVADO (2,5/3).** A Metodologia comum destravou Sherlock (0/3 → 2,5/3):
- **INC-SQL-02 ✓** S006-DIV, Art. 39, fator 0,56 quantificado, exige base de comprovação.
- **INC-SQL-03 ✓** S005-DIV, Art. 54, teto R$ 5.000,00 quantificado.
- **INC-SQL-01 ◐** S008 detectou a área certa (locação, Art. 71, Metodologia 5.1) mas
  classificou NAO_VERIFICAVEL/ALERTA em vez de DIVERGENCIA/CRÍTICO — tratou a lógica do
  CASE (tributação vedada operacionalizada no script) como "decisão interna sem documento
  de suporte". Erro de natureza: a evidência operacional é o fato; nenhum documento muda o
  que o script executa. **Correção aplicada:** Passo 5c ganhou o bullet "divergência
  normativa operacionalizada" e o novo Passo 5d calibra severidade pela natureza.

**MET-05 — REPROVA na contagem bruta (2 FP / 5 DIV+CRITICO ≈ 40%), mas ambos artefatos:**
- **S004 (exportações)** — defeito da massa, não do agente: o comentário declarava
  conferência de "CFOP 7101" enquanto o filtro executa `LIKE '7%'`. O agente leu certo.
  **Massa v3 corrige o comentário** para coincidir com o filtro; o arquivo volta a ser
  verdadeiro negativo válido.
- **S009 (cadeia não reproduzível)** — sistêmica agregada elevada a CRITICO, repetindo o
  padrão do MOD_SINT_001. **Correção aplicada:** Passo 5d + controle do 8f proíbem
  sistêmica agregada em nível CRITICO.

**MET-07 — APROVADO (~2,3).** Todas as ocorrências citam artigo correto + LC 214/2025
no formato canônico; S001 cita o Acórdão 2833/2025 (bônus). Vinculação número↔norma do
Passo 5b sobreviveu até o relatório final (0,56 / R$ 5.000,00 / R$ 8,00 na seção de
Divergências para o Contraditório).

**Ruído de Watson (não pontuado, mas relevante):** 6 dos 9 alertas CRITICA do ciclo são
"ausência de data operacional / período de referência" — um por arquivo, artefato da massa
mínima. **Correções aplicadas:** (a) `verificacao_metadados` do skills.md recalibrada
(período inferível do conteúdo = presente com ressalva; só data de geração ausente = ALTA;
padrão recorrente = agregação na consolidação); (b) gerador grava período de referência e
data de geração no protocolo e no inventário (massa v3).

**Parser SQL definitivamente homologado** (2ª rodada com 3/3 no Watson, linhas exatas).
Critério de avanço para os demais formatos: re-rodar SQL com massa v3 + calibrações e
confirmar MET-05 <15%; em paralelo, IPYNB → MD → PDF → DOCX → TXT.

---
*DVA-CBS | Projeto Diógenes | TC 015.848/2025-6 | Uso Interno Restrito*
*Fora do alcance dos agentes — manter em `docs/conformidade/` apenas*
