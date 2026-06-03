# Walkthrough — Auditoria Sequencial dos Agentes do Diógenes

Log cronológico da validação agente por agente. Cada etapa só é encerrada com **chancela
explícita do usuário**. Ordem: Irene → Watson → Sherlock → Mycroft (4 fases).

Protocolo de execução: análise read-only e calibração de prompts são feitas diretamente;
qualquer comando que **rode os agentes** (LLM) é entregue ao usuário, que executa no
terminal e traz o resultado (controle de consumo de tokens).

Baseline de comportamento: ciclo `MOD_010_A1_20260602T202655Z` (concluído, gpt-5.5-thinking).

---

## Etapa 1 — Irene Adler (Catalogadora Semântica)
Key model: `gpt-5.5-thinking` (ChatTCU)

**Status:** ✅ Chancelado pelo usuário (2026-06-03)

- **A. Mapeamento de Contrato:** ✅ concluído — ver `irene/contrato.md`
- **B. Teste de Comportamento:** ✅ auditado a partir dos artefatos do run baseline
  (`irene_catalog.yaml`, score 0.9529 → APROVADO), sem custo de token.
- **C. Consolidação:** ✅ 5 achados levantados (F1–F5). F1 (modelo) e F2 (diretórios) anotados na documentação; F3 e F4 serão mantidos como ressalvas operacionais sem necessidade de alteração de código da biblioteca externa neste momento.

### Chancela do usuário
> Chancelado pelo usuário em 2026-06-03. As ressalvas da Irene Adler foram mapeadas e registradas. Liberado o avanço para a Etapa 2 (Watson).

---

## Etapa 2 — Dr. John Watson (Integridade Técnica)
Key model: `gpt-5.5-thinking` (ChatTCU)

**Status:** ✅ Chancelado pelo usuário (2026-06-03)

- **A. Mapeamento de Contrato (sem LLM):** ✅ concluído — ver [contrato.md](file:///c:/Users/marquesf/Projetos/projeto_diogenes/diogenes/docs/auditoria_agentes/watson/contrato.md)
- **B. Teste de Comportamento:** ✅ concluído — validado com sucesso para o `.csv` (triagem gerada) e o `.docx` (UnicodeDecodeError corrigido no CLI, arquivo analisado sem acionar o safety filter).
- **C. Consolidação:** ✅ concluído — dossiê finalizado em [dossie.md](file:///c:/Users/marquesf/Projetos/projeto_diogenes/diogenes/docs/auditoria_agentes/watson/dossie.md). As calibrações aplicadas no `soul.md`, `skills.md` e `heartbeat.md` foram testadas com sucesso via `bench pipeline --limit 3`, comprovando contadores estritamente numéricos e inteiros no cabeçalho.

### Chancela do usuário
> Chancelado pelo usuário em 2026-06-03. As calibrações de contadores inteiros e as mitigações contra o filtro de segurança (ChatTCU) foram atestadas como eficazes e o CLI foi corrigido para leitura de binários. Liberado o avanço para a Etapa 3 (Sherlock).

---

---

## Etapa 3 — Sherlock Holmes (Validação Metodológica)
**Status:** ✅ Chancelado pelo usuário (2026-06-03)

- **A. Mapeamento de Contrato:** ✅ concluído — ver `sherlock/contrato.md`
- **B. Teste de Comportamento:** ✅ concluído — validado com sucesso via `bench call` com fixture combinada sanitizada.
- **C. Consolidação:** ✅ concluído — dossiê finalizado em [dossie.md](file:///c:/Users/marquesf/Projetos/projeto_diogenes/diogenes/docs/auditoria_agentes/sherlock/dossie.md). As calibrações aplicadas no `heartbeat.py`, `heartbeat.md` e `soul.md` resolveram a falha estrutural e as ocorrências do safety filter. A ferramenta de teste `bench call` foi melhorada para salvar respostas completas em arquivo.

### Chancela do usuário
> Chancelado pelo usuário em 2026-06-03. As calibrações monolíticas de Sherlock resolveram a causa raiz dos "zero pontos válidos" (NV-GLOBAL-01) e a sanitização contornou o filtro do ChatTCU. Liberado o avanço para a Etapa 4 (Mycroft).

---

## Etapa 4 — Mycroft Holmes (Orquestrador — 4 fases)
**Status:** ✅ Chancelado pelo usuário (2026-06-03)

- **A. Mapeamento de Contrato:** ✅ concluído — ver `mycroft/contrato.md` (7 call_types mapeados, Artigos 3/5/8/9/10/14 verificados)
- **B. Teste de Comportamento:** ✅ auditado a partir dos artefatos do ciclo baseline (passive audit — nenhuma calibração ativa necessária)
- **C. Consolidação:** ✅ concluído — dossiê finalizado em `mycroft/dossie.md`

### Fases validadas

- **Fase 4.1 — Tasking & Decisão Watson:** Mycroft injetou premissas globais corretamente, incorporou catálogo Irene e detectou Planilha de Verificação. Avaliação de Watson aprovada com Art. 5 confirmado (sem abertura de arquivos brutos). ✓
- **Fase 4.2 — Auto-Lestrade & Alerta Crítico:** 254 alertas CRITICA → estado `AGUARDANDO_DECISAO_LESTRADE_ALERTA` → auto-Lestrade executou proceed automático. Art. 9 confirmado. ✓
- **Fase 4.3 — Stranger Room & Crítica Metodológica:** Crítica localizada em NV-GLOBAL-01 (classificação JSON vs. corpo). Sherlock R1 sustentou com fundamentação técnica. Mycroft acatou (APROVADO, overruled: false). Art. 8 (martelo) confirmado. ✓
- **Fase 4.4 — Consolidação Final:** Completude das 11 seções verificada antes de emitir consolidado. Art. 14 (impessoalidade) confirmado. ✓

### Achados — sem calibração necessária

- **F-Mycroft-01** (documentação): `agent.md` dizia `claude-sonnet-4-6`; produção usa `gpt-5.5-thinking`. **Corrigido** no `agent.md` (mesmo padrão de Irene F1).
- **F-Mycroft-02** (comportamento esperado): `mapear_pontos` não foi chamado no ciclo baseline. Correto — esse call_type só seria usado no modo ponto-a-ponto (`verificar_ponto`). No modo monolítico (`validacao_inicial`, corrigido na Etapa 3) o heartbeat não usa `MC_mapa_pontos.md`. Não é gap, é coerência arquitetural.

### Chancela do usuário
> Chancelado pelo usuário em 2026-06-03. Mycroft Holmes validado por passive audit do ciclo baseline MOD_010_A1_20260602T202655Z — todas as 4 fases em conformidade com os Artigos constitucionais. F-Mycroft-01 corrigido. F-Mycroft-02 aceito como comportamento esperado. Auditoria sistemática dos 4 agentes concluída.

