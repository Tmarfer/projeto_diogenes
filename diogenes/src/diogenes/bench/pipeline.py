"""
bench/pipeline.py — DVA-CBS | Projeto Diógenes
Pipeline de bancada ponta a ponta: Irene→Mycroft→Watson→Sherlock→Mycroft.

Executa todos os passos de um ciclo usando prompts REDUZIDOS (~12K system)
e salva outputs + auditoria em workspace/_bench/pipeline_<timestamp>/.

Não toca audit_index, Stranger's Room, nem estados do orquestrador.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from diogenes.bench.prompt_builder import (
    build_reduced_system,
    build_user_irene_catalog,
    build_user_mycroft_avaliar,
    build_user_mycroft_consolidar,
    build_user_mycroft_tasks,
    build_user_sherlock,
    build_user_watson_analise,
    build_user_watson_consolidar,
    get_model_for_agent,
)
from diogenes.config import get_config
from diogenes.llm.chattcu import ChatTCUClient
from diogenes.models import LLMCall, LLMMessage, LLMResponse


@dataclass
class StepResult:
    step_name: str
    agent: str
    call_type: str
    model: str
    success: bool
    response_text: str = ""
    error: str = ""
    duration_s: float = 0.0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    system_chars: int = 0
    user_chars: int = 0


@dataclass
class PipelineResult:
    module: str
    output_dir: Path
    started_at: str = ""
    finished_at: str = ""
    total_duration_s: float = 0.0
    steps: list[StepResult] = field(default_factory=list)
    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0
    success: bool = True


class BenchPipeline:
    """Pipeline de bancada completo para um módulo específico."""

    def __init__(
        self,
        module: str,
        model_override: str | None = None,
        timeout: int = 120,
        max_retries: int = 1,
        output_dir: Path | None = None,
    ):
        self._module = module
        self._model_override = model_override
        self._timeout = timeout
        self._max_retries = max_retries

        cfg = get_config()
        workspace = cfg.workspace.path

        self._input_dir = workspace / "input" / module
        if not self._input_dir.is_dir():
            raise FileNotFoundError(
                f"Diretório de input não encontrado: {self._input_dir}"
            )

        ts = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        self._output_dir = output_dir or (workspace / "_bench" / f"pipeline_{module}_{ts}")
        self._output_dir.mkdir(parents=True, exist_ok=True)

        self._bench_id = f"BENCH_PIPELINE_{module}_{ts}"
        self._client = ChatTCUClient(
            base_url=cfg.llm.chattcu_base_url,
            cycle_id=self._bench_id,
            runtime_dir=self._output_dir / "_runtime",
        )
        self._result = PipelineResult(
            module=module,
            output_dir=self._output_dir,
            started_at=datetime.now(UTC).isoformat(),
        )

    def run(self, console_callback=None) -> PipelineResult:
        """Executa pipeline completo. console_callback(msg) para log."""

        def _log(msg: str):
            if console_callback:
                console_callback(msg)

        t0 = time.time()

        # Load CSVs
        csvs = self._load_csvs()
        catalog_json = self._load_catalog()
        _log(f"📂 Input: {len(csvs)} CSVs carregados")

        # Step 1: Irene (catalog via LLM)
        _log("\n━━━ Passo 1/8: Irene — Classificação de abas ━━━")
        irene_result = self._step_irene(csvs, catalog_json)
        self._save_step("01_irene_catalog.md", irene_result)

        # Step 2: Mycroft definir_tasks_watson
        _log("\n━━━ Passo 2/8: Mycroft — Definir tarefas Watson ━━━")
        tasks_result = self._step_mycroft_tasks(irene_result.response_text, csvs)
        self._save_step("02_mycroft_tasks.md", tasks_result)

        # Step 3: Watson análise por arquivo
        _log(f"\n━━━ Passo 3/8: Watson — Análise de {len(csvs)} arquivos ━━━")
        watson_analises = []
        for i, (filename, content) in enumerate(csvs, 1):
            _log(f"  [{i}/{len(csvs)}] {filename}")
            step = self._step_watson_analise(filename, content, i)
            self._save_step(f"03_watson_{i:02d}_{filename[:40]}.md", step)
            watson_analises.append((filename, step.response_text if step.success else f"[ERRO: {step.error}]"))

        # Step 4: Watson consolidar
        _log("\n━━━ Passo 4/8: Watson — Consolidação ━━━")
        watson_consolidado = self._step_watson_consolidar(watson_analises)
        self._save_step("04_watson_consolidado.md", watson_consolidado)

        # Step 5: Mycroft avaliar_watson
        _log("\n━━━ Passo 5/8: Mycroft — Avaliar Watson ━━━")
        mycroft_watson = self._step_mycroft_avaliar(
            watson_consolidado.response_text, "Watson"
        )
        self._save_step("05_mycroft_decisao_watson.md", mycroft_watson)

        # Step 6: Sherlock validação
        _log("\n━━━ Passo 6/8: Sherlock — Validação metodológica ━━━")
        sherlock_result = self._step_sherlock(
            watson_consolidado.response_text,
            mycroft_watson.response_text,
        )
        self._save_step("06_sherlock_validacao.md", sherlock_result)

        # Step 7: Mycroft avaliar_sherlock
        _log("\n━━━ Passo 7/8: Mycroft — Avaliar Sherlock ━━━")
        mycroft_sherlock = self._step_mycroft_avaliar(
            sherlock_result.response_text, "Sherlock"
        )
        self._save_step("07_mycroft_decisao_sherlock.md", mycroft_sherlock)

        # Step 8: Mycroft consolidar
        _log("\n━━━ Passo 8/8: Mycroft — Consolidação final ━━━")
        final = self._step_mycroft_consolidar(
            watson_consolidado.response_text,
            sherlock_result.response_text,
            mycroft_watson.response_text,
            mycroft_sherlock.response_text,
        )
        self._save_step("08_relatorio_final.md", final)

        # Finalize
        self._result.finished_at = datetime.now(UTC).isoformat()
        self._result.total_duration_s = time.time() - t0
        self._result.total_prompt_tokens = sum(s.prompt_tokens for s in self._result.steps)
        self._result.total_completion_tokens = sum(s.completion_tokens for s in self._result.steps)
        self._result.success = all(s.success for s in self._result.steps)

        # Write audit
        self._write_audit()
        _log(f"\n✅ Pipeline concluído em {self._result.total_duration_s:.1f}s")
        _log(f"📁 Output: {self._output_dir}")

        return self._result

    # ── Steps ────────────────────────────────────────────────────────────────

    def _step_irene(self, csvs: list[tuple[str, str]], catalog_json: str | None) -> StepResult:
        system = build_reduced_system("mycroft", "definir_tasks_watson")
        user = build_user_irene_catalog(csvs, catalog_json)
        return self._call("irene_catalog", "mycroft", "definir_tasks_watson", system, user)

    def _step_mycroft_tasks(self, irene_output: str, csvs: list[tuple[str, str]]) -> StepResult:
        system = build_reduced_system("mycroft", "definir_tasks_watson")
        catalog_summary = "\n".join(f"- {name} ({content.count(chr(10))} linhas)" for name, content in csvs)
        user = build_user_mycroft_tasks(catalog_summary, self._module)
        if irene_output:
            user += f"\n\n## Classificação Irene\n{irene_output[:3000]}"
        return self._call("mycroft_tasks", "mycroft", "definir_tasks_watson", system, user)

    def _step_watson_analise(self, filename: str, csv_content: str, idx: int) -> StepResult:
        system = build_reduced_system("watson", "analise_inicial")
        user = build_user_watson_analise(filename, csv_content)
        return self._call(f"watson_analise_{idx:02d}", "watson", "analise_inicial", system, user)

    def _step_watson_consolidar(self, analises: list[tuple[str, str]]) -> StepResult:
        system = build_reduced_system("watson", "consolidar_watson")
        user = build_user_watson_consolidar(analises)
        return self._call("watson_consolidar", "watson", "consolidar_watson", system, user)

    def _step_mycroft_avaliar(self, agent_output: str, agent_name: str) -> StepResult:
        system = build_reduced_system("mycroft", "avaliar_agente")
        user = build_user_mycroft_avaliar(agent_output, agent_name)
        call_type_suffix = agent_name.lower()
        return self._call(f"mycroft_avaliar_{call_type_suffix}", "mycroft", "avaliar_agente", system, user)

    def _step_sherlock(self, watson_consolidado: str, mycroft_decisao: str) -> StepResult:
        system = build_reduced_system("sherlock", "validacao_inicial")
        user = build_user_sherlock(watson_consolidado, mycroft_decisao)
        return self._call("sherlock_validacao", "sherlock", "validacao_inicial", system, user)

    def _step_mycroft_consolidar(
        self,
        watson_consolidado: str,
        sherlock_validacao: str,
        mycroft_decisao_watson: str,
        mycroft_decisao_sherlock: str,
    ) -> StepResult:
        system = build_reduced_system("mycroft", "consolidar")
        user = build_user_mycroft_consolidar(
            watson_consolidado, sherlock_validacao,
            mycroft_decisao_watson, mycroft_decisao_sherlock,
        )
        return self._call("mycroft_consolidar", "mycroft", "consolidar", system, user)

    # ── Core call ────────────────────────────────────────────────────────────

    def _call(
        self,
        step_name: str,
        agent: str,
        call_type: str,
        system_prompt: str,
        user_prompt: str,
    ) -> StepResult:
        model = get_model_for_agent(agent, self._model_override)
        result = StepResult(
            step_name=step_name,
            agent=agent,
            call_type=call_type,
            model=model,
            success=False,
            system_chars=len(system_prompt),
            user_chars=len(user_prompt),
        )

        llm_call = LLMCall(
            call_id=f"{self._bench_id}_{step_name}",
            cycle_id=self._bench_id,
            phase="bench_pipeline",
            agent=agent,
            call_type=call_type,
            model=model,
            temperature=0.0,
            max_tokens=8000,
            seed=42,
            raciocinio=True,
            messages=[
                LLMMessage(role="system", content=system_prompt),
                LLMMessage(role="user", content=user_prompt),
            ],
            timeout_segundos=self._timeout,
            max_tentativas_retry=self._max_retries,
            backoff_segundos=10,
        )

        t0 = time.time()
        try:
            resp: LLMResponse = self._client.complete(llm_call)
            result.duration_s = time.time() - t0
            result.response_text = resp.content
            result.prompt_tokens = resp.prompt_tokens
            result.completion_tokens = resp.completion_tokens
            result.success = True
        except Exception as exc:
            result.duration_s = time.time() - t0
            result.error = str(exc)[:500]
            result.response_text = f"[ERRO no passo {step_name}]: {result.error}"

        self._result.steps.append(result)
        return result

    # ── I/O ──────────────────────────────────────────────────────────────────

    def _load_csvs(self) -> list[tuple[str, str]]:
        csv_dir = self._input_dir / "CSV"
        if not csv_dir.is_dir():
            raise FileNotFoundError(f"CSV dir not found: {csv_dir}")
        csvs: list[tuple[str, str]] = []
        for p in sorted(csv_dir.glob("*.csv")):
            csvs.append((p.name, p.read_text(encoding="utf-8", errors="replace")))
        return csvs

    def _load_catalog(self) -> str | None:
        catalog_path = self._input_dir / "CSV" / "CATALOGO.json"
        if catalog_path.is_file():
            return catalog_path.read_text(encoding="utf-8")
        return None

    def _save_step(self, filename: str, result: StepResult) -> None:
        safe_name = "".join(c if c.isalnum() or c in "._-" else "_" for c in filename)
        out_path = self._output_dir / safe_name
        content = result.response_text if result.success else f"# ERRO\n\n{result.error}"
        out_path.write_text(content, encoding="utf-8")

    def _write_audit(self) -> None:
        audit: dict[str, Any] = {
            "pipeline_id": self._bench_id,
            "module": self._module,
            "started_at": self._result.started_at,
            "finished_at": self._result.finished_at,
            "total_duration_s": round(self._result.total_duration_s, 1),
            "total_prompt_tokens": self._result.total_prompt_tokens,
            "total_completion_tokens": self._result.total_completion_tokens,
            "all_success": self._result.success,
            "steps": [],
        }
        for step in self._result.steps:
            audit["steps"].append({
                "name": step.step_name,
                "agent": step.agent,
                "call_type": step.call_type,
                "model": step.model,
                "success": step.success,
                "duration_s": round(step.duration_s, 1),
                "prompt_tokens": step.prompt_tokens,
                "completion_tokens": step.completion_tokens,
                "system_chars": step.system_chars,
                "user_chars": step.user_chars,
                "error": step.error or None,
                "response_length": len(step.response_text),
            })

        (self._output_dir / "_audit.json").write_text(
            json.dumps(audit, indent=2, ensure_ascii=False), encoding="utf-8"
        )

        # Human-readable report
        lines = [
            f"# Auditoria — Pipeline de Bancada",
            f"",
            f"**Pipeline:** {self._bench_id}",
            f"**Módulo:** {self._module}",
            f"**Início:** {self._result.started_at}",
            f"**Fim:** {self._result.finished_at}",
            f"**Duração total:** {self._result.total_duration_s:.1f}s",
            f"**Tokens input:** {self._result.total_prompt_tokens:,}",
            f"**Tokens output:** {self._result.total_completion_tokens:,}",
            f"**Status:** {'✅ Completo' if self._result.success else '⚠ Com erros'}",
            f"",
            f"## Passos",
            f"",
            f"| # | Passo | Agente | Modelo | Duração | Tokens | Status |",
            f"|---|-------|--------|--------|---------|--------|--------|",
        ]
        for i, step in enumerate(self._result.steps, 1):
            status = "✅" if step.success else f"❌ {step.error[:30]}"
            tokens = f"{step.prompt_tokens}+{step.completion_tokens}"
            lines.append(
                f"| {i} | {step.step_name} | {step.agent} | {step.model} | "
                f"{step.duration_s:.1f}s | {tokens} | {status} |"
            )

        # Errors section
        errors = [s for s in self._result.steps if not s.success]
        if errors:
            lines.append(f"\n## Erros ({len(errors)})")
            for s in errors:
                lines.append(f"\n### {s.step_name}")
                lines.append(f"```\n{s.error}\n```")

        lines.append(f"\n---\n*Gerado em {datetime.now(UTC).isoformat()}*")

        (self._output_dir / "_audit_report.md").write_text(
            "\n".join(lines), encoding="utf-8"
        )
