"""
bench/core.py — DVA-CBS | Projeto Diógenes
Core da bancada cirúrgica: montagem de prompts, validação de modelos, chamada isolada.
Compartilhado entre o CLI (diogenes bench) e o MCP (integra-chattcu).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from diogenes.agents.heartbeat import HeartbeatLoader
from diogenes.config import get_config


@dataclass
class AgentSpec:
    agent_id: str
    modelo: str
    temperatura: float = 0.0
    max_tokens: int | None = None
    timeout_segundos: int = 180
    retries: int = 4


@dataclass
class PromptBundle:
    """Resultado da montagem de prompt para bancada."""
    agent_id: str
    call_type: str | None
    system_prompt: str
    user_prompt: str
    model: str
    system_chars: int = 0
    user_chars: int = 0
    heartbeat_full_chars: int = 0
    heartbeat_used_chars: int = 0

    def __post_init__(self):
        self.system_chars = len(self.system_prompt)
        self.user_chars = len(self.user_prompt)

    @property
    def estimated_tokens(self) -> int:
        return max(1, (self.system_chars + self.user_chars) // 4)

    @property
    def heartbeat_reduction_pct(self) -> float:
        if self.heartbeat_full_chars == 0:
            return 0.0
        return round((1 - self.heartbeat_used_chars / self.heartbeat_full_chars) * 100, 1)


def _project_root() -> Path:
    """Resolve project root (where agents_spec.yaml lives).
    Uses cwd since diogenes commands are always run from the project root.
    """
    cwd = Path.cwd()
    if (cwd / "agents_spec.yaml").is_file():
        return cwd
    # Fallback: try to derive from config workspace path
    try:
        cfg = get_config()
        candidate = Path(cfg.workspace.path).resolve().parent
        if (candidate / "agents_spec.yaml").is_file():
            return candidate
    except Exception:
        pass
    return cwd


def load_agents_spec(project_root: Path | None = None) -> dict[str, AgentSpec]:
    """Load agents_spec.yaml and return parsed specs."""
    root = project_root or _project_root()
    spec_path = root / "agents_spec.yaml"
    if not spec_path.is_file():
        raise FileNotFoundError(f"agents_spec.yaml not found at {root}")

    with open(spec_path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    agents: dict[str, AgentSpec] = {}
    for agent_id, cfg in data.get("agentes", {}).items():
        agents[agent_id] = AgentSpec(
            agent_id=agent_id,
            modelo=str(cfg.get("modelo", "")),
            temperatura=float(cfg.get("temperatura", 0.0)),
            max_tokens=cfg.get("max_tokens"),
            timeout_segundos=int(cfg.get("timeout_segundos", 180)),
            retries=int(cfg.get("max_tentativas_retry", cfg.get("retries", 4))),
        )
    return agents


def build_prompt(
    agent_id: str,
    user_prompt: str,
    call_type: str | None = None,
    project_root: Path | None = None,
    model_override: str | None = None,
) -> PromptBundle:
    """Build a complete prompt bundle for bench testing."""
    root = project_root or _project_root()
    specs = load_agents_spec(root)

    if agent_id not in specs:
        raise ValueError(
            f"Agent '{agent_id}' not found. Available: {sorted(specs.keys())}"
        )

    spec = specs[agent_id]
    docs_dir = root / "docs" / "agentes" / agent_id

    # Load individual docs
    soul = _read_if_exists(docs_dir / "soul.md")
    agent_doc = _read_if_exists(docs_dir / "agent.md")
    skills = _read_if_exists(docs_dir / "skills.md")
    heartbeat_path = docs_dir / "heartbeat.md"
    heartbeat_full = _read_if_exists(heartbeat_path)
    heartbeat_full_chars = len(heartbeat_full)

    # Extract heartbeat section if call_type provided
    heartbeat_section = ""
    if call_type and heartbeat_full:
        loader = HeartbeatLoader(heartbeat_path)
        heartbeat_section = loader.get_section(call_type)

    heartbeat_used = heartbeat_section or heartbeat_full
    heartbeat_used_chars = len(heartbeat_used)

    # Build system prompt
    parts: list[str] = []
    if soul:
        parts.append(f"# soul.md\n{soul}")
    if agent_doc:
        parts.append(f"# agent.md\n{agent_doc}")
    if heartbeat_used:
        label = f"heartbeat.md (seção: {call_type})" if heartbeat_section else "heartbeat.md"
        parts.append(f"# {label}\n{heartbeat_used}")
    if skills:
        parts.append(f"# skills.md\n{skills}")

    system_prompt = "\n\n---\n\n".join(parts)
    model = model_override or spec.modelo

    return PromptBundle(
        agent_id=agent_id,
        call_type=call_type,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        model=model,
        heartbeat_full_chars=heartbeat_full_chars,
        heartbeat_used_chars=heartbeat_used_chars,
    )


def validate_models(project_root: Path | None = None) -> list[dict[str, Any]]:
    """Validate all configured models against ChatTCU catalog.

    Returns list of dicts with validation results per agent.
    Does NOT call LLM — only checks model availability.
    """
    from diogenes.config import get_config
    from diogenes.llm.chattcu import ChatTCUClient

    root = project_root or _project_root()
    specs = load_agents_spec(root)
    cfg = get_config()

    runtime_dir = (
        cfg.workspace.path
        / "_bench"
        / "validate-models"
        / datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    )
    client = ChatTCUClient(
        base_url=cfg.llm.chattcu_base_url,
        cycle_id="BENCH_VALIDATE_MODELS",
        runtime_dir=runtime_dir,
    )
    available_models = client.listar_modelos()
    model_ids: dict[str, dict[str, Any]] = {}
    for model in available_models:
        for key in ("name", "display_name", "id", "model_id"):
            value = model.get(key)
            if value:
                model_ids[str(value)] = model

    results = []
    for agent_id, spec in specs.items():
        found = model_ids.get(spec.modelo)
        results.append({
            "agent_id": agent_id,
            "modelo": spec.modelo,
            "available": bool(found),
            "display_name": found.get("display_name") if found else None,
            "fornecedora": found.get("fornecedora") if found else None,
        })
    return results


def _read_if_exists(path: Path) -> str:
    if path.is_file():
        return path.read_text(encoding="utf-8")
    return ""
