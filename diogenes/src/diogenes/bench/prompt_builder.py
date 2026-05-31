"""
bench/prompt_builder.py — DVA-CBS | Projeto Diógenes
Construtor de prompts REDUZIDOS para pipeline de bancada.

System prompt = soul.md + heartbeat section (só a seção do call_type).
Omite agent.md e skills.md intencionalmente (55K → ~12K).

User prompt = conteúdo real dos CSVs ou dados do catálogo.
"""
from __future__ import annotations

from pathlib import Path

from diogenes.agents.heartbeat import HeartbeatLoader
from diogenes.bench.core import _project_root, _read_if_exists, load_agents_spec

# Limite de linhas por CSV antes de truncar (evita tokens excessivos)
_MAX_CSV_LINES = 2000


def build_reduced_system(
    agent_id: str,
    call_type: str,
    project_root: Path | None = None,
) -> str:
    """Monta system prompt REDUZIDO: soul + heartbeat section."""
    root = project_root or _project_root()
    docs_dir = root / "docs" / "agentes" / agent_id

    soul = _read_if_exists(docs_dir / "soul.md")
    heartbeat_path = docs_dir / "heartbeat.md"

    loader = HeartbeatLoader(heartbeat_path)
    section = loader.get_section(call_type)

    parts: list[str] = []
    if soul:
        parts.append(soul)
    if section:
        parts.append(f"# Instruções operacionais — {call_type}\n\n{section}")
    else:
        # Fallback: se seção não encontrada, usar heartbeat completo (menos ideal)
        full = _read_if_exists(heartbeat_path)
        if full:
            parts.append(full)

    return "\n\n---\n\n".join(parts)


def build_user_irene_catalog(
    csvs: list[tuple[str, str]],
    catalog_json: str | None = None,
) -> str:
    """User prompt para Irene/Mycroft: lista de abas disponíveis."""
    lines = ["# Catálogo de arquivos disponíveis\n"]
    for filename, content in csvs:
        line_count = content.count("\n")
        header = content.split("\n", 1)[0] if content else ""
        lines.append(f"- **{filename}** ({line_count} linhas): colunas = `{header}`")
    if catalog_json:
        lines.append(f"\n## CATALOGO.json\n```json\n{catalog_json}\n```")
    return "\n".join(lines)


def build_user_watson_analise(
    filename: str,
    csv_content: str,
    irene_classification: str | None = None,
) -> str:
    """User prompt para Watson análise individual de CSV."""
    lines = [f"# Arquivo para análise: {filename}\n"]
    if irene_classification:
        lines.append(f"**Classificação Irene:** {irene_classification}\n")

    csv_lines = csv_content.splitlines()
    if len(csv_lines) > _MAX_CSV_LINES:
        truncated = "\n".join(csv_lines[:_MAX_CSV_LINES])
        lines.append(
            f"## Conteúdo (truncado em {_MAX_CSV_LINES} de {len(csv_lines)} linhas)\n"
            f"```csv\n{truncated}\n```\n"
            f"⚠ {len(csv_lines) - _MAX_CSV_LINES} linhas omitidas."
        )
    else:
        lines.append(f"## Conteúdo completo ({len(csv_lines)} linhas)\n```csv\n{csv_content}\n```")

    return "\n".join(lines)


def build_user_watson_consolidar(
    analises: list[tuple[str, str]],
) -> str:
    """User prompt para Watson consolidar múltiplas análises."""
    lines = ["# Consolidação de análises de integridade\n"]
    lines.append(f"Total de arquivos analisados: {len(analises)}\n")
    for filename, analysis in analises:
        lines.append(f"## {filename}\n{analysis}\n")
    return "\n".join(lines)


def build_user_mycroft_tasks(
    catalog_summary: str,
    module_name: str,
) -> str:
    """User prompt para Mycroft definir tasks Watson."""
    return (
        f"# Definição de tarefas Watson — {module_name}\n\n"
        f"Analise o catálogo abaixo e defina as tarefas de integridade "
        f"para Watson executar em cada arquivo.\n\n"
        f"{catalog_summary}"
    )


def build_user_mycroft_avaliar(
    agent_output: str,
    agent_name: str = "Watson",
) -> str:
    """User prompt para Mycroft avaliar output de outro agente."""
    return (
        f"# Avaliação do output de {agent_name}\n\n"
        f"Avalie a qualidade, completude e pertinência da análise abaixo.\n\n"
        f"## Output de {agent_name}\n{agent_output}"
    )


def build_user_sherlock(
    watson_consolidado: str,
    mycroft_decisao: str,
) -> str:
    """User prompt para Sherlock validação metodológica."""
    return (
        "# Pacote para validação metodológica\n\n"
        "## Consolidação Watson (integridade)\n"
        f"{watson_consolidado}\n\n"
        "## Decisão Mycroft sobre Watson\n"
        f"{mycroft_decisao}"
    )


def build_user_mycroft_consolidar(
    watson_consolidado: str,
    sherlock_validacao: str,
    mycroft_decisao_watson: str,
    mycroft_decisao_sherlock: str,
) -> str:
    """User prompt para Mycroft consolidar relatório final."""
    return (
        "# Consolidação final do ciclo\n\n"
        "## Watson — Consolidação de integridade\n"
        f"{watson_consolidado}\n\n"
        "## Mycroft — Decisão sobre Watson\n"
        f"{mycroft_decisao_watson}\n\n"
        "## Sherlock — Validação metodológica\n"
        f"{sherlock_validacao}\n\n"
        "## Mycroft — Decisão sobre Sherlock\n"
        f"{mycroft_decisao_sherlock}"
    )


def get_model_for_agent(agent_id: str, model_override: str | None = None) -> str:
    """Retorna modelo configurado ou override."""
    if model_override:
        return model_override
    specs = load_agents_spec()
    if agent_id not in specs:
        raise ValueError(f"Agente '{agent_id}' não encontrado em agents_spec.yaml")
    return specs[agent_id].modelo
