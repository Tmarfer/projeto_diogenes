# Dossiê de Validação — Dr. John Watson

**Veredito preliminar:** 🟡 Em calibração (divergências identificadas em cabeçalho consolidado e recusas de segurança do modelo que requerem ajustes de prompt).

Base: contrato em [contrato.md](file:///c:/Users/marquesf/Projetos/projeto_diogenes/diogenes/docs/auditoria_agentes/watson/contrato.md) + comportamento real do ciclo `MOD_010_A1_20260602T202655Z` (auditado a partir de `watson_consolidado.md`, `watson_registro_decisao.md` e logs do ciclo).

---

## O que está aderente (confirmado)

- **Artigo 6 (Integridade Técnica Estrita):** Watson não utilizou terminologias metodológicas como "Atendido", "Divergência" ou "Conforme metodologia" em seus relatórios e registros de decisão. Toda a análise concentrou-se na Camada 0 (metadados, integridade aritmética, consistência interna e premissas não justificadas). ✓
- **Artigo 4 (Mandato de Invocação):** Watson agiu exclusivamente sob delegação do orquestrador via `MC_tasks_watson.md`. ✓
- **Artigo 13 (Isolamento de Diretório):** Watson operou exclusivamente sobre as cópias locais dos arquivos gerados no diretório do ciclo. ✓
- **Artigo 14 (Impessoalidade):** Os relatórios principais (`01_apresentacao.md` / `watson_consolidado.md`) foram redigidos em terceira pessoa de forma estritamente impessoal, com assinatura padrão ao final. ✓
- **Exceção do Trace (Primeira Pessoa):** Os traces de raciocínio de Watson (`watson_trace_*.md`) usaram narrativa em primeira pessoa de forma adequada, limitando-se ao uso interno de Mycroft. ✓
- **Registro de Decisão:** Watson produziu com sucesso o `watson_registro_decisao.md` detalhando as 12 decisões de julgamento e bifurcações do ciclo. ✓

---

## Achados

### F1 — Contagem de Alertas CRÍTICA em Prosa no Cabeçalho Consolidado *(falha de formato)*

- **Projetado:** O `skills.md` define que o template do consolidado de Watson deve conter `**Alertas CRITICA:** [n]` e `**Total de alertas:** [n]`, onde `[n]` representa um valor inteiro.
- **Real:** Watson respondeu a esse campo em prosa:
  > `**Alertas CRITICA:** múltiplos, distribuídos em todo o ciclo; maior concentração em metadados ausentes, truncamentos, parâmetros não rastreáveis e notas/ajustes documentais`
- **Risco:** O extrator regex do Orquestrador/Mycroft não conseguiu ler um número inteiro do cabeçalho, resultando em `critical_alerts_count: null` (ou não quantificado) no frontmatter da Stranger Room, necessitando de fallbacks ou tolerâncias adicionais no código do orquestrador para calcular o total.
- **Ação proposta:** Calibrar o `skills.md` e o `heartbeat.md` (seção `consolidar_watson`) para reforçar que os contadores no cabeçalho (Alertas CRITICA, Alertas ALTA, Total) **devem conter exclusivamente um número inteiro** (ex: `254` ou `0`), sem prosa e sem explicações adicionais.

### F2 — Recusas de Segurança (Safety Filter) no ChatTCU *(bloqueio de modelo)*

- **Projetado:** Watson deve processar todos os arquivos elegíveis. Caso um arquivo não seja analisável por erro estrutural ou indisponibilidade, registra a ocorrência no consolidado e prossegue, garantindo completude.
- **Real:** Quatro arquivos do ciclo baseline falharam no processamento com a mensagem padrão de recusa do ChatTCU: `"I'm sorry, but I cannot assist with that request."`. Os arquivos foram:
  1. `NOTA METODOLÓGICA CBS  V_11_25b - atualização.docx` (bloqueado no meio da geração, cortado após o cabeçalho)
  2. `prod_cnae_cf.csv`
  3. `base_nfe.csv`
  4. `base_nfe_geral.csv`
- **Causa:** O ChatTCU possui um middleware com filtros de segurança (segurança da informação, PII, e dados fiscais/eSocial sensíveis) que intercepta a requisição. Se o prompt do usuário contém grandes blocos de CPFs/CNPJs reais, ou se a resposta do modelo tenta copiar ou citar trechos literais brutos que ativam heurísticas do filtro, a geração é abortada e substituída pela mensagem padrão.
- **Risco:** Redução da cobertura técnica e auditoria incompleta de arquivos críticos do módulo.
- **Ação proposta:** Calibrar o `soul.md` e `skills.md` de Watson para:
  1. Proibir terminantemente a inclusão de CPFs, CNPJs ou chaves de acesso NFe de forma literal/completa em seus relatórios e traces. Watson deve mascarar dados sensíveis (ex: `***.***.***-**`) ou referenciar células e linhas de forma genérica (ex: `linha 42`).
  2. Orientar o agente a não transcrever grandes blocos textuais literalizados de documentos, priorizando descrições sumarizadas e estatísticas estruturais.
  3. Adicionar diretrizes de postura institucional para mitigar falsos positivos nos filtros de segurança do TCU.

---

## Teste de confirmação isolado (requer execução do usuário)

Para validar a calibração dos prompts e verificar se a recusa de segurança foi mitigada, o usuário deve rodar a chamada isolada de Watson para um dos arquivos que foram recusados na execução baseline.

```powershell
# Executar no terminal do VS Code a chamada isolada de Watson para o arquivo prod_cnae_cf.csv:
C:\Users\marquesf\AppData\Local\Python\pythoncore-3.14-64\Scripts\diogenes.exe bench call watson --call-type analise_arquivo --fixture C:\Users\marquesf\Projetos\projeto_diogenes\workspace\cycles\MOD_010_A1_20260602T202655Z\inputs\2026_04_27\04_TRANSFORMADO\demais_pessoas_fisicas\consumo_final_contas_nacionais\prod_cnae_cf.csv
```

> **Verificação:** A resposta de Watson deve ser gerada sem a mensagem "I'm sorry..." e conter a estrutura de cabeçalho correta com contagem numérica de alertas.

---

## Decisão pendente do usuário

1. Aprova os achados e a proposta de calibração dos prompts de Watson?
2. Deseja realizar a calibração dos prompts agora e partir para os testes assistidos?
