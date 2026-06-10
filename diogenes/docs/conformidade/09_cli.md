# Conformidade — CLI (RF-CL)

> PRD Bloco 3.9 (linhas 358-382) vs. `src/diogenes/cli/commands/`
> Auditoria: 2026-06-09 | Baseline: 305 testes passando, 1 skipped (cobertura CLI em `test_cli_commands.py`)

| Req | Resumo | Status | Evidência | Gap | Prio | Onda |
|---|---|---|---|---|---|---|
| RF-CL-01 | Comando raiz `diogenes` com `--help` listando subcomandos | Conforme | `cli/app.py` (Typer); um arquivo por subcomando em `commands/` | — | — | — |
| RF-CL-02 | `start --module --activity` dispara Motor de Start | Conforme | `commands/start.py` | — | — | — |
| RF-CL-03 | `confirm-manifest --cycle` registra confirmação e dispara Orquestrador | Conforme | `commands/confirm_manifest.py` | — | — | — |
| RF-CL-04 | `proceed --cycle` autoriza prosseguimento pós-alerta | Conforme | `commands/proceed.py` → `retomar_apos_alerta` | — | — | — |
| RF-CL-05 | `pause --cycle` interrompe e marca status | Conforme | `commands/pause.py` | — | — | — |
| RF-CL-06 | `resume --cycle` retoma ciclo pausado na fase correta | Conforme | `commands/resume.py` | — | — | — |
| RF-CL-07 | `verify-output --cycle` dispara Motor de Saída | Conforme | `commands/verify_output.py` | — | — | — |
| RF-CL-08 | `seal --cycle` registra chancela; exige verificação prévia | Conforme | `commands/seal.py` exige `AGUARDANDO_CHANCELA_LESTRADE`; `audit_index.py:106` `seal_cycle` | — | — | — |
| RF-CL-09 | `abort --cycle --reason` em qualquer estado, preserva diretório | Conforme | `commands/abort.py` | — | — | — |
| RF-CL-10 | `status --cycle` exibe fase, último arquivo SR, próximo passo | Conforme | `commands/status.py` | — | — | — |
| RF-CL-11 | `list [--module] [--status]` com filtros | Conforme | `commands/list.py` | — | — | — |
| RF-CL-12 | `show --cycle [--phase]` formata Stranger's Room | Conforme | `commands/show.py` | — | — | — |
| RF-CL-13 | Informativos idempotentes; modificadores falham antes de escrever | Conforme | Validação de pré-condições antes de escrita em todos os modificadores | — | — | — |

**Síntese:** 13/13 Conforme.

**Subcomandos além do PRD (sem RF — ver `12_sdd_gaps.md`):** `init`, `autorun`, `complete-sherlock`, `report` (painel local), `deliver` (Fase de Entrega), grupo `bench` (bancada cirúrgica: smoke, validate-models, preview, call, pipeline). Todos auditáveis; propor RFs no PRD-adendo.
