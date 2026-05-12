# DVA-CBS | Projeto Diógenes

**Departamento de Validação Assistida da CBS**  
TC 015.848/2025-6 | TCU / SecexContas

> Uso Interno Restrito.

## Inicialização rápida

```bash
# 1. Clonar e entrar no repositório
git clone <url> diogenes && cd diogenes

# 2. Instalar (Python 3.11+)
pip install -e ".[dev]"

# 3. Configurar
cp .env.example .env
# Editar .env: DIOGENES_LLM_API_KEY, DIOGENES_LLM_BASE_URL, DIOGENES_WORKSPACE

# 4. Inicializar workspace
diogenes init

# 5. Verificar
diogenes --help
```

## Operação básica

```bash
# Adicionar arquivos do módulo
cp -r /caminho/pacote_rfb/ $DIOGENES_WORKSPACE/input/MOD_010/

# Abrir ciclo
diogenes start --module MOD_010 --activity 1

# Ler manifesto, preencher prioridades, confirmar
diogenes confirm-manifest --cycle MOD_010_A1_YYYYMMDDTHHMMSSZ

# [ciclo executa automaticamente após Sprint 2]

# Verificar e chancelas
diogenes verify-output --cycle <id>
diogenes seal --cycle <id>
```

## Documentos de referência
- `docs/agentes/` — definição dos agentes (soul, skills, agent, heartbeat)
- `PRD_Piloto_Diogenes_v01.md` — requisitos do piloto
- `SDD_Piloto_Diogenes_v01.md` — arquitetura de software

*DVA-CBS | Projeto Diógenes | TC 015.848/2025-6*
