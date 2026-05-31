---
author: sherlock
content_hash: sha256:2946055ece2a7221
critical_alerts_count: null
cycle_id: MOD_010_A1_20260531T041556Z
dilemmas_count: null
file_type: apresentacao
has_critical_alert: null
has_dilemma: null
mycroft_overruled: null
phase: sherlock_validacao
role: Auditor de Validação Metodológica CBS
round: null
timestamp_utc: '2026-05-31T13:02:34Z'
---

```markdown
<!-- SECAO: cabecalho_ponto -->
# Verificação de Ponto Metodológico — Sherlock
**Módulo:** Não informado no material recebido
**Número do ponto:** Não informado no material recebido
**Título do ponto:** Não informado no material recebido
**Dispositivo metodológico:** Não informado no material recebido
**Camada:** Não identificável com os documentos fornecidos
**Timestamp:** 2026-05-31T10:01:00-03:00
**Call Type:** verificar_ponto
**Classificação:** NAO_VERIFICAVEL
**Impacto potencial:** Alto
**Trace produzido:** Não
**Razão do trace:** Não aplicável
**Bifurcação de julgamento:** Não
**Nota metodológica com alteração verificada neste ponto:** Não verificável
<!-- /SECAO: cabecalho_ponto -->

<!-- SECAO: verificacao_premissas_globais -->
## Verificação de Premissas Globais

**Premissa 1 — Alteração dos anos-base (2023 e 2024):**  
Os documentos metodológicos recebidos fazem referência genérica a `an_exercicio = <ano>`, sem indicação do ponto metodológico específico nem do ano efetivamente aplicado nos artefatos analisados. Assim, não foi possível verificar se este ponto opera com os anos-base ajustados de 2023 e 2024 ou se ainda referencia 2024 e 2025. [Premissa Global | Alteração dos anos-base]

**Premissa 2 — Critério de equivalência:**  
A verificação deste ponto deveria confrontar mesmas premissas e mesmos caminhos com os resultados documentados; contudo, sem o `MC_mapa_pontos.md`, sem o trecho do Apêndice aplicável e sem os `watson_analise_*.md` pertinentes, não há base documental suficiente para executar o teste de equivalência exigido. [Premissa Global | Critério de equivalência]

**Premissa 3 — Nota metodológica com alteração:****  
Não foi fornecido o `MC_mapa_pontos.md` nem o trecho do `watson_consolidado.md` que indicaria eventual nota metodológica com alteração relevante para este ponto. Portanto, não foi possível confirmar se há ou não nota sinalizada. [Premissa Global | Notas metodológicas como elemento de verificação prioritária]
<!-- /SECAO: verificacao_premissas_globais -->

<!-- SECAO: verificacao -->
## Verificação

**O que a metodologia prescreve:**  
Com os documentos recebidos, foi possível identificar apenas descrições metodológicas genéricas de duas frentes de trabalho:  
1. estimativa do valor de créditos com base em comparação entre Carnê-Leão e Livro Caixa declarado na DIRPF, análise de lançamentos, cálculo de percentual e aplicação desse percentual ao valor declarado; e  
2. apuração de rendimentos de trabalho não assalariado na DIRPF, com menção a correção de ocupações não determinadas e totais por categoria.  
Também foram descritas, em nível geral, tabelas de rendimentos recebidos de pessoa física, declarações de IRPF, demonstrativos do Carnê-Leão e lançamentos de pagamentos do Carnê-Leão.  

Entretanto, não foi fornecido o trecho do Apêndice metodológico correspondente ao ponto desta chamada. Sem esse trecho, não é possível identificar qual prescrição específica deve ser usada como régua de validação do ponto.  

**O que os documentos registram:**  
Não foram fornecidos os `watson_analise_*.md` relevantes para este ponto. Assim, não há registro, nesta chamada, do que efetivamente foi executado pela RFB nem do que Watson encontrou quanto a fonte de dado, filtros, escopo, granularidade ou reprodutibilidade documental.

**Fundamentação da classificação:**  
O ponto foi classificado como `NAO_VERIFICAVEL` porque os insumos indispensáveis para a Fase 1 não integraram o material recebido nesta chamada:  
- ausência do `MC_mapa_pontos.md`, que identificaria número do ponto, título, camada, arquivos relevantes e eventual sinalização de nota metodológica;  
- ausência do trecho do Apêndice metodológico correspondente, que definiria o dispositivo a ser confrontado;  
- ausência dos `watson_analise_*.md`, que constituem a base exclusiva desta fase para descrever o que foi feito nos artefatos.  

Nessas condições, não é possível confrontar prescrição e execução, nem verificar aderência metodológica ou reprodutibilidade documental, sem especulação. A insuficiência é interna ao conjunto documental da chamada, razão pela qual a classificação adequada é `NAO_VERIFICAVEL`, e não `LIMITACAO`. [Premissa Global | Critério de equivalência]

**Impacto sobre o resultado do módulo:**  
O impacto potencial é alto, porque a ausência dos insumos estruturantes impede a emissão de classificação metodológica válida para o ponto e, por consequência, compromete a consolidação posterior deste item no quadro do módulo.
<!-- /SECAO: verificacao -->

<!-- SECAO: encaminhamento -->
## Encaminhamento

**O que a RFB deve demonstrar ou corrigir:**  
Para tornar o ponto verificável no contraditório técnico ou em nova rodada interna, devem ser apresentados, no mínimo:  
1. o `MC_mapa_pontos.md` com a identificação do ponto desta chamada;  
2. o trecho do Apêndice metodológico correspondente ao dispositivo aplicável;  
3. os `watson_analise_*.md` mapeados como relevantes para o ponto;  
4. se existente, a indicação de nota metodológica com alteração sinalizada por Watson;  
5. a indicação do ano-base efetivamente utilizado no ponto, para aferição da premissa global de 2023 e 2024.  
<!-- /SECAO: encaminhamento -->

<!-- SECAO: assinatura_sherlock_ponto -->
---
*Verificação produzida por: Sherlock Holmes — Auditor de Validação Metodológica CBS*  
*DVA-CBS | Projeto Diógenes | TC 015.848/2025-6*  
*Uso interno restrito*  
<!-- /SECAO: assinatura_sherlock_ponto -->
```

Observação final: com o material efetivamente enviado nesta chamada, **não foi possível produzir um `sherlock_ponto_*.md` plenamente válido nos termos do template**, porque o dispositivo metodológico específico do ponto não foi fornecido. O registro acima documenta a insuficiência documental sem suprir lacunas por inferência.
