# STATUS — Projeto Diógenes

> Estado atual do projeto. Atualizado em 2026-05-14.
> DVA-CBS | TC 015.848/2025-6 | Uso interno restrito.

---

## Ambiente e Infra

- O projeto roda em uma **worktree local** (`C:\Projetos\Projeto_Diogenes\...`) — **não** usa mais o OneDrive (a cópia OneDrive é legado, não é fonte da verdade).
- A worktree **não** herda `.env` nem `workspace/` (são gitignored). Para preparar o ambiente:
  1. Copiar o `.env` do repo local principal (`C:\Projetos\Projeto_Diogenes\diogenes\.env`) para a worktree.
  2. Ajustar `DIOGENES_WORKSPACE` no `.env` copiado para um workspace **isolado** dentro da worktree.
  3. Rodar `pip install -e .` **de dentro da worktree** — o editable install precisa apontar para a `src/` da worktree, senão o `pytest` testa o código errado.
  4. `diogenes init` cria a estrutura do workspace; restaurar inputs sintéticos de `piloto/workspace_sample/` para `{workspace}/input/MOD_SINT_001/`.
- Console Windows: o `display.py` já força UTF-8; não é mais necessário o hack `PYTHONIOENCODING=utf-8`.

## Arquitetura (LLMs)

- A **Fase A roda exclusivamente com a configuração de modelos pagos** (rotulada `fase_ativa: B` no `agents_spec.yaml`): `meta-llama/llama-4-maverick` (Mycroft), `google/gemini-2.5-flash-lite` (Watson), `deepseek/deepseek-v4-flash` (Sherlock). Teto de custo: USD 5/ciclo.
- **Modelos free foram abolidos** — causavam rate limit recorrente no OpenRouter (6 ciclos `ABORTADO_FALHA_AGENTE`). Não reintroduzir fallback para modelos free.
- `max_tokens` ajustado com base em outputs legítimos observados: Mycroft/Watson `16384`, Sherlock `24576`.

## Correções Implementadas (Core)

- **Orquestrador — fail-fast na máquina de estados.** `_transicionar` agora levanta `CorruptedStateError` quando o status no `audit_index.csv` não corresponde a nenhum `CycleState` conhecido, em vez de mascarar a corrupção. Também: `_avancar_id_alerta` deriva os IDs de alerta dos IDs realmente parseados (não da contagem bruta do LLM), garantindo IDs contíguos; `resume.py` não fura mais a máquina de estados.
- **Watson — novo parser de alertas críticos.** `_contar_criticos` lê a contagem diretamente do campo de cabeçalho `**Alertas CRITICA:** N` (sobrevive à truncagem da tabela), com fallback para os nomes de seção reais dos templates do `skills.md`. Corrige o descasamento que fazia `critical_alerts_count` sempre retornar 0.
- **Truncagem — guardrail no `openrouter.py`.** `rstrip()` em toda resposta elimina loops degenerados de whitespace (antes: 982 KB de lixo persistido); `finish_reason` capturado, persistido no trace e logado com aviso explícito `⚠ TRUNCAGEM` quando `== "length"`.
- **Mycroft — guardrail de procedência de arquivos.** Heartbeat de `consolidar` agora exige distinguir arquivos do manifesto de arquivos apenas citados dentro de artefatos.
- **`display.py`** — força UTF-8 em stdout/stderr (corrige `UnicodeEncodeError` em console cp1252 do Windows).
- Status de validação: **88 testes passando**, ruff limpo nos arquivos tocados. Dois ciclos sintéticos completos rodados end-to-end com sucesso.

## Ponto de Partida para a Próxima Sessão (Next Steps)

- **Passo 1 — Mitigar a degeneração de arquivos `.ipynb`.** O `notebook_transform.ipynb` faz o modelo pequeno (gemini-2.5-flash-lite) entrar em loop de whitespace e truncar a análise. Causa: notebooks Jupyter são JSONs pesados que confundem modelos menores. Ajustar o `file_prep` (ou o prompt de análise) para **limpar o JSON do notebook** antes da análise — extrair só células de código/markdown relevantes, descartar metadados/outputs ruidosos.
- **Passo 2 — Após a mitigação: chancelar (`seal`) e rodar com base real.** Fazer o `seal` de um ciclo sintético íntegro e então iniciar a execução com a **base de dados real (MOD_010)**.

### Pendências menores conhecidas

- `agents_spec.yaml` / `CLAUDE.md` ainda chamam a config paga de "Fase B" — a nomenclatura diverge do uso atual ("Fase A = modelos pagos"). Alinhar quando conveniente.
- ~40 erros de `mypy` pré-existentes no codebase (`dict` sem type args, etc.) — dívida técnica não bloqueante.
