"""
persistence/manifest.py — DVA-CBS | Projeto Diógenes
Geração e leitura do manifesto de abertura de ciclo (manifest.md).

O manifesto é gerado pelo Motor de Start e confirmado por Lestrade.
Schema conforme o template em docs/agentes/manifesto_abertura_template.md.

Referência normativa: RF-MS-05 (PRD v0.1), Bloco 5.3 (SDD v0.1)
"""

from __future__ import annotations

from pathlib import Path

from diogenes.models import CycleManifest

ACTIVITY_NAMES: dict[int, str] = {
    1: "Atividade 1 — Validação de Módulo",
    2: "Atividade 2 — Revalidação de Módulo",
}


def render_manifesto(manifest: CycleManifest) -> str:
    """Renderiza o CycleManifest para Markdown conforme o template institucional."""
    activity_name = ACTIVITY_NAMES.get(manifest.activity, f"Atividade {manifest.activity}")
    sala_str = "Sim" if manifest.is_sigilo_module else "Não"

    # Tabela de arquivos
    rows: list[str] = []
    for f in manifest.input_files:
        size_str = (
            f"{f.size_bytes / 1_048_576:.2f} MB"
            if f.size_bytes >= 1_048_576
            else f"{f.size_bytes / 1_024:.1f} KB"
        )
        hash_short = f"{f.sha256[:16]}...{f.sha256[-8:]}"
        rows.append(
            f"| {f.name} | {f.extension or '—'} | {size_str} "
            f"| `{hash_short}` | `inputs/{f.rel_path}` |"
        )
    table = "\n".join(rows)

    prioridades = manifest.prioridades_analise or "[não preenchido]"
    alertas = manifest.alertas_lestrade or "[Nenhuma condição especial identificada.]"
    confirmed_status = "CONFIRMADO" if manifest.confirmed_at_utc else "PENDENTE"
    confirmed_ts = manifest.confirmed_at_utc or "—"
    prev = f"\n**Ciclo anterior:** `{manifest.previous_cycle_id}`" if manifest.previous_cycle_id else ""

    return (
        f"# Manifesto de Abertura\n"
        f"**Processo:** TC 015.848/2025-6\n"
        f"**Módulo:** {manifest.module_id}\n"
        f"**Identificador:** {manifest.module_id}\n"
        f"**Atividade:** {activity_name}\n"
        f"**Ciclo:** Ciclo {manifest.cycle_num} | `{manifest.cycle_id}`{prev}\n"
        f"**Timestamp de abertura (UTC):** {manifest.opened_at_utc}\n"
        f"**Sala de Sigilo:** {sala_str}\n"
        f"**Hash de integridade do pacote:** `{manifest.package_hash}`\n"
        f"**Versão do sistema:** diogenes {manifest.diogenes_version} | "
        f"Python {manifest.python_version} | openai {manifest.openai_version}\n"
        f"**Commit:** `{manifest.git_commit}`\n"
        f"\n---\n\n"
        f"## Arquivos Recebidos\n\n"
        f"| Arquivo | Formato | Tamanho | Hash SHA-256 | Caminho em inputs/ |\n"
        f"|---------|---------|---------|--------------|--------------------|\n"
        f"{table}\n\n"
        f"**Total de arquivos:** {len(manifest.input_files)}\n"
        f"**Inventário declarado pela RFB:** Não declarado — piloto local\n"
        f"**Observação:** Nenhuma\n"
        f"\n---\n\n"
        f"## Prioridades de Análise\n\n"
        f"*Campo a preencher por Lestrade antes de confirmar este manifesto.*\n\n"
        f"**Critério de priorização:**\n"
        f"{prioridades}\n\n"
        f"*Se não preenchido, Mycroft aplica a ordem padrão: "
        f"documentação → scripts SQL → notebooks Python → planilhas → outros.*\n"
        f"\n---\n\n"
        f"## Condições Especiais\n\n"
        f"**Alertas de Lestrade:**\n"
        f"{alertas}\n"
        f"\n---\n\n"
        f"## Confirmação de Lestrade\n\n"
        f"**Status:** {confirmed_status}\n"
        f"**Timestamp de confirmação:** {confirmed_ts}\n"
        f"**Próximo passo:** "
        f"`diogenes confirm-manifest --cycle {manifest.cycle_id}`\n"
        f"\n---\n\n"
        f"*DVA-CBS | Projeto Diógenes | TC 015.848/2025-6*\n"
        f"*Manifesto gerado automaticamente pelo Motor de Start | Uso interno restrito*\n"
    )


def write_manifesto(manifest: CycleManifest, cycle_dir: Path) -> Path:
    """Escreve o manifesto em cycle_dir/manifest.md e retorna o Path."""
    path = cycle_dir / "manifest.md"
    path.write_text(render_manifesto(manifest), encoding="utf-8")
    return path


def update_manifesto_confirmado(manifest_path: Path, confirmed_at_utc: str) -> None:
    """Atualiza os campos de confirmação no manifesto existente."""
    content = manifest_path.read_text(encoding="utf-8")
    content = content.replace(
        "**Status:** PENDENTE\n**Timestamp de confirmação:** —",
        f"**Status:** CONFIRMADO\n**Timestamp de confirmação:** {confirmed_at_utc}",
    )
    manifest_path.write_text(content, encoding="utf-8")
