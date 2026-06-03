"""
bench/prompt_builder.py — DVA-CBS | Projeto Diógenes
Construtor de prompts REDUZIDOS para pipeline de bancada.

System prompt = soul.md + heartbeat section (só a seção do call_type).
Omite agent.md e skills.md intencionalmente (55K → ~12K).

User prompt = conteúdo real dos CSVs ou dados do catálogo.
"""
from __future__ import annotations

from pathlib import Path

from diogenes.agents.file_prep import rotulo_tipo  # re-export — fonte única de tipos
from diogenes.agents.heartbeat import HeartbeatLoader
from diogenes.bench.core import _project_root, _read_if_exists, load_agents_spec

__all__ = ["rotulo_tipo"]  # mantém rotulo_tipo importável a partir deste módulo

# file_prep é a fonte única de truncamento por tipo (Etapa 2). Aqui mantemos apenas
# uma rede de segurança em chars contra conteúdos extremos, sem re-truncar por linhas.
_MAX_CHARS_SEGURANCA = 160_000

# Linguagem da cerca de código por tipo (apresentação no prompt).
_CERCA_POR_TIPO: dict[str, str] = {
    "csv": "csv",
    "planilha": "text",
    "sql": "sql",
    "notebook": "python",
    "script": "python",
    "esquema": "json",
    "documento": "markdown",
}


def _cerca_por_tipo(tipo: str) -> str:
    """Linguagem da cerca de código apropriada para o tipo."""
    return _CERCA_POR_TIPO.get(tipo, "text")


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
    content: str,
    tipo: str | None = None,
    irene_classification: str | None = None,
) -> str:
    """User prompt para Watson — análise individual de um arquivo de qualquer tipo.

    `content` já vem convertido para texto por file_prep.preparar_arquivo (xlsx, sql,
    ipynb, pdf) ou é o texto bruto (csv, md, py). `tipo` é o rótulo derivado da
    extensão (ver rotulo_tipo); orienta Watson sobre qual análise do heartbeat aplicar.
    """
    tipo_efetivo = tipo or rotulo_tipo(filename)
    cerca = _cerca_por_tipo(tipo_efetivo)

    lines = [
        f"# Arquivo para análise: {filename}\n",
        f"**Tipo identificado:** {tipo_efetivo}\n",
    ]
    if irene_classification:
        lines.append(f"**Classificação Irene:** {irene_classification}\n")

    # O conteúdo já vem truncado por file_prep (fonte única). Aqui só uma rede de
    # segurança em chars contra extremos, sem re-truncar por linhas.
    if len(content) > _MAX_CHARS_SEGURANCA:
        content = content[:_MAX_CHARS_SEGURANCA] + "\n[TRUNCADO — rede de segurança da bancada]"
    lines.append(f"## Conteúdo\n```{cerca}\n{content}\n```")

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
    module_docs: str | None = None,
) -> str:
    """User prompt para Mycroft definir tasks Watson.

    `catalog_summary` é o inventário multi-tipo dos arquivos da entrega.
    `module_docs`, quando presente, é o resumo da documentação do módulo (briefing,
    regra de negócio) — contexto para Mycroft definir o escopo das tasks.
    """
    parts = [
        f"# Definição de tarefas Watson — {module_name}\n",
        "Analise o inventário abaixo e defina as tarefas de integridade "
        "para Watson executar em cada arquivo, na ordem da cadeia de produção "
        "(documentação → SQL → notebooks → planilhas de resultado → outros).\n",
        f"## Inventário da entrega\n{catalog_summary}",
    ]
    if module_docs:
        parts.append(f"\n## Documentação do módulo (briefing / regra de negócio)\n{module_docs}")
    return "\n".join(parts)


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
    metodologia: str | None = None,
    corpus_juridico: str | None = None,
) -> str:
    """User prompt para Sherlock validação metodológica.

    `metodologia` é a documentação metodológica / regra de negócio do módulo (cat. C);
    `corpus_juridico` é o recorte curado do arcabouço jurídico do módulo (cat. D) —
    a régua contra a qual Sherlock valida. Sem esses insumos Sherlock só consegue
    registrar limitação metodológica.
    """
    parts = [
        "# Pacote para validação metodológica\n",
    ]
    if metodologia:
        parts.append(
            "## Metodologia e regra de negócio do módulo\n"
            f"{metodologia}\n"
        )
    if corpus_juridico:
        parts.append(
            "## Arcabouço jurídico curado do módulo (dispositivos aplicáveis)\n"
            f"{corpus_juridico}\n"
        )
    parts.append(
        "## Consolidação Watson (integridade)\n"
        f"{watson_consolidado}\n"
    )
    parts.append(
        "## Decisão Mycroft sobre Watson\n"
        f"{mycroft_decisao}"
    )
    return "\n".join(parts)


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
