---
documento: SDD Derivado — Sherlock Holmes (Reescrita Guiada v2)
projeto: DVA-CBS | Projeto Diógenes
processo: TC 015.848/2025-6
unidade: SecexContas — Tribunal de Contas da União
versao: 0.1
status: Documento de Trabalho Interno
data: 2026-06-11
uso: Interno Restrito
documentos_fonte:
  - src/diogenes/agents/sherlock.py (referência v1, 339 LOC)
  - src/diogenes/agents/contexto_metodologico.py + agents/heartbeat.py
  - docs/agentes/sherlock/{agent,soul,skills,heartbeat}.md
  - docs/auditoria_agentes/sherlock/contrato.md
  - agents_spec.yaml + CLAUDE.md (correções 2026-06-11)
---

# SDD Derivado — Sherlock Holmes

> O "como" da reescrita v2 de Sherlock. Parte de onde o
> [PRD_derivado_sherlock.md](PRD_derivado_sherlock.md) encerra. Pacote de
> Trabalho único: PT-SH-1 (Seção 11).

---

## 1. Relação com o SDD mestre

Blocos de origem: 1.2, 1.6 (Sherlock = Camadas 1–3), 2.3/2.4, 8. O modo
monolítico, a degradação escalonada e o `is_fallback` são posteriores ao SDD
v0.1 — documentados nas calibrações 2026-06-03 (dossiê) e correções 2026-06-11
(CLAUDE.md) e aqui.

## 2. Posição na arquitetura

```
Mycroft.montar_pacote_sherlock → [EM_EXECUCAO_SHERLOCK]
   Sherlock.validar(pacote)                  ← MONOLÍTICO, degradação escalonada
   Sherlock.validacao_planilha_rn_sherlock   ← CONDICIONAL (flag da Planilha)
   Sherlock.consolidar                        ← 11 seções + JSON
   → completude (Orquestrador) → gate is_fallback → Stranger Room
   → [AGUARDANDO_REVISAO_MYCROFT_SHERLOCK] → (até 2× responder_critica)
   → Mycroft.consolidar
```

- **Quem chama:** o Orquestrador. Sherlock nunca recebe nada diretamente de
  Watson (fluxo obrigatório Watson → Mycroft → Sherlock).
- O Orquestrador verifica as 11 seções + JSON **antes** de acionar
  `Mycroft.consolidar()`; ausência → `AGUARDANDO_COMPLETUDE`.

## 3. Invocador — classe, assinaturas e parâmetros

Classe v1: `SherlockAgent` (`agents/sherlock.py:74`).

| Método | Linha v1 | Retorno | call_type / heartbeat |
|---|---|---|---|
| `validar(pacote_sherlock: str)` | `:88` | `SherlockOutput` | `validacao_inicial` (seção monolítica própria — Fix 3-A) |
| `validacao_planilha_rn_sherlock(...)` | `:135` | `SherlockOutput` | `validacao_planilha_rn_sherlock` |
| `consolidar(...)` | `:165` | `SherlockOutput` | `consolidar_sherlock` |
| `responder_critica(critica, output_anterior, ...)` | `:191` | `SherlockOutput` | `resposta_r1` / `resposta_r2` |
| `_construir_system_prompt()` | `:215` | str | soul + skills |
| `_montar_call(...)` | `:220` | `LLMCall` | interno |
| `_fallback_output_completo()` | `:242` | `SherlockOutput` (`is_fallback=True`) | interno |
| `_parsear_output(content)` | `:271` | `SherlockOutput` | interno |

Função de módulo: `reduzir_pacote_sherlock(pacote)` (`:48`) — réguas de
truncamento da degradação (metodologia 40k / corpus 15k, com ressalva
obrigatória no output).

Helpers: `_extrair_secoes` (`:293`), `_contar_dilemas` (`:310`),
`_extrair_bool_campo` (`:314`), `_extrair_int_campo` (`:328`).

**Contexto metodológico** (`agents/contexto_metodologico.py` — parte do
contrato): `carregar_metodologia_modulo` (`:39`, teto `_MAX_CHARS_METODOLOGIA =
80_000`) e `carregar_corpus_juridico` (`:68`, teto 30k; recorte por módulo
derivado de `DIOGENES_CORPUS_JURIDICO_DIR`).

**Mapeamento de heartbeat** (`agents/heartbeat.py:37` — contrato crítico):
`"validacao_inicial": "validacao_inicial"` (monolítico). O mapeamento para
`verificar_ponto` causou a falha NV-GLOBAL-01 — **teste obrigatório**.

**Parâmetros** (`agents_spec.yaml::agentes.sherlock`): `gpt-5.5-thinking`,
temperatura 0.1, max_tokens 8000, max_tokens_ciclo 131072, timeout 1500s,
retry 4× (demais call_types; `validacao_inicial` usa 2 por estágio — override),
backoff 30s.

## 4. Consolidação dos 4 arquivos de definição

```python
system_prompt = soul.md + "\n\n---\n\n" + skills.md   # filesystem, sem cache
user_prompt   = heartbeat.md[call_type] + "\n\n" + inputs
```

### 4.1 `soul.md` — síntese (197 linhas)

| Regra | Conteúdo |
|---|---|
| Identidade | Validador metodológico (Acórdão 2833/2025); raciocínio dedutivo; relatório seco, preciso, defensável |
| Art. 7 | Parte das análises de Watson, nunca dos brutos; fidelidade à metodologia, não "verdade absoluta" |
| Reproduzibilidade | Toda posição com lastro rastreável; divergência reproduzível por terceiro |
| Exceção ao Art. 14 (Fix 3-B) | Trace interno em 1ª pessoa permitido; outputs em 3ª pessoa |
| Anti-PII (ChatTCU, Fix 3-C) | Mascaramento e referência estrutural |

### 4.2 `skills.md` — síntese (875 linhas)

| Elemento | Conteúdo |
|---|---|
| Premissas Globais | anos-base 2023/2024 (alteração RFB — não é bug), critério de equivalência, nota metodológica |
| Sistema de classificação obrigatório | Atendido / Atendido Parcialmente / Divergência / Atenção / Limitação / Não Verificável |
| Formato de citação obrigatório | ex.: `[Acórdão 2833/2025 \| Apêndice X \| Módulo 10 \| Seção 3.1 \| RN-10.01]` |
| Template 1 `verificar_ponto` (bancada) | Verificação de Premissas Globais; Verificação; Nota Metodológica com Alteração; Encaminhamento |
| Template 1b | Trace de Raciocínio (opcional, 1ª pessoa) |
| Template 2 `consolidar_sherlock` | Seções 1–9 (Quadro Consolidado; Divergências p/ Contraditório; Não Verificáveis; Dilemas; Posição Consolidada; Roteiro de Perguntas; Alterações Encaminhadas RFB; Impacto entre Módulos; Pendências Simulador) + **Seção 10: Relatório Estruturado (10.1–10.11)** + **Seção 11: JSON de Ocorrências** (mapeamento `NAO_VERIFICAVEL → ALERTA` no dashboard) |
| Template 2b `validacao_planilha_rn_sherlock` | Verificações Ponto a Ponto metodológicas; Verificações Criadas; Dilemas; Posição |

### 4.3 `agent.md` — composição por call_type (contrato)

- `validacao_inicial` (real): heartbeat monolítico + pacote Sherlock (síntese de
  Mycroft, decisão/consolidado de Watson, metodologia, corpus) — **NÃO inclui
  arquivos originais do pacote RFB**.
- `consolidar_sherlock`: heartbeat + quadro consolidado + `watson_consolidado.md`.
- `resposta_r1/r2`: heartbeat + output anterior + crítica de Mycroft + ponto
  relevante.
- (`verificar_ponto`/`MC_mapa_pontos.md`: composição reservada à bancada.)

### 4.4 `heartbeat.md` — transcrição verbatim (contrato de prompt)

Transcrição integral de `docs/agentes/sherlock/heartbeat.md` (2026-06-11),
incluindo a seção monolítica `validacao_inicial` (Fix 3-A) e o protocolo de
degradação escalonada. O prompt v2 deve ser **byte-idêntico** (gate nº 2); o
arquivo original prevalece.

<!-- INÍCIO TRANSCRIÇÃO VERBATIM heartbeat.md (Sherlock) -->
# Heartbeat — Sherlock Holmes
## Auditor de Validação Metodológica CBS | DVA-CBS | Projeto Diógenes

---

*Este arquivo é organizado em seções por call_type. O invocador injeta apenas a seção
correspondente no início do user_prompt.*

---

# Heartbeat de Sherlock — validacao_inicial

## Sua Situação Nesta Chamada

Você está sendo acionado em modo monolítico para realizar a validação metodológica completa
do módulo. Nesta chamada, você recebe o pacote inteiro: o Watson consolidado com todos os
alertas técnicos identificados, as premissas globais do ciclo, o documento de Regras de
Negócio do módulo e o corpus jurídico disponível. Você não vê os arquivos originais do
pacote — trabalha exclusivamente sobre o que Watson analisou e o que a metodologia prescreve.

## Seu Protocolo para Esta Chamada

**Passo 1: Leia as premissas globais do ciclo.**
Identifique: módulo, período de referência e observações gerais de Mycroft sobre o pacote Watson.

→ **Premissa 1 — Ano-base:** todos os pontos devem ser verificados sob os anos-base de
**2023 e 2024** (alteração declarada pela RFB; os anos 2024 e 2025 da metodologia original
ficam substituídos). Se qualquer ponto ainda referencia 2024/2025 sem ajuste: sinalize como
divergência ou atenção conforme o impacto.

→ **Premissa 3 — Nota metodológica:** verifique se Watson sinalizou `Nota metodológica com
alteração detectada: Sim` no consolidado. Se sim: identifique o alcance antes de classificar
os pontos afetados e registre o que seria a classificação sob a metodologia original.

**Passo 2: Extraia os pontos de validação do documento de Regras de Negócio do módulo.**
Leia o documento de Regras de Negócio recebido. Para cada ponto verificável, identifique:
o que a metodologia homologada prescreve, o dispositivo legal correspondente (Apêndice, artigo,
parágrafo), a camada (C1/C2/C3) e quais análises de Watson são relevantes.

Se o documento de Regras de Negócio não estiver disponível no pacote recebido: classifique
o módulo como `Não Verificável` por ausência de insumo metodológico e documente a razão exata.

**Passo 3: Leia o Watson consolidado.**
Compreenda o que Watson encontrou: inconsistências de integridade, alertas por severidade,
arquivos analisados e não analisados. Use o que Watson encontrou como insumo para a verificação
metodológica — você não reavalia o trabalho de Watson (Artigo 7).

**Passo 4: Valide cada ponto extraído.**
Para cada ponto identificado no Passo 2, execute:

→ **4a — Camada 1 (Aderência Metodológica):** o que o dispositivo prescreve foi executado?
Compare a prescrição com o que Watson registrou sobre como os dados foram produzidos.
Use os cinco ângulos do skills.md: dispositivo legal, premissa metodológica, fonte de dado,
escopo de contribuintes e granularidade.

→ **4b — Camada 2 (Reprodutibilidade):** o percurso de extração declarado é logicamente
reproduzível? As bases estão suficientemente identificadas, os filtros são precisos, o
percurso declarado é capaz de produzir os dados apresentados?

→ **4c — Classificação:** escolha pela hierarquia do sistema de status do skills.md.
Cite o dispositivo no formato obrigatório:
`[Acórdão 2833/2025-Plenário | Apêndice X — §Y]` ou `[LC 214/2025 | Art. N]`.
Classificação sem citação de dispositivo é output inválido.

→ **4d — Dilema:** há duas interpretações de peso equivalente sem dispositivo de desempate?
Registre como dilema. Não resolva por escolha arbitrária.

→ **4e — Ancoragem ao fato de Watson (obrigatório para DIVERGENCIA/ATENCAO):** convirja os
dois fluxos. O fato (de Watson): arquivo-fonte, célula/linha, valor observado e esperado —
transcreva os números, eles devem sobreviver até o relatório final. A norma (sua): o
dispositivo violado ou cujo enquadramento não está comprovado. A ponte: uma frase ligando os
dois. Se Watson registrou o número, **use o número** — norma citada de forma abstrata sem o
dado quantificado é meia ocorrência.

→ **4f — Natureza da ocorrência (controle de falso positivo):** antes de emitir, classifique:
  - *Divergência confirmada:* há valor concreto que não bate — emita com o número.
  - *Divergência normativa operacionalizada (não rebaixar para NAO_VERIFICAVEL):* a lógica de
    cálculo que Watson transcreveu do script/planilha aplica tratamento que a norma veda ou
    não reconhece (ex.: CBS sobre locação de bem móvel quando o Art. 71 não a reconhece).
    A evidência operacional É o fato — nenhum documento adicional muda o que o script executa.
    Classifique DIVERGENCIA; a ausência de "documento de suporte da decisão interna" não a
    transforma em lacuna.
  - *Lacuna de rastreabilidade:* o percurso não é reproduzível mas **não há evidência de
    erro** — NAO_VERIFICAVEL de severidade baixa; não eleve a ALERTA/CRITICO.
  - *Conformidade legítima:* tratamento correto (exportação imune pelo Art. 12 §1°, alíquota
    zero pelo Art. 47) **não vira ocorrência** — flagar tratamento correto é falso positivo.
  Não multiplique ocorrências genéricas ("cadeia não reprodutível", "sem parametrização")
  que repetem a mesma lacuna — uma lacuna, uma ocorrência.

→ **4g — Gradação de impacto pela natureza:** divergência normativa operacionalizada com
valor quantificado → impacto alto (CRITICO no dashboard). Tratamento aplicado sem a
comprovação documental exigida (o cálculo pode estar certo — falta o lastro) → impacto médio
(ALERTA), salvo materialidade demonstrada sobre o resultado agregado. Ocorrência sistêmica
agregada (reprodutibilidade, parametrização, hashes, metadados recorrentes) → ocorrência
única de impacto médio no máximo — **nunca CRITICO por acumulação**.

**Passo 5: Produza os outputs por ponto.**
Para cada ponto validado, produza um documento `sherlock_ponto_{n:02d}_{titulo_slug}.md`
usando o Template 1 do skills.md. **Todos os pontos na mesma resposta — esta chamada é
monolítica.** Não interrompa nem aguarde confirmação entre pontos.

**Passo 6: Verifique o Artigo 7.**
Há análise de célula, fórmula ou script no output? Isso é território de Watson — remova.
Substitua pela referência à análise de Watson correspondente.

**Passo 7: Verifique o Artigo 14.**
Terceira pessoa nos documentos de análise. O trace interno, quando produzido,
pode usar primeira pessoa — mesma exceção documentada para Watson (Passo 7b).
"Sherlock Holmes" apenas na assinatura ao final de cada documento de output, para rastreabilidade.

**Passo 7b: Decida sobre o trace.**
Se a classificação de algum ponto exigiu escolha entre hipóteses não capturada integralmente
no output estruturado, ou se o dispositivo admitia duas leituras antes de uma ser adotada:
produza o trace usando o Template 1b do skills.md em primeira pessoa. Nunca entregável ao GT.

## Restrições Ativas Nesta Chamada

- Esta chamada é monolítica: processe **todos** os pontos em uma única resposta. (Sem UM_PONTO_POR_CHAMADA)
- Você não analisa integridade estrutural dos artefatos. (Artigo 7)
- Você não vê arquivos originais — apenas o consolidado de Watson. (agent.md)
- Toda classificação cita o dispositivo metodológico. (Artigo 7 e skills.md)
- **Toda DIVERGENCIA/ATENCAO ancora ao achado concreto de Watson: arquivo-fonte e valor.** (Passo 4e)
- **Lacuna ≠ divergência; lógica operacionalizada contra a norma é DIVERGENCIA; tratamento correto não vira ocorrência.** (Passo 4f)
- **Severidade segue a natureza da ocorrência; sistêmica agregada nunca é CRITICO.** (Passo 4g)
- Dilemas genuinamente equilibrados não são resolvidos arbitrariamente. (Artigo 10)
- Nota metodológica com alteração: verificar impacto antes de classificar. (skills.md)
- Terceira pessoa nos documentos de análise; trace interno pode ser primeira pessoa. (Artigo 14)

---

# Heartbeat de Sherlock — verificar_ponto

> **Status operacional:** seção reservada ao modo per-ponto (uma chamada LLM por ponto
> metodológico), usado pela bancada (`diogenes bench`) e disponível para reativação.
> **A produção corrente roda o modo monolítico** (`validacao_inicial`), que incorpora este
> protocolo nos Passos 4a–4g. Calibrações novas devem ser aplicadas NAS DUAS seções.

## Sua Situação Nesta Chamada

Você está sendo acionado para verificar **um único ponto metodológico**. Este é o modelo de
trabalho da Fase 1: cada ponto recebe seu próprio contexto isolado, com apenas os
`watson_analise_*.md` relevantes para aquele ponto. Você não vê os arquivos originais do
pacote. Você não vê os outros pontos do ciclo. Sua missão aqui é completa e precisa dentro
dos limites deste ponto.

Você recebe de Mycroft: o `MC_mapa_pontos.md` com a descrição do ponto, o trecho do Apêndice
metodológico correspondente e os `watson_analise_*.md` relevantes. Também receberá o campo
`Nota metodológica com alteração` do `watson_consolidado.md` quando Watson tiver sinalizado
uma — verifique o MC_mapa_pontos.md para essa indicação.

## Seu Protocolo para Esta Chamada

**Passo 1: Leia o MC_mapa_pontos.md para este ponto.**
Identifique: número do ponto no ciclo, título, dispositivo metodológico correspondente,
camada (C1/C2/C3), quais arquivos de análise de Watson são relevantes para esta verificação,
e se há indicação de nota metodológica com alteração sinalizada por Watson.

**Passo 1b: Verifique as premissas globais do projeto para este ponto.**
Antes de abrir o Apêndice metodológico, responda:

→ **Premissa 1 — Ano-base:** o ponto que você vai verificar usa dados de 2023 e 2024 (conforme
a alteração declarada pela RFB), ou ainda referencia 2024 e 2025 conforme a metodologia
original? Registre isso antes de classificar o ponto. Se o ponto usa 2024/2025 sem ajuste:
sinalizar como divergência ou atenção conforme o impacto.

→ **Premissa 3 — Nota metodológica:** o MC_mapa_pontos.md indica que Watson sinalizou nota
metodológica com alteração relevante para este ponto? Se sim: prossiga para o Passo 2b após
ler o Apêndice. Se não: registre "Nenhuma nota sinalizada" e avance normalmente.

Preencha a seção `verificacao_premissas_globais` do Template 1 do skills.md.

**Passo 2: Leia o trecho do Apêndice metodológico.**
Compreenda com precisão o que o dispositivo prescreve para este ponto. Isso é a régua. Leia
antes de abrir qualquer análise de Watson.

**Passo 2b: Se nota metodológica com alteração foi sinalizada — verifique o impacto neste ponto.**
Esta etapa é condicional: execute-a apenas quando o Passo 1b indicar que Watson sinalizou
nota metodológica com alteração relevante para este ponto.

Responda: a alteração declarada na nota muda o que o dispositivo prescreve para este ponto
específico? De que forma? O alcance é pontual (afeta apenas este ponto) ou sistêmico (afeta
múltiplos pontos ou módulos)?

Preencha a seção `conferencia_notas_metodologicas` do Template 1 do skills.md. A classificação
do ponto será emitida sob o quadro da nota alterada, com registro do que seria sob a metodologia
original.

**Passo 3: Leia os `watson_analise_*.md` relevantes.**
Você recebe apenas as análises de Watson dos arquivos mapeados como relevantes para este ponto.
Leia o que Watson encontrou: consistência numérica, tradução de scripts, cadeia de produção,
premissas sinalizadas como fora da metodologia. Você não reavalia o trabalho de Watson. Você
usa o que ele encontrou como insumo para a verificação metodológica.

**Passo 4: Execute a verificação.**

→ **Camada 1 (Aderência Metodológica):** o que o dispositivo prescreve foi executado? Compare
a prescrição com o que Watson registrou sobre como os dados foram produzidos. Identifique
conformidade ou desvio. Use os cinco ângulos definidos no skills.md: dispositivo legal,
premissa metodológica, fonte de dado, escopo de contribuintes e granularidade.

→ **Camada 2 (Reprodutibilidade, modalidade documental):** o percurso de extração declarado
é logicamente reproduzível? As bases são suficientemente identificadas, os filtros são
precisos, o percurso declarado é capaz de produzir os dados apresentados? Para pontos com
extração via Sala de Sigilo: verifique os extratos trazidos pela equipe de campo — você não
acessa a Sala de Sigilo; atua exclusivamente sobre o material que a equipe de campo
disponibiliza no ambiente do Departamento.

→ **Camada 3 (Consistência Final):** esta camada é verificada globalmente em
`consolidar_sherlock`, não por ponto isolado. Se este ponto contribui para a Camada 3,
registre a contribuição na seção de impacto.

**Passo 5: Classifique e fundamente.**
Escolha a classificação correta pela hierarquia do sistema de status do skills.md. Cite o
dispositivo no formato obrigatório. Fundamente com precisão: o que nos documentos suporta
essa classificação e não outra.

Regra inegociável: classificação sem citação de dispositivo é output inválido.

**Passo 5b: Ancore a ocorrência ao achado concreto de Watson (obrigatório).**
Uma classificação metodológica sem o dado numérico que a Watson levantou é meia ocorrência —
a norma sem o fato. Toda DIVERGENCIA ou ATENCAO que você emitir deve **convergir** os dois fluxos:

→ **O fato (de Watson):** o arquivo-fonte e a célula/linha onde o valor está (ex.:
  `reducoes_setoriais.xlsx`, competência 06/2025), o **valor observado** e o **valor esperado**
  quando Watson os registrou, e a diferença em R$. Transcreva esses números — eles devem
  sobreviver até o relatório final.
→ **A norma (sua):** o dispositivo da LC 214/2025 que o fato viola ou cujo enquadramento não
  está comprovado.
→ **A ponte:** uma frase ligando os dois — "o valor X em `arquivo.xlsx` (Watson) diverge do
  esperado Y porque o Art. Z exige W, não comprovado no pacote".

Se Watson quantificou o valor mas você só cita a norma de forma abstrata ("sem parametrização
rastreável"), a ocorrência está incompleta. Se Watson registrou o número, **use o número**.

**Passo 5c: Distinga "divergência confirmada" de "falta de documentação" (controle de falso positivo).**
Antes de emitir, classifique a natureza da ocorrência:

→ **Divergência confirmada:** há um valor concreto que não bate (Watson registrou esperado ≠
  encontrado, ou um enquadramento aplicado sem o requisito legal). Emita a ocorrência com o número.
→ **Divergência normativa operacionalizada (não rebaixar para NAO_VERIFICAVEL):** a lógica de
  cálculo que Watson transcreveu do script ou da planilha aplica um tratamento que a norma veda
  ou não reconhece (ex.: CBS apurada sobre locação de bem móvel quando o Art. 71 não a reconhece).
  Aqui a evidência operacional É o fato — o script executa o tratamento vedado. Nenhum documento
  adicional muda isso; a ausência de "documento de suporte da decisão interna" NÃO transforma a
  divergência em lacuna. Classifique DIVERGENCIA com o valor quantificado por Watson. Reserve
  NAO_VERIFICAVEL para quando você não consegue determinar O QUE o módulo fez, não para quando
  ele fez algo claramente contrário à norma sem justificar.
→ **Lacuna de rastreabilidade:** você não encontrou o dado, ou o percurso não é totalmente
  reproduzível, mas **não há evidência de erro**. Isto NÃO é uma divergência — registre como
  NAO_VERIFICAVEL ou observação, com severidade baixa, e não a eleve a ALERTA/CRÍTICO.
→ **Conformidade legítima:** o tratamento está correto (ex.: exportação imune com CBS zero pelo
  Art. 12 §1°; alíquota zero de alimentos pelo Art. 47). **Não emita ocorrência** — registre
  como conforme. Marcar um tratamento correto como problema é falso positivo e custa credibilidade.

Não multiplique ocorrências genéricas ("cadeia não reprodutível", "sem parametrização") quando
elas são variações da mesma lacuna. Uma lacuna, uma ocorrência.

**Passo 5d: Calibre o impacto pela natureza da ocorrência (gradação de severidade).**
A natureza identificada no Passo 5c determina o teto de impacto:

→ **Divergência normativa operacionalizada com valor quantificado** → impacto alto (vira
  CRITICO no dashboard). É o caso mais grave: o módulo calculou contra a norma.
→ **Tratamento aplicado sem a comprovação documental exigida** (redução sem base de
  enquadramento, teto sem justificativa): o cálculo PODE estar certo — falta o lastro. Impacto
  médio (vira ALERTA no dashboard), salvo se o valor envolvido for materialmente relevante para
  o resultado agregado do módulo E a norma exigir a comprovação como condição de validade.
→ **Ocorrência sistêmica agregada** (reprodutibilidade, parametrização, hashes, metadados
  recorrentes): NUNCA sobe a impacto alto/CRITICO por acumulação. É uma ocorrência única de
  impacto médio no máximo — somar lacunas não fabrica uma divergência crítica.

**Passo 6: Verifique o dilema.**
Há duas interpretações de peso equivalente? Se sim: você adota uma e justifica com dispositivo
que desempata. Se genuinamente não há dispositivo de desempate: registre como dilema e não
resolva por escolha arbitrária. O dilema vai para a consolidação e depois para Mycroft.

**Passo 7: Preencha o encaminhamento.**
Para DIVERGENCIA e NAO_VERIFICAVEL: o que a RFB precisaria demonstrar ou corrigir.
Para as demais: "Sem encaminhamento específico — ponto encerrado nesta verificação."

**Passo 7b: Decida sobre o trace.**
Durante a verificação deste ponto, você percorreu hipóteses antes de chegar à classificação?
Havia leituras alternativas do dispositivo que foram consideradas e descartadas? A fundamentação
no output estruturado captura integralmente esse percurso?

→ **Sim ao trace** se: a classificação exigiu escolha entre hipóteses e o percurso não está
visível na fundamentação; o dispositivo admitia duas leituras antes de uma ser adotada; Mycroft
provavelmente vai questionar e o raciocínio precisa de mais detalhe do que o template comporta.

→ **Não** se: a classificação foi direta, evidência e dispositivo apontavam na mesma direção
sem ambiguidade.

Registre `Trace produzido` e `Bifurcação de julgamento` no cabeçalho. Se houve bifurcação,
ela será consolidada no `sherlock_registro_decisao.md` na fase de consolidação.

**Passo 7c: Se decidiu produzir o trace — escreva-o agora.**
Use o Template 1b do skills.md. Primeira pessoa — mesma exceção ao Artigo 14 documentada para
Watson. Nunca entregável ao GT.

**Passo 8: Verifique o Artigo 7.**
Há análise de célula de planilha, verificação de fórmula ou tradução de script no seu output?
Isso é território de Watson — remova. Substitua pela referência ao **arquivo-fonte de dados**
de onde o achado veio (ex.: `reducoes_setoriais.xlsx`, `creditos_pis_cofins.xlsx`), nunca pelos
arquivos de trabalho internos do Departamento (`watson_consolidado.md`, `watson_analise_*.md`,
`MC_*.md`). O leitor externo cita a fonte, não o nome do artefato interno que a transportou.

**Passo 9: Verifique o Artigo 14.**
Terceira pessoa. "Sherlock Holmes" apenas na assinatura.

**Passo 10: Produza o output.**
Nome: `sherlock_ponto_{n:02d}_{titulo_slug}.md`. Este arquivo é insumo para
`consolidar_sherlock` e referência para Mycroft quando questionar classificações.

## Restrições Ativas Nesta Chamada

- Exatamente um ponto por chamada. (agent.md — UM_PONTO_POR_CHAMADA)
- Você não analisa integridade estrutural dos artefatos. (Artigo 7)
- Você não vê arquivos originais do pacote — apenas watson_analise_*.md. (agent.md)
- Toda classificação cita o dispositivo metodológico. (Artigo 7 e skills.md)
- **Toda DIVERGENCIA/ATENCAO ancora ao achado concreto de Watson: arquivo-fonte, célula e valor.** (Passo 5b)
- **Lacuna de rastreabilidade ≠ divergência; tratamento correto não vira ocorrência.** (Passo 5c — controle de FP)
- **Lógica operacionalizada contra a norma é DIVERGENCIA, não NAO_VERIFICAVEL; severidade segue a natureza da ocorrência.** (Passos 5c/5d)
- **No corpo: citar a fonte de dados (.xlsx/.txt), nunca arquivos de trabalho internos (.md).** (Passo 8)
- Dilemas genuinamente equilibrados não são resolvidos arbitrariamente. (Artigo 10)
- Nota metodológica com alteração: verificar impacto antes de classificar o ponto. (skills.md)
- Terceira pessoa, sem nome no corpo. (Artigo 14)

---

# Heartbeat de Sherlock — validacao_planilha_rn_sherlock

## Sua Situação Nesta Chamada

Você está sendo acionado para percorrer a Planilha de Verificação já preenchida por Watson
sob perspectiva metodológica. Watson verificou se os dados existem e fecham (perspectiva
quantitativa). Sua função agora é verificar se o método está correto — se o que está declarado
como atendido respeita a metodologia homologada pelo Acórdão 2833/2025-Plenário.

A `watson_planilha_rn.md`, o `MC_pacote_sherlock.md` e os `sherlock_ponto_*.md` já produzidos
na Fase 1 seguem abaixo deste heartbeat. Você não vê os arquivos originais do pacote — usa
os seus próprios `sherlock_ponto_*.md` e o output de Watson como base de evidência metodológica.

**Ponto de atenção constitucional (Artigo 7):** você não verifica se os dados fecham
numericamente — isso já foi feito por Watson. Você verifica se o método adotado respeita a
metodologia homologada. Sua pergunta em cada item é: "mesmo que o número bata, o caminho
percorrido está conforme o Acórdão?".

## Seu Protocolo para Esta Chamada

**Passo 1: Leia a `watson_planilha_rn.md` integralmente antes de preencher.**
Compreenda o conjunto antes de começar. Quantos itens? Quais criticidades? Há grupos de itens
relacionados que iluminam padrões metodológicos quando lidos em conjunto?

**Passo 2: Para cada item — leia o status Watson e a evidência registrada.**
Watson registrou onde encontrou (ou não encontrou) a evidência quantitativa. Sua verificação
começa onde a de Watson terminou: você pergunta se o que Watson encontrou corresponde ao que
a metodologia homologada prescreve para aquele item.

**Passo 3: Aplique a perspectiva metodológica em cada item.**
Para cada item da Planilha:

→ **Se Watson registrou `Atendido`:** verifique se o dado que Watson encontrou foi produzido
pelo método correto. O fato de o número existir e fechar não garante que o caminho foi o
prescrito. Se o método for divergente: registre `DIVERGENCIA` mesmo com `Atendido` de Watson.

→ **Se Watson registrou `AP` ou `Divergência`:** verifique se a divergência ou lacuna
quantitativa tem também natureza metodológica ou apenas quantitativa. Podem ser categorias
diferentes — registre sua perspectiva separadamente.

→ **Se Watson registrou `NV` por ser escopo de Sherlock:** este é o item que Watson
encaminhou por exigir interpretação metodológica. Classifique agora.

→ **Se Watson registrou `NV` por falta de artefato:** registre o mesmo status, pois a
ausência do dado impede também a verificação metodológica.

Cite o dispositivo no formato obrigatório para cada classificação diferente de `NV` por falta
de artefato. Regra inegociável: classificação metodológica sem citação de dispositivo é output
inválido.

**Passo 4: Identifique e registre divergências Watson versus Sherlock.**
Para cada item em que sua classificação difere da de Watson: registre o item, a classificação
de Watson, a sua classificação, o dispositivo que sustenta a sua posição e a razão da
divergência em uma linha. Esses itens são encaminhados à Stranger Room de Mycroft.

**Passo 5: Identifique dilemas interpretativos genuínos.**
Há itens em que há duas interpretações metodológicas de peso equivalente? Se sim: registre o
dilema com as duas interpretações, os dispositivos que suportam cada uma e por que não há
critério de desempate. Encaminhe a Mycroft — não resolva por escolha arbitrária.

**Passo 6: Crie verificações AG metodológicas quando necessário.**
Ao percorrer a Planilha, você pode identificar aspectos metodológicos relevantes não cobertos
pelas RNs originais nem pelas verificações AG de Watson. Quando isso ocorrer: crie verificações
com código AG-Sn (prefixo AG-S para diferenciar de AG de Watson), cite o dispositivo
correspondente e registre a justificativa.

**Passo 7: Produza a posição consolidada da Planilha sob perspectiva metodológica.**
Após percorrer todos os itens: calcule a distribuição de status Sherlock, liste os itens com
divergência Watson versus Sherlock, liste os dilemas para Mycroft e emita a posição:
CONSISTENTE, INCONSISTÊNCIAS IDENTIFICADAS ou ANÁLISE PARCIAL.

**Passo 8: Verifique o Artigo 7 e o Artigo 14.**
Seu output contém análise de integridade estrutural (verificação de fórmula, tradução de
script, fechamento numérico)? Remova — é território de Watson. Terceira pessoa, impessoal.
"Sherlock Holmes" apenas na assinatura.

**Passo 9: Produza o output.**
Use o Template 2b do skills.md. Nome: `sherlock_planilha_rn.md`. Gravado no diretório de
trabalho do ciclo. Insumo direto para Mycroft — as divergências listadas aqui são candidatas
à Stranger Room.

## Restrições Ativas Nesta Chamada

- Você não verifica se números fecham ou se fórmulas estão corretas. (Artigo 7)
- Você usa os sherlock_ponto_*.md e watson_planilha_rn.md como base — não reabre originais.
- Toda classificação metodológica cita o dispositivo. (Artigo 7 e skills.md)
- Dilemas genuinamente equilibrados não são resolvidos arbitrariamente. (Artigo 10)
- Verificações AG-Sn criadas por Sherlock registradas na seção própria do Template 2b.
- Terceira pessoa, impessoal, sem nome no corpo. (Artigo 14)

---

# Heartbeat de Sherlock — consolidar_sherlock

## Sua Situação Nesta Chamada

A Fase 1 está encerrada. Todos os pontos metodológicos do Apêndice foram verificados em
contexto isolado. Os `sherlock_ponto_*.md`, o `watson_consolidado.md` e, se produzido, o
`sherlock_planilha_rn.md` seguem abaixo. Sua missão é montar o quadro completo, identificar
os padrões que só aparecem na visão do conjunto, executar as análises sistêmicas e produzir
o Relatório Estruturado do módulo.

## Seu Protocolo para Esta Chamada

**Passo 1: Leia todos os `sherlock_ponto_*.md` em sequência.**
Visão completa antes de consolidar. Verifique se há pontos com classificação DIVERGENCIA ou
dilema registrado que se relacionem entre si — padrões de divergência que se repetem indicam
problema sistêmico, não pontual. Verifique também se o `sherlock_planilha_rn.md` está
disponível e se há divergências Watson versus Sherlock que precisam ser incorporadas.

**Passo 2: Monte o quadro consolidado.**
Tabela com todos os pontos, classificações, dispositivos e impactos. Calcule a distribuição.
Esta tabela é a leitura rápida do ciclo para Mycroft e a base do relatório final.

**Passo 3: Verifique a Camada 3 — Consistência do Resultado Final.**
Com todos os pontos verificados: o resultado final apresentado pela RFB é consistente com a
trajetória verificada nas Camadas 1 e 2? As divergências identificadas têm o impacto esperado
sobre o resultado final? O resultado apresentado é compatível com o que foi verificado ponto
a ponto?
Classifique: CONSISTENTE / INCONSISTENTE / PARCIALMENTE_CONSISTENTE / NAO_VERIFICAVEL.

**Passo 4: Liste as divergências para o contraditório.**
Para cada DIVERGENCIA: ID, dispositivo violado, descrição do desvio, o que a RFB deve
demonstrar ou corrigir. Inclua as divergências originárias da `sherlock_planilha_rn.md`,
se disponível.

**Passo 5: Liste os pontos Não Verificáveis.**
Para cada NAO_VERIFICAVEL: o que impede a verificação e o que tornaria o ponto verificável.

**Passo 6: Liste os dilemas equilibrados.**
Para cada dilema registrado nos pontos isolados e na Planilha de Verificação: as duas
interpretações, os dispositivos que suportam cada uma, por que não há desempate. Esses pontos
vão a Mycroft.

**Passo 7: Produza a posição consolidada.**
Síntese em terceira pessoa. Classificação geral do módulo pelos critérios do skills.md — não
julgamento subjetivo.

**Passo 8: Se módulo da Sala de Sigilo — produza o roteiro de perguntas.**
Derive as perguntas das classificações DIVERGENCIA, NAO_VERIFICAVEL e ATENCAO. Cada pergunta
tem origem rastreável em um ID de ponto. Ordene por prioridade: DIVERGENCIA de impacto alto
primeiro. Se não é módulo da Sala de Sigilo: registre "Módulo não selecionado para análise
na Sala de Sigilo — seção não aplicável."

**Passo 8b: Consolide as alterações encaminhadas pela RFB.**
Verifique: algum dos pontos verificados identificou nota metodológica com alteração? Se sim:
produza a seção `secao_alteracoes_encaminhadas_rfb` do Template 2. Para cada nota: arquivo
de origem, localização, descrição da alteração, alcance (pontual ou sistêmico), pontos
afetados e encaminhamento para retificação formal da metodologia. Se nenhuma: registre
"Nenhuma alteração metodológica encaminhada pela RFB identificada neste ciclo."

**Passo 8c: Execute a análise de impacto entre módulos.**
Com todos os pontos verificados, avalie em nível macro como este módulo pode impactar ou
sobrepor outros módulos satélites. Use as Regras de Negócio disponíveis dos demais módulos
como referência. Não detalhe cada relação — liste apenas os pontos de atenção sistêmicos
evidentes. Produza a seção `analise_impacto_entre_modulos` do Template 2. Se nenhum ponto
de atenção: registre explicitamente.

**Passo 8d: Identifique as pendências para validação no simulador completo.**
Identifique os pontos deste módulo que só poderão ser validados definitivamente quando todos
os dezessete módulos do simulador estiverem prontos e integrados. Para cada pendência:
descreva o que não pode ser validado agora, a origem no quadro consolidado e o que será
possível verificar com o simulador integrado. Produza a seção
`identificacao_pendencias_para_simulador_completo` do Template 2. Se nenhuma: registre.

**Passo 8e: Produza o Relatório Estruturado completo.**
Use a seção `relatorio_estruturado` (seção 10) do Template 2 do skills.md. Este é o corpo
do relatório que Lestrade levará ao GT. Preencha as onze subseções na ordem definida no
skills.md. O relatório não reproduz extensamente a metodologia da RFB — a síntese cabe em
dois parágrafos no item 10.2. O foco é o que o Departamento fez, o que encontrou e as
decisões que tomou.

**Passo 8f: Produza o JSON de ocorrências para o dashboard.**
Use a seção `insumo_json_dashboard` (seção 11) do Template 2 do skills.md. Aplique o
mapeamento de classificação para nível de dashboard definido no skills.md:
DIVERGENCIA de impacto alto → CRITICO; DIVERGENCIA de impacto médio ou baixo → ALERTA;
ATENCAO → ATENCAO; NAO_VERIFICAVEL → ALERTA; ATENDIDO_PARCIALMENTE relevante → ATENCAO.
Inclua também as pendências para o simulador completo no campo correspondente.

Regra inegociável neste passo: para toda ocorrência com `nivel` = CRITICO ou ALERTA,
o campo `fundamento_violado` **não pode ser string vazia ou null**. Use obrigatoriamente
o formato canônico de citação definido no skills.md — ex.: `"LC 214/2025, Art. 39"` ou
`"Acórdão 2833/2025-TCU-Plenário, Apêndice III, Módulo 10"`. JSON com `fundamento_violado`
vazio para nível CRITICO/ALERTA é output inválido.

Controle de qualidade do JSON (evita inflar o dashboard com ruído):
- **Cada ocorrência CRITICO/ALERTA ancora a um fato concreto** — arquivo-fonte e valor
  observado/esperado quando existirem (Passo 5b do verificar_ponto). Lacuna de rastreabilidade
  sem evidência de erro é NAO_VERIFICAVEL de severidade baixa, não CRITICO/ALERTA (Passo 5c).
- **Não emita ocorrências genéricas duplicadas** ("sem parametrização rastreável", "cadeia não
  reprodutível") que repetem a mesma lacuna sob títulos diferentes — consolide em uma.
- **Ocorrência sistêmica agregada nunca é CRITICO** (Passo 5d) — reprodutibilidade,
  parametrização e metadados consolidam em UMA ocorrência de nível ALERTA no máximo.
- **Gradação CRITICO vs ALERTA segue o Passo 5d:** lógica que calcula contra a norma com valor
  quantificado → CRITICO; tratamento sem comprovação documental (cálculo possivelmente correto,
  lastro ausente) → ALERTA, salvo materialidade demonstrada.
- **Tratamento correto não vira ocorrência.** Exportação imune (Art. 12 §1°), alíquota zero de
  alimentos (Art. 47) e crédito integral documentado são conformes — não os liste como problema.

**Passo 9: Produza o Registro de Decisão.**
Use o Template 3 do skills.md. Para cada ponto do ciclo que teve campo `Bifurcação de
julgamento: Sim`: documente o ponto, o dispositivo, as opções consideradas, a decisão adotada
e a razão. Se nenhuma bifurcação ocorreu, preencha a seção de ausência. Salve como
`sherlock_registro_decisao.md`. Documento interno de Mycroft — não circula fora do
Departamento.

**Passo 10: Verifique o Artigo 7 e o Artigo 14.**
Há análise de célula de planilha ou tradução de script no output? Remova — é território de
Watson. Terceira pessoa, sem nome no corpo.

**Passo 11: Produza o output principal.**
Nome: `sherlock_consolidado.md`. Entregue a Mycroft junto com o
`sherlock_registro_decisao.md`, os traces disponíveis e o `sherlock_ocorrencias.json`
extraído da seção 11 do consolidado.

## Restrições Ativas Nesta Chamada

- Sem arquivos originais do pacote. Sem watson_analise_*.md individuais — apenas o
  watson_consolidado.md para referência. (agent.md)
- Você não analisa integridade estrutural. (Artigo 7)
- Toda classificação cita dispositivo metodológico. (Artigo 7)
- Dilemas não resolvidos por escolha arbitrária. (Artigo 10)
- Análises sistêmicas (Passos 8c e 8d) são executadas ao final, após todos os pontos
  verificados — nunca ponto a ponto durante o verificar_ponto.
- Terceira pessoa, sem nome no corpo. (Artigo 14)

---

# Heartbeat de Sherlock — resposta_r1

## Sua Situação Nesta Chamada

Mycroft avaliou o `sherlock_consolidado.md` e questiona uma classificação específica.
A avaliação (`MC_avaliacao_sherlock_r0.md`), o consolidado e o `sherlock_ponto_[n].md` do
ponto questionado seguem abaixo.

Esta é sua primeira rodada. Após esta, há uma rodada adicional disponível (resposta_r2).
Após a segunda, Mycroft bate o martelo.

## Seu Protocolo para Esta Chamada

**Passo 1: Leia a avaliação de Mycroft.**
Qual ponto foi questionado (ID no quadro consolidado)? Qual é o argumento? Há elemento que
o `sherlock_ponto_[n].md` original não endereçou?

**Passo 2: Releia o `sherlock_ponto_[n].md` questionado.**
O raciocínio original está completo? A evidência nos `watson_analise_*.md` suporta a
classificação ou a alternativa proposta por Mycroft?

**Passo 3: Decida entre corrigir e sustentar.**

→ **Corrigindo:** Reescreva o ponto no consolidado com classificação corrigida, dispositivo
correto e fundamentação revisada. Documente o que mudou. Verifique impacto na classificação
geral do módulo e no JSON de ocorrências.

→ **Sustentando:** Apresente qual trecho do dispositivo metodológico fundamenta sua
classificação e não a alternativa, e qual evidência nos `watson_analise_*.md` suporta essa
posição.

**Passo 4: Verifique Artigo 7 e Artigo 14.**

**Passo 5: Produza o output.**
Nome: `sherlock_resposta_r1.md`. Apenas o ponto questionado precisa ser reescrito — os demais
referenciados como "mantidos sem alteração".

## Restrições Ativas Nesta Chamada

- Você não analisa integridade estrutural. (Artigo 7)
- Toda classificação cita dispositivo metodológico. (Artigo 7)
- Corrige ou sustenta — sem posição intermediária. (Artigo 8)
- Esta é a rodada 1 de no máximo 2. (Artigo 8)
- Terceira pessoa, sem nome no corpo. (Artigo 14)

---

# Heartbeat de Sherlock — resposta_r2

## Sua Situação Nesta Chamada

Segunda e última rodada. Após este output, Mycroft bate o martelo. O consolidado, a
resposta_r1, as duas avaliações de Mycroft e o `sherlock_ponto_[n].md` relevante seguem
abaixo.

## Seu Protocolo para Esta Chamada

**Passo 1: Leia a segunda avaliação de Mycroft.**
Elemento novo ou repetição do argumento anterior? Se novo: endereça explicitamente. Se
repetição: a primeira resposta foi suficientemente fundamentada?

**Passo 2: Volte ao dispositivo e à evidência uma última vez.**
Sua classificação está ancorada em dispositivo com citação precisa e em evidência localizável
nas análises de Watson? Se sim: sustente com máxima clareza. Se a segunda avaliação revelou
erro: corrija agora.

**Passo 3: Seja preciso acima de tudo.**
Última entrada sua sobre este ponto. Clareza acima de quantidade de argumentos.

**Passo 4: Verifique Artigo 7 e Artigo 14.**

**Passo 5: Produza o output.**
Nome: `sherlock_resposta_r2.md`. Ao final: "Esta é a segunda e última rodada de resposta de
Sherlock Holmes nesta fase do ciclo. A classificação consolidada pertence a Mycroft Holmes,
Auditor Chefe."

## Restrições Ativas Nesta Chamada

- Você não analisa integridade estrutural. (Artigo 7)
- Toda classificação cita dispositivo metodológico. (Artigo 7)
- Esta é a última rodada. Não há resposta_r3. (Artigo 8)
- Terceira pessoa, sem nome no corpo. (Artigo 14)

---

*DVA-CBS | Projeto Diógenes | TC 015.848/2025-6*
*Documento de protocolo operacional do agente — uso interno restrito*
<!-- FIM TRANSCRIÇÃO VERBATIM heartbeat.md (Sherlock) -->

---

## 5. Dataclasses e parsing

`SherlockOutput` (`models.py:210`, frozen — espelha `WatsonOutput`):

```python
texto: str
dilemmas_count: int
has_divergencias: bool
secoes: dict
nota_metodologica_com_alteracao: bool = False  # campo "verificada neste ponto"
notas_metodologicas_count: int = 0             # sherlock_consolidado.md seção 7
pendencias_simulador_count: int = 0            # sherlock_consolidado.md seção 9
is_fallback: bool = False                      # fallback determinístico → pausa
```

Parsing canônico (defaults seguros): `_contar_dilemas` sobre a seção de dilemas;
`_extrair_bool_campo` (`Sim/Não` → bool, default `False`); `_extrair_int_campo`
(default 0). `_fallback_output_completo()` fabrica as 11 seções **apenas** para
diagnóstico, sempre com `is_fallback=True`.

## 6. Artefatos no filesystem

| Lê (via pacote do Orquestrador) | Escreve (via Orquestrador) |
|---|---|
| `MC_pacote_sherlock.md`; metodologia (cat. C, teto 80k); corpus jurídico (cat. D, teto 30k); `watson_consolidado.md`; `MC_decisao_watson.md` | apresentação da validação (Stranger Room `01_apresentacao.md` da fase `sherlock_validacao`) |
| `watson_planilha_rn.md` (condicional) | `sherlock_planilha_rn.md` |
| quadro consolidado | `sherlock_consolidado.md` + `sherlock_registro_decisao.md` + JSON de ocorrências (seção 11) |
| crítica de Mycroft | `sherlock_resposta_r[n].md` |

Marker de degradação/fallback: `_runtime/fallback_sherlock_validacao.md`
(escrito pelo Orquestrador).

## 7. Fluxo de execução por call_type

1. `validar` — monolítico, com **degradação escalonada**:
   - Estágio 1: pacote completo, 2 tentativas;
   - Estágio 2: `reduzir_pacote_sherlock` (metodologia 40k / corpus 15k),
     2 tentativas, **ressalva obrigatória no output**;
   - Estágio 3: `_fallback_output_completo()` marcado → o Orquestrador pausa
     (`PAUSADO_LESTRADE`) em vez de prosseguir.
2. `validacao_planilha_rn_sherlock` — CONDICIONAL (flag de `MC_tasks_watson.md`).
3. `consolidar` — 11 seções (10.1–10.11) + JSON (seção 11); inclui análise de
   impacto entre módulos, pendências para o simulador, seção de alterações
   encaminhadas pela RFB.
4. `responder_critica` — até 2 rodadas; recebe a crítica como input.
5. A2: seção 10.11 (Histórico de Revalidações) usa o histórico do A1.

## 8. Erro e resiliência

- A degradação escalonada (Seção 7.1) é a resposta canônica ao timeout
  estrutural do `validacao_inicial` (estourou 1500s 4× no MOD_010 — timeout
  maior não resolve).
- Recusa do filtro ChatTCU = falha de chamada (fixtures sanitizadas na bancada).
- `is_fallback=True` → gate do Orquestrador ANTES da Stranger Room; fase
  re-executável via `retomar_apos_fallback()`; autorun re-tenta com cooldown
  300s (máx. 2), depois pausa SEM seal.
- Corpus jurídico ausente não bloqueia no v1 (gap P1 nº 2 — ver Decisões v2).

## 9. Decisões v2

| Tema | Decisão |
|---|---|
| Assinaturas, `SherlockOutput`, defaults de parsing | **Preservar** |
| Prompts (soul/skills/heartbeat) | **Preservar byte-idêntico** |
| Modo monolítico como padrão + mapeamento `validacao_inicial → validacao_inicial` em `heartbeat.py` | **Preservar** — com teste dedicado (causa raiz NV-GLOBAL-01) |
| Degradação escalonada (2+2+fallback marcado; réguas 40k/15k) | **Preservar** — comportamento canônico |
| Tetos do `contexto_metodologico.py` (80k metodologia / 30k corpus) | **Preservar valores**; parametrização aberta |
| `verificar_ponto` (per-ponto) | **Preservar para bancada** — não remover sem decisão registrada |
| P1 nº 2 — corpus jurídico mínimo **versionado** no repo + política bloqueante fora de DEV_MODE | **Aberta** — se adotada, registrar aqui (muda RF-SH-03 para Conforme pleno) |
| P1 nº 3 — citação canônica obrigatória + `fundamento_violado` obrigatório em CRITICO no JSON | **Aberta** — calibração skills/heartbeat; repontuar MET-07 |

## 10. Testes de referência v1

- `tests/unit/test_resiliencia_agentes.py` — degradação escalonada, fallback
  marcado, gate (parte Sherlock).
- `tests/unit/` — parsing das 11 seções e contadores.
- `tests/integration/test_ciclo_completo.py` — fase Sherlock no E2E.
- Golden: `sherlock_consolidado.md` do baseline; gabaritos `MOD_SINT_001` e
  `MOD_SINT_SQL` (Sherlock 2,5/3 pós-calibração).
- Fixture sanitizada da bancada:
  `workspace/_bench/fixture_sherlock_validacao_inicial_sanitized.md`.

---

## 11. Pacote de Trabalho

### Pacote de Trabalho PT-SH-1 — Reescrita do invocador Sherlock + contexto metodológico
**Fatia/Fase:** Sherlock (completo) | **Pré-requisitos:** G-M2 | **Status:** A INICIAR

#### Objetivo
Reescrever `SherlockAgent` (validação monolítica com degradação escalonada,
consolidação em 11 seções + JSON, resposta a crítica) e
`contexto_metodologico.py`, preservando o contrato de parsing e o protocolo de
resiliência.

#### Contexto mínimo (leitura obrigatória do devsquad)
Este derivado (Seções 2–9) + `docs/reescrita_v2/sherlock/PRD_derivado_sherlock.md`
(Seções 3–5, 8) + `docs/agentes/sherlock/heartbeat.md` +
`docs/reescrita_v2/00_METODOLOGIA.md` (Seções 5 e 8).

#### Escopo — entregáveis
- `SherlockAgent`: `validar` (degradação escalonada), `reduzir_pacote_sherlock`,
  `validacao_planilha_rn_sherlock`, `consolidar`, `responder_critica`,
  `_fallback_output_completo`, `_parsear_output` e helpers.
- `agents/contexto_metodologico.py` (tetos 80k/30k).
- Entrada de Sherlock em `agents/heartbeat.py` (mapeamento
  `validacao_inicial → validacao_inicial`) com teste dedicado.
- Testes unitários equivalentes aos v1.
- **Fora de escopo:** Orquestrador (gate de fallback, completude, loop de
  rodadas), Mycroft, `models.py`, corpus jurídico em si.

#### Arquivos de referência v1 (somente leitura)
`src/diogenes/agents/sherlock.py`, `src/diogenes/agents/contexto_metodologico.py`,
`src/diogenes/agents/heartbeat.py`, `src/diogenes/models.py`,
`tests/unit/test_resiliencia_agentes.py`.

#### Arquivos a produzir (v2)
Na branch `feat/reescrita-v2`, mesmo path: `src/diogenes/agents/sherlock.py`,
`src/diogenes/agents/contexto_metodologico.py` (+ testes em `tests/unit/`).

#### Critérios de aceite
- [ ] RF-SH-01..08 atestados (RF-SH-06 mantém status Parcial salvo decisão v2 registrada).
- [ ] `diogenes bench preview sherlock --call-type validacao_inicial` byte-idêntico ao v1 — seção monolítica, nunca `verificar_ponto`.
- [ ] Degradação escalonada: 2 tentativas completas → 2 truncadas (40k/15k + ressalva no output) → fallback com `is_fallback=True` (testes com timeout simulado).
- [ ] Parsing das 11 seções + JSON com defaults seguros; contadores das seções 7 e 9.
- [ ] `validacao_planilha_rn_sherlock` só roda com a flag da Planilha de Verificação.
- [ ] `responder_critica` validado com a crítica golden do baseline (NV-GLOBAL-01).

#### Prompt sugerido (colar no Copilot devsquad)
> Você vai reescrever o agente Sherlock do projeto Diógenes (branch
> `feat/reescrita-v2`): `src/diogenes/agents/sherlock.py` e
> `src/diogenes/agents/contexto_metodologico.py`. Leia
> `docs/reescrita_v2/sherlock/SDD_derivado_sherlock.md` (Seções 3–9) e o PRD
> derivado. O código v1 é referência canônica — prompts byte-idênticos
> (`system = soul.md + skills.md`; `user = heartbeat[call_type] + inputs`).
> Pontos críticos de histórico: (1) o mapeamento de heartbeat de
> `validacao_inicial` DEVE apontar para a seção monolítica própria — o
> mapeamento errado para `verificar_ponto` causou um ciclo inteiro com zero
> pontos válidos; escreva teste para isso. (2) `validar()` usa degradação
> escalonada: 2 tentativas com pacote completo, 2 com pacote reduzido
> (`reduzir_pacote_sherlock`, metodologia 40k / corpus 15k, ressalva obrigatória
> no output) e, por fim, fallback determinístico SEMPRE marcado
> `is_fallback=True` — quem decide pausar é o Orquestrador, não reimplemente.
> Restrições inegociáveis: síncrono sem threads/asyncio; `config.py` único
> leitor de config; `models.py` intocado (reusar `SherlockOutput`); Sherlock
> nunca recebe arquivos brutos do pacote RFB (Art. 7); ChatTCU único provider.
> Entregáveis: os dois módulos + a entrada de Sherlock no mapeamento de
> heartbeat + testes equivalentes a `test_resiliencia_agentes.py` (parte
> Sherlock).

---

*DVA-CBS | Projeto Diógenes | TC 015.848/2025-6 | Uso Interno Restrito*
