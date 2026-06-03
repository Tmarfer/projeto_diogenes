# Dossiê de Validação — Irene Adler

**Veredito preliminar:** ✅ Aderente ao contrato no essencial (gate funciona, limites
constitucionais respeitados), com **5 achados** — 1 de calibração de modelo, 2 de
documentação desatualizada e 2 de granularidade de risco. Nenhum bloqueante.

Base: contrato em `contrato.md` + comportamento real do ciclo `MOD_010_A1_20260602T202655Z`
(auditado a partir de `irene_catalog.yaml` e do log de execução — sem custo de token).

---

## O que está aderente (confirmado)

- **Gate de recomendação correto:** `score_consolidado 0.9529 ≥ 0.95 → APROVADO`. ✓
- **Pipeline C1–C5 íntegro:** 71 abas perfiladas (C3, 269s) e classificadas (C4, 1.998s);
  fallback openpyxl operou quando 3 CSVs estavam ausentes, sem abortar. ✓
- **Limite constitucional respeitado:** as `flags_atencao` e justificativas descrevem
  **estrutura** ("nome sugere valor monetário mas tipo físico é str"; "inconsistência
  entre nº de colunas declarado e estatísticas"), nunca correção fiscal ou metodologia.
  Irene não invadiu território de Watson nem de Sherlock. ✓
- **11 papéis** aplicados; cobertura semântica coerente com o conteúdo das abas. ✓

---

## Achados

### F1 — Modelo do C4 diverge da documentação *(calibração)*
- **Projetado:** `agent.md` declara `model: "Claude 4.6 Sonnet"` (temp 0.1, timeout 180s);
  `.env` tem `IRENE_MODEL=Claude 4.6 Sonnet`.
- **Real:** o log do run mostra `[Irene] C4 — Modelo: gpt-5.5-thinking`.
- **Risco:** a classificação semântica rodou num modelo diferente do documentado. Pode ser
  intencional (frente de avaliação gpt-5.5), mas não há registro disso. `carregar_config_irene()`
  lê a config própria do pacote `irene`, **não** o `agents_spec.yaml` do Diógenes — duas
  fontes de verdade de modelo coexistindo.
- **Ação proposta:** alinhar `agent.md` + `.env` ao modelo realmente usado, OU documentar
  explicitamente por que o C4 usa outra família. Decidir qual é a fonte de verdade do modelo da Irene.

### F2 — `heartbeat.md` e `agent.md` descrevem estrutura de diretórios obsoleta *(doc drift)*
- **Projetado:** `heartbeat.md` fala em `input/{modulo}/XLSX/` e saída em `IRENE_OUT/{modulo}/`.
- **Real:** `_derivar_manifesto_irene` varre a estrutura hierárquica real
  (`01_ENTRADA_COPIADA` + `04_TRANSFORMADO`, via `rglob`) e o catálogo é copiado para
  `cycles/{id}/irene_catalog.yaml`. O `CATALOGO.json` é auto-gerado se ausente.
- **Risco:** documentação induz a erro quem for manter o agente.
- **Ação proposta:** atualizar `heartbeat.md`/`agent.md` para a topologia real do `--delivery`.

### F3 — Confiança baixa por aba não gera flag de revisão *(granularidade de risco)*
- **Observado:** abas com `confianca_papel` 0.72–0.78 (ex.: `2n02` 0.74, `Números` 0.72,
  `Rend Trab Não Assalariado` 0.72) ficaram com `requer_revisao_humana: false`.
- **Risco:** o `score_consolidado` 0.9529 (média ponderada) mascara abas individualmente
  frágeis. Watson recebe essas abas sem sinalização de baixa confiança de papel.
- **Ação proposta:** avaliar em `skills.md`/C5 um limiar por aba (ex.: `confianca_papel < 0.80
  → requer_revisao_humana: true`) independente do score consolidado.

### F4 — `resultado_final` com confiança 0.72 não dispara atenção reforçada *(regra do gate)*
- **Observado:** a aba `Números` foi classificada `resultado_final` com `confianca_papel 0.72`.
- **Contrato:** o gate só bloqueia em "falha em aba `resultado_final`" — confiança baixa
  não conta como falha. Mas uma aba de resultado conclusivo com 0.72 é exatamente onde um
  erro de papel é mais caro.
- **Ação proposta:** elevar o tratamento de `resultado_final` com confiança baixa (flag ou
  rebaixar recomendação para ALERTA), discutir limiar no `skills.md`.

### F5 — Sem ocorrência (controle positivo)
Nenhuma violação de limite constitucional detectada. Registrado como evidência de conformidade.

---

## Teste de confirmação isolado (opcional — requer execução do usuário)

A Irene não tem comando `bench` isolado (roda via Orquestrador). Para confirmar uma
calibração de F3/F4 com modelo real, re-executar apenas a fase Irene sobre um recorte:

```powershell
# A ENTREGAR AO USUÁRIO — re-run isolado da catalogação (consome tokens; gpt-5.5-thinking)
cd C:\Users\marquesf\Projetos\projeto_diogenes\diogenes
$env:DIOGENES_DEV_MODE="true"; $env:IRENE_C4_SAMPLE_N="5"   # limita C4 a 5 abas p/ baratear
diogenes bench pipeline MOD_010 --delivery C:\Users\marquesf\Projetos\projeto_diogenes\workspace\_teste_inputs\MOD_010_Pessoa_Fisica --limit 5
```
> Inspecionar o `irene_catalog.yaml` resultante: as abas de baixa confiança passaram a
> `requer_revisao_humana: true`? `resultado_final` fraco rebaixou a recomendação?

---

## Decisão pendente do usuário
1. Quais achados calibrar agora (F1–F4) antes de avançar a Watson?
2. Rodar o teste de confirmação isolado, ou aceitar a auditoria por artefatos como suficiente para Irene?
