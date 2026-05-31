# Fixtures para Bancada Cirúrgica — DVA-CBS | Projeto Diógenes

Fixtures mínimas extraídas do ciclo `MOD_010_A1_20260531T041556Z` (primeiro
ciclo ENCERRADO_CHANCELADO). Cada fixture exercita exatamente 1 `call_type`
de um agente específico.

## Estrutura

```
fixtures/
├── watson/           # Watson (integridade)
├── sherlock/         # Sherlock (metodologia)
├── mycroft/          # Mycroft (orquestrador)
├── motor_saida/      # Motor de Saída (higienização)
└── shared/           # Artefatos compartilhados (catálogo mini, tasks)
```

## Uso via MCP

```
diogenes_call_agent_fixture(
    agent_id="watson",
    fixture_path="tests/fixtures/watson/analise_csv_pequeno.md",
    call_type="analise_inicial",
    dry_run=False
)
```

## Uso via pytest

```python
from pathlib import Path
FIXTURES = Path(__file__).parent / "fixtures"
fixture = (FIXTURES / "watson" / "analise_csv_pequeno.md").read_text()
```

## Princípios

- Mínimas: cada fixture exercita 1 call_type
- Determinísticas: sem dependência de rede ou workspace
- Extraídas do piloto real: MOD_010 (AUX_MOD_10 PF - execução.xlsx)
- Versionadas: entram no git (2-50KB cada)
- Sanitizadas: sem dados sensíveis do processo
