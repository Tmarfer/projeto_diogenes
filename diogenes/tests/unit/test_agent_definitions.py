"""
tests/unit/test_agent_definitions.py — DVA-CBS | Projeto Diógenes
Testes de consistência das definições dos agentes (soul, skills, heartbeat).

Verifica:
- Todos os agentes têm as 4 definições obrigatórias (soul, skills, heartbeat, agent)
- Todos os call_types de cada agente têm seção no heartbeat.md correspondente
- heartbeat.md é parseável e sem seções com conteúdo vazio
- Tags <!-- SECAO: X --> são balanceadas nos skills.md
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

from diogenes.agents.heartbeat import CALL_TYPE_TO_SECTION, HeartbeatLoader

# Raiz do pacote diogenes/ — 3 níveis acima deste arquivo (tests/unit/test_*.py)
DIOGENES_ROOT = Path(__file__).parent.parent.parent
DOCS_AGENTES  = DIOGENES_ROOT / "docs" / "agentes"
AGENTS_SPEC   = DIOGENES_ROOT / "agents_spec.yaml"

# call_types que cada agente deve ter com seção no heartbeat.md.
# Inclui apenas call_types ativos — condicionais (validacao_planilha_rn) também
# são verificados pois devem ter seção mesmo que nem sempre acionados.
AGENT_CALL_TYPES: dict[str, list[str]] = {
    "watson": [
        "analise_inicial",        # → seção "analise_arquivo" via CALL_TYPE_TO_SECTION
        "consolidar_watson",
        "validacao_planilha_rn",
        "resposta_r1",
        "resposta_r2",
    ],
    "mycroft": [
        "definir_tasks_watson",
        "avaliar_agente",
        "fixar_decisao",
        "montar_pacote_sherlock",
        "mapear_pontos",
        "consolidar",
    ],
    "sherlock": [
        "validacao_inicial",
        "validacao_planilha_rn_sherlock",
        "consolidar_sherlock",
        "resposta_r1",
        "resposta_r2",
    ],
}

_DEFINITION_FILES = ("soul.md", "skills.md", "heartbeat.md", "agent.md")

_RE_SECAO_OPEN  = re.compile(r"<!--\s*SECAO:\s*(\S+)\s*-->")
_RE_SECAO_CLOSE = re.compile(r"<!--\s*/SECAO:\s*(\S+)\s*-->")


# ── Existência de arquivos ────────────────────────────────────────────────

class TestDefinitionFilesExist:

    def test_docs_agentes_dir_exists(self) -> None:
        assert DOCS_AGENTES.is_dir(), (
            f"docs/agentes/ não encontrado em {DOCS_AGENTES}. "
            "Executar de dentro do diretório diogenes/."
        )

    def test_agents_spec_exists(self) -> None:
        assert AGENTS_SPEC.is_file(), f"agents_spec.yaml não encontrado em {AGENTS_SPEC}"

    def test_all_active_agents_have_definition_dirs(self) -> None:
        for agent_id in AGENT_CALL_TYPES:
            assert (DOCS_AGENTES / agent_id).is_dir(), (
                f"Pasta de definições de '{agent_id}' não encontrada: "
                f"{DOCS_AGENTES / agent_id}"
            )

    @pytest.mark.parametrize("agent_id", list(AGENT_CALL_TYPES.keys()) + ["irene"])
    def test_agent_has_all_required_files(self, agent_id: str) -> None:
        agent_dir = DOCS_AGENTES / agent_id
        if not agent_dir.is_dir():
            pytest.skip(f"Pasta {agent_id} não encontrada")
        missing = [f for f in _DEFINITION_FILES if not (agent_dir / f).is_file()]
        assert not missing, (
            f"Agente '{agent_id}' — arquivos ausentes: {missing}"
        )

    def test_agents_in_spec_have_docs_dirs(self) -> None:
        with open(AGENTS_SPEC, encoding="utf-8") as f:
            spec = yaml.safe_load(f)
        missing_dirs = [
            aid for aid in spec.get("agentes", {})
            if not (DOCS_AGENTES / aid).is_dir()
        ]
        assert not missing_dirs, (
            f"Agentes em agents_spec.yaml sem pasta em docs/agentes/: {missing_dirs}"
        )


# ── Consistência do heartbeat ─────────────────────────────────────────────

class TestHeartbeatConsistency:

    @pytest.mark.parametrize("agent_id,call_types", list(AGENT_CALL_TYPES.items()))
    def test_all_call_types_have_heartbeat_section(
        self, agent_id: str, call_types: list[str]
    ) -> None:
        """Cada call_type tem seção não-vazia no heartbeat.md do agente."""
        heartbeat_path = DOCS_AGENTES / agent_id / "heartbeat.md"
        assert heartbeat_path.is_file(), f"heartbeat.md ausente para '{agent_id}'"

        loader = HeartbeatLoader(heartbeat_path)
        missing: list[str] = []
        for call_type in call_types:
            section = loader.get_section(call_type)
            if not section.strip():
                section_name = CALL_TYPE_TO_SECTION.get(call_type, call_type)
                missing.append(f"{call_type!r} → seção esperada: {section_name!r}")

        assert not missing, (
            f"Agente '{agent_id}': call_types sem seção no heartbeat.md:\n"
            + "\n".join(f"  - {m}" for m in missing)
        )

    @pytest.mark.parametrize("agent_id", list(AGENT_CALL_TYPES.keys()))
    def test_heartbeat_sections_not_empty(self, agent_id: str) -> None:
        """Nenhuma seção parseada do heartbeat.md tem conteúdo vazio."""
        loader = HeartbeatLoader(DOCS_AGENTES / agent_id / "heartbeat.md")
        sections = loader.available_sections()
        assert sections, f"heartbeat.md de '{agent_id}' não tem seções parseáveis."

        empty = [s for s in sections if not loader.get_section(s).strip()]
        assert not empty, (
            f"heartbeat.md de '{agent_id}': seções com conteúdo vazio: {empty}"
        )


# ── Balanceamento de tags SECAO nos skills.md ─────────────────────────────

class TestSkillsSecaoTags:

    @pytest.mark.parametrize("agent_id", list(AGENT_CALL_TYPES.keys()) + ["irene"])
    def test_secao_tags_balanced(self, agent_id: str) -> None:
        """<!-- SECAO: X --> e <!-- /SECAO: X --> são balanceadas."""
        skills_path = DOCS_AGENTES / agent_id / "skills.md"
        if not skills_path.is_file():
            pytest.skip(f"skills.md não encontrado para '{agent_id}'")

        text = skills_path.read_text(encoding="utf-8")
        opens  = [m.group(1) for m in _RE_SECAO_OPEN.finditer(text)]
        closes = [m.group(1) for m in _RE_SECAO_CLOSE.finditer(text)]

        unmatched_open  = [s for s in opens  if opens.count(s)  != closes.count(s)]
        unmatched_close = [s for s in closes if closes.count(s) != opens.count(s)]

        issues: list[str] = []
        if unmatched_open:
            issues.append(f"Sem fechamento: {sorted(set(unmatched_open))}")
        if unmatched_close:
            issues.append(f"Sem abertura: {sorted(set(unmatched_close))}")

        assert not issues, (
            f"skills.md de '{agent_id}': tags SECAO desbalanceadas — "
            + "; ".join(issues)
        )
