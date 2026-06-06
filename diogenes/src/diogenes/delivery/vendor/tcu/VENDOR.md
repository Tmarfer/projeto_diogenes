# Bibliotecas TCU vendorizadas — Fase de Entrega

Cópias **vendorizadas** (não referenciadas via OneDrive em runtime) das bibliotecas
utilitárias do projeto `4-CalculoCBS2027` que geram os documentos institucionais
no padrão GT Reforma Tributária / SecexContas.

## Proveniência

- **Origem:** `4-CalculoCBS2027/4-SCRIPTS_PROCESSAMENTO/UTILITARIOS/01-BIBLIOTECAS_UTILITARIAS/`
- **Copiado em:** 2026-06-04
- **Motivo:** o projeto Diógenes não deve depender, em runtime, de um caminho do
  OneDrive que não existe nas demais máquinas/CI. As libs foram trazidas como cópia.

## Arquivos

| Arquivo | Papel |
|---------|-------|
| `tcu_formatter.py` | Motor base de DOCX institucional — classe `TCUFormatter`. |
| `tcu_apendice_gerador.py` | Apêndice de 7 seções — classe `ApendiceGerador` (importa `tcu_formatter`). |
| `gerar_ficha_sintese_pdf_png.py` | Conversor HTML→PDF/PNG via Playwright/Chromium — `gerar_documentos()`. |
| `tcu_docx_lib.py` | Shim de compatibilidade que re-exporta `tcu_formatter`. |
| `logo_tcu_extracted.png` | Logo TCU usado no header dos DOCX. |

## Dependências

- `python-docx>=1.1.0`, `matplotlib>=3.8.0` (gráficos), `playwright>=1.40.0` (+ `python -m playwright install chromium`).

## Como atualizar

Recopiar os arquivos da pasta de origem e atualizar a data acima. **Não editar**
as cópias diretamente — mudanças devem nascer na biblioteca-fonte e ser revendorizadas.
O acesso é feito sempre por import relativo do pacote `diogenes.delivery.vendor.tcu`,
nunca pelo caminho do OneDrive.
