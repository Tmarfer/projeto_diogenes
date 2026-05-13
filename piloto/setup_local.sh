#!/usr/bin/env bash
# setup_local.sh — Prepara o ambiente local para executar o piloto Fase A
# DVA-CBS | Projeto Diógenes | TC 015.848/2025-6
#
# USO:
#   chmod +x piloto/setup_local.sh
#   ./piloto/setup_local.sh
#
# O script assume que você está na raiz do repositório (projeto_diogenes/).
# Requer Python 3.11+ e pip instalados.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DIOGENES_DIR="$REPO_ROOT/diogenes"
WORKSPACE_DIR="$HOME/diogenes_workspace"

echo "=== DVA-CBS | Projeto Diógenes — Setup Local ==="
echo ""
echo "Repositório : $REPO_ROOT"
echo "Pacote      : $DIOGENES_DIR"
echo "Workspace   : $WORKSPACE_DIR"
echo ""

# ── 1. Instalar o pacote ───────────────────────────────────────────────────
echo "[1/4] Instalando pacote Python..."
cd "$DIOGENES_DIR"
pip install -e ".[dev]" --quiet
echo "      OK: diogenes instalado"

# ── 2. Criar .env se não existir ──────────────────────────────────────────
if [ ! -f "$DIOGENES_DIR/.env" ]; then
    cp "$DIOGENES_DIR/.env.example" "$DIOGENES_DIR/.env"
    echo ""
    echo "      ATENÇÃO: .env criado a partir de .env.example"
    echo "      Edite $DIOGENES_DIR/.env e preencha DIOGENES_LLM_API_KEY"
    echo "      antes de continuar."
    echo ""
fi

# Verificar se a chave foi preenchida
if grep -q "DIOGENES_LLM_API_KEY=$" "$DIOGENES_DIR/.env" || \
   grep -q "DIOGENES_LLM_API_KEY=<sua_chave>" "$DIOGENES_DIR/.env"; then
    echo ""
    echo "ERRO: DIOGENES_LLM_API_KEY está em branco em .env"
    echo "      Obtenha sua chave em https://openrouter.ai/keys"
    echo "      e preencha no arquivo: $DIOGENES_DIR/.env"
    exit 1
fi

# ── 3. Copiar inputs do MOD_SINT_001 para o workspace ────────────────────
echo "[2/4] Criando workspace em $WORKSPACE_DIR..."
mkdir -p "$WORKSPACE_DIR/input/MOD_SINT_001/entrega"
mkdir -p "$WORKSPACE_DIR/input/MOD_SINT_001/gt_artefatos"

SRC="$REPO_ROOT/piloto/workspace_sample/input/MOD_SINT_001"
DST="$WORKSPACE_DIR/input/MOD_SINT_001"

cp "$SRC/briefing.md"                              "$DST/"
cp "$SRC/entrega/descricao_metodologica.md"        "$DST/entrega/"
cp "$SRC/entrega/notebook_transform.ipynb"         "$DST/entrega/"
cp "$SRC/entrega/planilha_cbs.xlsx"                "$DST/entrega/"
cp "$SRC/entrega/script_extracao.sql"              "$DST/entrega/"
cp "$SRC/gt_artefatos/ata_reuniao_entrega.md"      "$DST/gt_artefatos/"
cp "$SRC/gt_artefatos/regras_negocio.md"           "$DST/gt_artefatos/"

echo "      OK: 7 arquivos copiados para $WORKSPACE_DIR/input/MOD_SINT_001/"

# ── 4. Inicializar workspace ──────────────────────────────────────────────
echo "[3/4] Inicializando workspace..."
cd "$DIOGENES_DIR"
diogenes init
echo ""

# ── 5. Instruções finais ──────────────────────────────────────────────────
echo "[4/4] Setup concluído! Execute o ciclo Fase A:"
echo ""
echo "  cd $DIOGENES_DIR"
echo "  diogenes start --module MOD_SINT_001 --activity 1"
echo "  # → Anote o CYCLE_ID impresso"
echo "  diogenes confirm-manifest --cycle <CYCLE_ID>"
echo "  # → Aguarde (pode levar 10–20 min)"
echo ""
echo "  # Se Watson encontrar alertas críticos:"
echo "  diogenes proceed --cycle <CYCLE_ID>    # autorizar e continuar"
echo "  # ou"
echo "  diogenes pause --cycle <CYCLE_ID>      # pausar para revisão"
echo ""
echo "  # Ao final:"
echo "  diogenes verify-output --cycle <CYCLE_ID>"
echo "  diogenes seal --cycle <CYCLE_ID>"
echo ""
