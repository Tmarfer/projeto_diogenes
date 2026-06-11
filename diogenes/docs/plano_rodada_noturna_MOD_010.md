---
documento: Plano de Execução — Rodada Noturna Completa MOD_010 (Atividade 1)
projeto: DVA-CBS | Projeto Diógenes
processo: TC 015.848/2025-6
versao: 1.0
data: 2026-06-10
uso: Interno Restrito
pre-requisito: calibrações pós-MOD_SINT_SQL v2 aplicadas (massa v3 + Passos 5c/5d Sherlock + metadados Watson)
---

# Plano — Rodada Noturna Completa MOD_010 (toda a massa)

## Objetivo

Primeira validação real ponta-a-ponta com **toda a massa do MOD_010 Pessoa Física**
(~130 arquivos: `01_ENTRADA_COPIADA` bruto + `04_TRANSFORMADO` + regra de negócio +
notas da reunião de entrega), com as calibrações da homologação por formato aplicadas:
Watson sem inflação de críticos por metadado, Sherlock com gradação de severidade
(Passos 5c/5d), pré-atendimento gerado com a ata real da reunião (`NOTION.md`).

## Pré-voo (checklist — executar antes de dormir)

| # | Verificação | Comando / ação |
|---|------------|----------------|
| 1 | Suíte verde | `pytest tests/ -q` (de dentro de `diogenes/`) |
| 2 | Conectividade ChatTCU | `diogenes bench smoke` |
| 3 | Modelos válidos | `diogenes bench validate-models` |
| 4 | **PIM re-elevado AGORA** | janela ~8h — elevar imediatamente antes do disparo |
| 5 | Token MSAL aquecido | o `bench smoke` já renova o cache silenciosamente |
| 6 | Corpus jurídico | `.env` → `DIOGENES_CORPUS_JURIDICO_DIR` aponta ao `ARCABOCO_JURIDICO` (recorte `por_modulo/MOD_010.md` + `CONST_010.md` + transversais) |
| 7 | Cooldown pós-Irene | `.env` → `DIOGENES_POST_IRENE_COOLDOWN_S=600` *(já configurado)* |
| 8 | DEV_MODE desligado | `.env` → `DIOGENES_DEV_MODE` ausente/false (senão o seal é bloqueado e timeouts encurtam) |
| 9 | Playwright | `python -m playwright install chromium` (ficha síntese PDF/PNG) |
| 10 | Disco/energia | MacBook na tomada; ≥2 GB livres no workspace |

## Disparo (1 comando)

```bash
cd /Users/tmarfer_mac/Documents/Projetos/projeto_diogenes/diogenes

caffeinate -i diogenes autorun --module MOD_010 --activity 1 \
  --delivery /Users/tmarfer_mac/Documents/Projetos/projeto_diogenes/workspace/_teste_inputs/MOD_010_Pessoa_Fisica \
  --auto-seal \
  2>&1 | tee ~/diogenes_overnight_MOD010_$(date +%Y%m%dT%H%M).log
```

- `caffeinate -i` impede o sleep do macOS durante a execução.
- `--delivery` aponta para o pacote full (o default `workspace/input/MOD_010` não existe).
- `--auto-seal` chancela e dispara a Fase de Entrega automaticamente **somente se** o
  Motor de Saída confirmar documento LIMPO; com marcas internas, o ciclo para em
  `AGUARDANDO_CHANCELA_LESTRADE` e a manhã começa pela revisão manual.
- O painel `report.html` abre sozinho e se auto-atualiza durante toda a execução.

## Expectativa de duração e custo

| Fase | Estimativa |
|------|-----------|
| Motor de Start (SHA-256 de ~130 arquivos) | minutos |
| Irene C1–C5 (catalogação dos XLSX/CSV) | 1–2 h (≈66 calls) + cooldown 10 min |
| Watson (análise por arquivo + consolidação) | 6–12 h (maior bloco) |
| Sherlock (pontos + planilha RN + consolidação) | 2–4 h |
| Mycroft (avaliações + consolidação + entrega) | 1–2 h |
| **Total** | **10–20 h** |

Custo de referência (gpt-5.5-thinking via ChatTCU): USD ~15–40 de referência —
**custo real zero** (infra institucional, `teto_custo_ciclo_usd: 0.00`).

## Riscos e postura

| Risco | Probabilidade | Mitigação / postura |
|-------|--------------|---------------------|
| **Expiração PIM (~8h) antes do fim** | ALTA | Elevar PIM imediatamente antes do disparo. Se expirar: o MSAL tenta renovação silenciosa a cada tentativa; se falhar, o ciclo aborta — **não re-rodar `resume`**; re-rodar `autorun` cria ciclo novo (checkpoint Watson é por ciclo). Registrar o ponto de morte pelo log. |
| Read timeout ChatTCU (observado 1×/ciclo SQL) | MÉDIA | Já mitigado: timeout 1500s + 4 tentativas + renovação de token por tentativa + retry de 2xx vazio. Pior caso por chamada ≈ 100 min — aceitável overnight. |
| Saturação pós-Irene | MÉDIA | `DIOGENES_POST_IRENE_COOLDOWN_S=600` já configurado. |
| Documento com marcas internas (Motor de Saída) | BAIXA | Regex da Onda 4 zerou as 142 marcas no MOD_SINT_001; se ocorrer, `--auto-seal` é ignorado e a chancela fica manual. |
| Ata errada no pré-atendimento | RESOLVIDO | `_ler_ata` agora casa por token de caminho: acha `NOTION.md` em `2026_04_27-entrega_MOD_010/` e ignora `CATALOGO.md`. |

## Critérios de avaliação na manhã seguinte

1. **Estado final:** `ENCERRADO_CHANCELADO` (ou `AGUARDANDO_CHANCELA_LESTRADE` com doc limpo).
2. **Cobertura Watson:** 100% dos arquivos analisáveis com análise individual (conferir
   `Arquivos não analisados` = 0 no consolidado; retry de 2xx vazio elimina perdas silenciosas).
3. **Perfil de severidade Watson:** alertas CRITICA concentrados em achados materiais —
   ausência de metadado não pode dominar a lista (calibração `verificacao_metadados`).
4. **Sherlock:** ocorrências individualizadas (não agregadas em 1 NV global); toda
   DIVERGENCIA/CRITICO com fundamento canônico (`LC 214/2025, Art. X`) e número de Watson
   (Passo 5b); nenhuma sistêmica agregada como CRITICO (Passo 5d).
5. **Entrega (9 artefatos):** Dashboard, Apêndice, Narrativo, Consolidado,
   **Pré-Atendimento com Bloco 1 = ata NOTION.md**, ficha HTML/PDF/2×PNG — nomes `Modulo10`.
6. **QA Mycroft:** `avaliar_entrega` = APROVADO (ou REQUER_AJUSTE com motivo acionável).
7. **Custo/telemetria:** somatório das chamadas no `report.html`; comparar com estimativa.

## Pós-rodada

- `diogenes report --cycle <id> --format html` para análise fria.
- Registrar resultado em `ESTADO_DIOGENES.md` + atualizar a matriz de conformidade
  (`docs/conformidade/11_aceitacao_metricas.md`) com MET-01..03 (operacionais) do ciclo real.
- Se aprovado: seguir a fila de homologação de formatos (SQL v3 → IPYNB → MD → PDF → DOCX → TXT)
  e preparar Atividade 2 (revalidação) sobre este ciclo.

---
*DVA-CBS | Projeto Diógenes | TC 015.848/2025-6 | Uso Interno Restrito*
