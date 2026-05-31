# Descrição Metodológica — Módulo CBS 001
## Módulo Sintético de Validação Piloto | DVA-CBS

**Processo TCU:** TC 015.848/2025-6  
**Módulo:** MOD_SINT_001 — Apuração da Base de Cálculo da CBS sobre Serviços de Tecnologia da Informação  
**Entregável:** Atividade 1 — Validação do Cálculo da Alíquota de Referência  
**Responsável RFB:** Coordenação-Geral de Tributação (COSIT)  
**Data de entrega à equipe GT:** 2026-04-15

---

## 1. Objeto da Metodologia

Este módulo descreve a metodologia utilizada pela Receita Federal do Brasil (RFB) para apurar a base de cálculo da CBS incidente sobre prestações de **serviços de tecnologia da informação (TI)** para o exercício de referência 2025, conforme disposto na Lei Complementar nº 214/2025, Artigo 7º, §§ 1º a 4º.

O escopo abrange os seguintes CNAE:
- **6201-5/00** — Desenvolvimento de programas de computador sob encomenda
- **6202-3/00** — Desenvolvimento e licenciamento de programas de computador customizáveis
- **6203-1/00** — Desenvolvimento e licenciamento de programas de computador não-customizáveis
- **6209-1/00** — Suporte técnico, manutenção e outros serviços em tecnologia da informação

---

## 2. Fontes de Dados

| # | Fonte | Sistema | Granularidade | Período |
|---|-------|---------|---------------|---------|
| 1 | SPED Contribuições | EFD-Contribuições | Estabelecimento / Mês | Jan–Dez 2025 |
| 2 | DCTF Web | Portal e-CAC | CNPJ raiz / Mês | Jan–Dez 2025 |
| 3 | CNPJ Cadastro | REDESIM | Estabelecimento | 31/12/2025 |
| 4 | RAIS 2025 | MTE | Estabelecimento / Ano | 2025 |

Todas as fontes foram consolidadas na base analítica do SERPRO mediante protocolo de transferência FTP seguro (chave RSA-4096), em 2026-02-10, com hash SHA-256 registrado no log de transferência (arquivo `log_transferencia_20260210.txt`).

---

## 3. Cadeia de Produção dos Dados

```
EFD-Contribuições (raw SPED) 
    → script_extracao.sql (ETL inicial — extração, filtragem CNAE, limpeza)
    → notebook_transform.ipynb (transformação, cruzamento com CNPJ/RAIS, flag de outliers)
    → planilha_cbs.xlsx (consolidação final por CNAE e porte)
    → Relatório de Alíquota de Referência MOD_SINT_001
```

---

## 4. Metodologia de Cálculo

### 4.1 Definição da Base de Cálculo

A base de cálculo (BC) da CBS é a **receita bruta** auferida pelo contribuinte com a prestação de serviços de TI, deduzidas as parcelas previstas no Art. 8º da LC 214/2025:

```
BC = Receita Bruta
   - Devoluções e Cancelamentos
   - Descontos Incondicionais
   - Transferências de ICMS para Estados (não aplicável a serviços)
```

Para o setor de TI, **não há dedução de insumos** na modalidade CBS padrão; a dedução de créditos ocorre pelo método de base ampla do IBS, mas não integra este cálculo.

### 4.2 Alíquota de Referência

A alíquota de referência CBS para serviços de TI é calculada como:

```
Alíquota_Ref = (Receita_CBS_Apurada / BC_Total) × 100
```

Onde:
- `Receita_CBS_Apurada`: soma dos valores efetivamente recolhidos à título de CBS (código de receita 1234-5 no DARF)
- `BC_Total`: soma das bases de cálculo declaradas no EFD-Contribuições (campo `VL_BC_COFINS` dos registros M200, M600)

### 4.3 Estratificação por Porte

O cálculo foi estratificado por **porte de empresa** conforme critério do Simples Nacional:

| Porte | Faturamento Anual | N° Empresas | BC Total (R$ bi) | Alíquota Ref. (%) |
|-------|-------------------|-------------|------------------|-------------------|
| ME    | até R$ 360 mil    | 48.230      | 12,4             | 8,65              |
| EPP   | até R$ 4,8 mi     | 31.450      | 87,3             | 8,71              |
| Outros| acima de R$ 4,8 mi| 8.920       | 1.423,7          | 8,78              |
| **Total** | —             | **88.600**  | **1.523,4**      | **8,77**          |

### 4.4 Tratamento de Outliers

Foram identificadas **147 empresas** com alíquota efetiva > 20% ou < 2%, classificadas como outliers pelo critério de ±3 desvios-padrão da média do CNAE. Essas empresas foram:
- Investigadas individualmente por auditores da COSIT (34 casos resolvidos: erro de preenchimento)
- Excluídas da base de cálculo da alíquota de referência (113 casos com comportamento atípico confirmado)

A exclusão reduz a base de 88.600 para **88.487 empresas** e não altera a alíquota de referência em mais de 0,02 pp.

---

## 5. Limitações Declaradas

1. **SPED 2025 parcial**: 3,2% dos estabelecimentos entregaram EFD com atraso > 30 dias; foram incluídos na base com flag `ENTREGA_TARDIA=1` e contribuem com estimativa proporcional.
2. **Cruzamento RAIS incompleto**: 412 CNPJ sem correspondência na RAIS 2025 (possível encerramento não informado ao MTE); foram mantidos na base com flag `RAIS_AUSENTE=1`.
3. **Câmbio**: prestações em moeda estrangeira convertidas pela PTAX do último dia útil de cada mês (Banco Central); potencial subestimação em meses de alta volatilidade cambial.

---

## 6. Verificações Internas de Consistência Realizadas

| Verificação | Resultado |
|-------------|-----------|
| Soma de BC por CNAE bate com total consolidado | ✓ OK (diferença < R$ 0,01) |
| Alíquota calculada na planilha bate com script SQL | ✓ OK (diferença: 0,0000%) |
| N° de CNPJs únicos na planilha bate com query SQL | ✓ OK (88.487 em ambos) |
| Outliers excluídos devidamente sinalizados | ✓ OK |
| Hash SHA-256 dos arquivos-fonte conferido | ✓ OK |

---

## 7. Documentos Entregues

| Arquivo | Descrição |
|---------|-----------|
| `planilha_cbs.xlsx` | Consolidação final com alíquotas por CNAE e porte |
| `script_extracao.sql` | ETL inicial — consultas SQL de extração e filtragem |
| `notebook_transform.ipynb` | Transformação e cruzamento de bases |
| `descricao_metodologica.md` | Este documento |

---

*Módulo sintético elaborado para fins de piloto do DVA-CBS | TC 015.848/2025-6*  
*Dados numéricos são fictícios — não representam valores reais da RFB*
