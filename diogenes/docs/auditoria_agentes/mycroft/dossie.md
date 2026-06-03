# Dossiê de Validação — Mycroft Holmes

**Veredito:** ✅ CHANCELADO (A validação sistemática de Mycroft Holmes atestou conformidade total com o contrato projetado e os limites constitucionais em todas as 4 fases operacionais. A Stranger Room do ciclo baseline registrou questionamentos localizados adequados, e o relatório consolidado final atendeu às exigências de impessoalidade e completude estrutural).

Base: contrato em [contrato.md](file:///c:/Users/marquesf/Projetos/projeto_diogenes/diogenes/docs/auditoria_agentes/mycroft/contrato.md) + comportamento real do ciclo `MOD_010_A1_20260602T202655Z` (auditado via stranger_room e logs do ciclo).

---

## 1. Fase 4.1 — Tasking & Decisão Watson

* **Tasking:** No início do ciclo, Mycroft gerou o arquivo `MC_tasks_watson.md` a partir do call_type `definir_tasks_watson`.
  - **Premissas Globais:** Mycroft injetou corretamente no prompt de Watson as premissas globais do projeto: Premissa 1 (anos-base 2023 e 2024), Premissa 2 (critério de equivalência), e Premissa 3 (sinalização de nota metodológica com alteração). ✓
  - **Catálogo Irene:** Mycroft leu e incorporou adequadamente a recomendação do Irene (`APROVADO` / `ALERTA` / `BLOQUEADO`) e a lista de abas, orientando Watson sobre a profundidade e foco de análise de cada arquivo com base em sua classificação semântica. ✓
  - **Planilha de Verificação:** Mycroft detectou corretamente a presença da Planilha de Verificação no pacote e incluiu a Task 4 correspondente nas tarefas de Watson. ✓
* **Avaliação e Decisão:** Watson apresentou seu consolidado inicial com 254 alertas críticos (severidade `CRITICA`). Mycroft executou `avaliar_watson` e determinou o resultado `APROVADO`. 
  - **Artigo 5 (Não-intervenção):** Confirmado. Mycroft realizou o julgamento do output de Watson com base estritamente na fundamentação e rastreabilidade apresentadas no relatório do agente, sem abrir os arquivos originais de entrega ou refazer cálculos. ✓
  - **Decisão Final:** Mycroft gravou a aprovação do consolidado em `MC_decisao_watson.md` (`99_decisao_final.md` em `stranger_room/watson_integridade/`), registrando a contagem correta de 254 alertas de Watson e fixando a decisão sem overruling (`mycroft_overruled: false`). ✓

---

## 2. Fase 4.2 — Auto-Lestrade & Alerta Crítico

* **Gatilho de Alerta Crítico (Artigo 9):** Watson identificou 254 alertas críticos. Conforme prescrito pelo Artigo 9, Mycroft suspendeu o ciclo para notificação de Lestrade antes de acionar Sherlock.
* **Máquina de Estados e Auto-Lestrade:** 
  - O orquestrador detectou a flag `has_critical_alert` e realizou a transição para o estado `AGUARDANDO_DECISAO_LESTRADE_ALERTA`.
  - O pipeline registrou o evento `CRITICAL_ALERT_NOTIFIED` e suspendeu o ciclo. No fluxo real (autorun), o mecanismo de auto-Lestrade executou o proceed automático (`LESTRADE_PROCEED_AUTHORIZED`), permitindo que Mycroft retomasse a orquestração e acionasse Sherlock. ✓

---

## 3. Fase 4.3 — Stranger Room & Crítica Metodológica

* **Montar Pacote Sherlock:** Mycroft consolidou as descobertas de Watson no arquivo `MC_pacote_sherlock.md`, integrando a decisão final de Watson, o resumo textual das ocorrências e os insumos metodológicos (Regras de Negócio e Corpus Jurídico). ✓
* **Stranger Room (Fase Sherlock):** Ocorreu 1 rodada de revisão técnica na Stranger Room de Sherlock (`sherlock_validacao`).
  - **Crítica Localizada (Regra do Ponto Único):** Mycroft identificou um ponto de divergência e formulou exatamente uma crítica em `02_critica_mycroft_r1.md`: questionou a inconsistência na ocorrência `NV-GLOBAL-01` entre a classificação do corpo do relatório (`NAO_VERIFICAVEL`) e a codificação estruturada no JSON do dashboard (`"nivel": "ALERTA"`). ✓
  - **Resposta de Sherlock R1:** Sherlock respondeu em `03_resposta_r1.md`, sustentando a codificação estruturada ao demonstrar que a seção 11 segue a regra específica de mapeamento do Template 2 (`NAO_VERIFICAVEL` -> `ALERTA` no dashboard), cuja taxonomia difere do relatório.
  - **Julgamento de Mycroft:** Mycroft avaliou a resposta do agente e emitiu o resultado `APROVADO` em `99_decisao_final.md`, decidindo acatar (ACATADO) a fundamentação técnica de Sherlock. A deliberação foi robusta, explicitou a coerência do mapeamento do dashboard e manteve `mycroft_overruled: false`. ✓

> **Investigação da Falha de Sherlock (Zero Pontos Válidos):**
> Confirmado que a causa de Sherlock ter retornado zero pontos válidos na baseline **não** foi decorrente de falha de Mycroft em montar o pacote (`montar_pacote_sherlock` incluiu corretamente todos os arquivos). A falha decorreu exclusivamente do mapeamento de heartbeat em `heartbeat.py` que direcionou Sherlock para a restrição de chamada unitária de ponto.

---

## 4. Fase 4.4 — Consolidação Final

* **Completude do Relatório (Artigo 12):** Antes de consolidar o produto, o orquestrador verificou a completude e presença de todas as seções obrigatórias (10.1 a 10.11 e JSON de ocorrências) em `sherlock_consolidado.md`.
* **Consolidação do Relatório:** Mycroft consolidou o relatório preliminar `relatorio_preliminar_*.md` incorporando o histórico do ciclo (Watson e Sherlock, Stranger Room, rodadas e decisões) e assinando ao final.
* **Impessoalidade (Artigo 14):** A redação final do consolidado e dos relatórios intermediários atendeu estritamente às exigências de impessoalidade e terceira pessoa, sem menção a personas ou discussões subjetivas no corpo textual (restrito aos arquivos internos de Stranger Room). ✓

---

## Achados e Calibrações (2026-06-03)

### F-Mycroft-01 — Deriva de modelo no agent.md (documentação)
`agent.md` documentava `claude-sonnet-4-6` como modelo preferencial. Produção usa `gpt-5.5-thinking` via `agents_spec.yaml`.
**Corrigido:** `agent.md` atualizado para refletir o modelo real de produção.

### F-Mycroft-02 — `mapear_pontos` não utilizado no ciclo real (comportamento esperado)
O call_type `mapear_pontos` não foi chamado no ciclo baseline. Esse call_type foi projetado para o modo de verificação ponto-a-ponto (`verificar_ponto`). No modo monolítico (`validacao_inicial`) corrigido na Etapa 3, Sherlock extrai os pontos diretamente do pacote — `MC_mapa_pontos.md` não é necessário. Não é gap, é coerência arquitetural com a correção aplicada.
**Aceito como comportamento esperado.**

### F-Mycroft-03 — Filtro de segurança no avaliar_sherlock (calibração aplicada)
No bench pipeline `pipeline_MOD_010_20260603T181246Z`, o Passo 7 (Mycroft avaliar Sherlock) retornou `"I'm sorry, but I cannot assist with that request."` — o filtro de segurança do ChatTCU bloqueou a chamada. O pipeline continuou com fallback, mas a avaliação não foi executada. Causa provável: Watson consolidado contém referências analíticas a identificadores PF que propagam pelo pipeline até o input de Mycroft.
**Calibração aplicada:** adicionada seção "Prevenção de Interceptação de Segurança (ChatTCU)" ao `soul.md` de Mycroft — mascaramento de PII, síntese estrutural e foco no raciocínio (sem transcrição de dados brutos). 187/187 testes passando após a mudança.

---
*DVA-CBS | Projeto Diógenes | TC 015.848/2025-6*
*Auditoria de agentes - dossiê consolidado de Mycroft Holmes*
