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


@dataclass(frozen=True)
class BenchProfile:
    name: str
    model_override: str | None = None
    timeout: int = 120
    max_retries: int = 1
    sherlock_mode: str = "protocolar"


BENCH_PROFILES: dict[str, BenchProfile] = {
    "default": BenchProfile(name="default"),
    "stable-gpt54": BenchProfile(
        name="stable-gpt54",
        model_override="gpt-5.4-thinking",
        timeout=600,
        max_retries=2,
        sherlock_mode="freeform_aux_only",
    ),
    "stable-gpt55": BenchProfile(
        name="stable-gpt55",
        model_override="gpt-5.5-thinking",
        timeout=600,
        max_retries=2,
        sherlock_mode="freeform_aux_only",
    ),
}


@dataclass
class StepResult:
    step_name: str
    agent: str
    call_type: str
    model: str
    success: bool
    api_success: bool = False
    semantic_status: str = "pending"
    blocking: bool = False
    attempts: int = 0
    output_path: str = ""
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
    profile: str = "default"
    model_override: str | None = None
    timeout: int = 120
    max_retries: int = 1
    sherlock_mode: str = "protocolar"
    started_at: str = ""
    finished_at: str = ""
    total_duration_s: float = 0.0
    steps: list[StepResult] = field(default_factory=list)
    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0
    success: bool = True
    api_success: bool = True
    has_limitations: bool = False
    preflight: dict[str, Any] = field(default_factory=dict)


def resolve_bench_profile(profile: str | None) -> BenchProfile:
    """Resolve perfil de bancada por nome."""
    profile_name = profile or "default"
    if profile_name not in BENCH_PROFILES:
        known = ", ".join(sorted(BENCH_PROFILES))
        raise ValueError(f"Perfil de bancada desconhecido: {profile_name}. Opções: {known}")
    return BENCH_PROFILES[profile_name]


class BenchPipeline:
    """Pipeline de bancada completo para um módulo específico."""

    def __init__(
        self,
        module: str,
        model_override: str | None = None,
        timeout: int | None = None,
        max_retries: int | None = None,
        profile: str | None = None,
        pre_report: bool = False,
        sherlock_mode: str | None = None,
        output_dir: Path | None = None,
        limit: int | None = None,
    ):
        bench_profile = resolve_bench_profile(profile)
        self._module = module
        self._profile = bench_profile.name
        self._model_override = model_override or bench_profile.model_override
        self._timeout = timeout if timeout is not None else bench_profile.timeout
        self._max_retries = max_retries if max_retries is not None else bench_profile.max_retries
        self._pre_report = pre_report
        self._sherlock_mode = sherlock_mode or bench_profile.sherlock_mode
        self._limit = limit

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
            profile=self._profile,
            model_override=self._model_override,
            timeout=self._timeout,
            max_retries=self._max_retries,
            sherlock_mode=self._sherlock_mode,
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
        if self._limit and self._limit > 0:
            csvs = csvs[:self._limit]
        catalog_json = self._load_catalog()
        self._result.preflight = self._build_preflight(csvs, catalog_json)
        self._write_preflight()
        self._write_live_status("preflight", "completed")
        _log(f"📂 Input: {len(csvs)} CSVs carregados")
        _log(self._format_pre_report("Preflight", self._result.preflight))

        # Step 1: Irene (catalog via LLM)
        _log("\n━━━ Passo 1/8: Irene — Classificação de abas ━━━")
        irene_result = self._step_irene(csvs, catalog_json)
        self._save_step("01_irene_catalog.md", irene_result, console_callback)

        # Step 2: Mycroft definir_tasks_watson
        _log("\n━━━ Passo 2/8: Mycroft — Definir tarefas Watson ━━━")
        tasks_result = self._step_mycroft_tasks(irene_result.response_text, csvs)
        self._save_step("02_mycroft_tasks.md", tasks_result, console_callback)

        # Step 3: Watson análise por arquivo
        _log(f"\n━━━ Passo 3/8: Watson — Análise de {len(csvs)} arquivos ━━━")
        watson_analises = []
        for i, (filename, content) in enumerate(csvs, 1):
            _log(f"  [{i}/{len(csvs)}] {filename}")
            step = self._step_watson_analise(filename, content, i)
            self._save_step(f"03_watson_{i:02d}_{filename[:40]}.md", step, console_callback)
            watson_analises.append((filename, step.response_text if step.success else f"[ERRO: {step.error}]"))

        # Step 4: Watson consolidar
        _log("\n━━━ Passo 4/8: Watson — Consolidação ━━━")
        watson_consolidado = self._step_watson_consolidar(watson_analises)
        self._save_step("04_watson_consolidado.md", watson_consolidado, console_callback)

        # Step 5: Mycroft avaliar_watson
        _log("\n━━━ Passo 5/8: Mycroft — Avaliar Watson ━━━")
        mycroft_watson = self._step_mycroft_avaliar(
            watson_consolidado.response_text, "Watson"
        )
        self._save_step("05_mycroft_decisao_watson.md", mycroft_watson, console_callback)

        # Step 6: Sherlock validação
        _log(f"\n━━━ Passo 6/8: Sherlock — Validação metodológica ({self._sherlock_mode}) ━━━")
        sherlock_result = self._step_sherlock(
            watson_consolidado.response_text,
            mycroft_watson.response_text,
        )
        self._save_step("06_sherlock_validacao.md", sherlock_result, console_callback)

        # Step 7: Mycroft avaliar_sherlock
        _log("\n━━━ Passo 7/8: Mycroft — Avaliar Sherlock ━━━")
        mycroft_sherlock = self._step_mycroft_avaliar(
            sherlock_result.response_text, "Sherlock"
        )
        self._save_step("07_mycroft_decisao_sherlock.md", mycroft_sherlock, console_callback)

        # Step 8: Mycroft consolidar
        _log("\n━━━ Passo 8/8: Mycroft — Consolidação final ━━━")
        final = self._step_mycroft_consolidar(
            watson_consolidado.response_text,
            sherlock_result.response_text,
            mycroft_watson.response_text,
            mycroft_sherlock.response_text,
        )
        self._save_step("08_relatorio_final.md", final, console_callback)

        # Finalize
        self._result.finished_at = datetime.now(UTC).isoformat()
        self._result.total_duration_s = time.time() - t0
        self._result.total_prompt_tokens = sum(s.prompt_tokens for s in self._result.steps)
        self._result.total_completion_tokens = sum(s.completion_tokens for s in self._result.steps)
        self._result.api_success = all(s.api_success for s in self._result.steps)
        self._result.has_limitations = any(s.semantic_status == "limited" for s in self._result.steps)
        self._result.success = self._result.api_success and not any(s.blocking for s in self._result.steps)

        # Write audit
        self._write_audit()
        self._write_final_audit()
        self._write_live_status("pipeline", "finished")
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
        if self._sherlock_mode == "freeform_aux_only":
            user = (
                "# Modo de bancada: sherlock_freeform_aux_only\n\n"
                "Valide o pacote abaixo como recorte reduzido AUX-only. "
                "Quando faltarem insumos metodológicos protocolarmente exigidos, "
                "registre a limitação explicitamente e avance com achados possíveis, "
                "sem tratar a validação como substituta do Sherlock oficial.\n\n"
                f"{user}"
            )
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
            max_tentativas_retry=1,
            backoff_segundos=0,
        )

        attempts_total = self._max_retries + 1
        t0 = time.time()
        errors: list[str] = []
        for attempt in range(1, attempts_total + 1):
            result.attempts = attempt
            try:
                resp: LLMResponse = self._client.complete(llm_call)
                result.response_text = resp.content
                result.prompt_tokens = resp.prompt_tokens
                result.completion_tokens = resp.completion_tokens
                result.api_success = True
                result.semantic_status = self._semantic_status(step_name, resp.content)
                result.blocking = self._is_blocking(step_name, result.semantic_status)
                result.success = True
                break
            except Exception as exc:
                errors.append(str(exc)[:500])
                if attempt < attempts_total:
                    time.sleep(min(10, attempt * 2))
                    continue
                result.error = " | ".join(errors)
                result.response_text = f"[ERRO no passo {step_name}]: {result.error}"
                result.semantic_status = "api_error"
                result.blocking = True
        result.duration_s = time.time() - t0

        self._result.steps.append(result)
        self._write_live_status(step_name, "completed")
        return result

    def _semantic_status(self, step_name: str, text: str) -> str:
        lowered = text.lower()
        limitation_markers = (
            "não é possível classificar",
            "nao e possivel classificar",
            "não substitui",
            "nao substitui",
            "insumos metodológicos",
            "insumos metodologicos",
            "limitação",
            "limitacao",
        )
        if step_name == "sherlock_validacao" and any(m in lowered for m in limitation_markers):
            return "limited"
        return "ok"

    def _is_blocking(self, step_name: str, semantic_status: str) -> bool:
        if semantic_status == "api_error":
            return True
        if step_name == "sherlock_validacao" and semantic_status == "limited":
            return False
        return False

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

    def _build_preflight(
        self,
        csvs: list[tuple[str, str]],
        catalog_json: str | None,
    ) -> dict[str, Any]:
        xlsx_dir = self._input_dir / "XLSX"
        xlsx_files = sorted(xlsx_dir.glob("*.xlsx")) if xlsx_dir.is_dir() else []
        csv_dir = self._input_dir / "CSV"
        csv_files = sorted(csv_dir.glob("*.csv")) if csv_dir.is_dir() else []
        warnings: list[str] = []
        module_normalized = self._module.upper().replace("_", "")
        if module_normalized.startswith("MOD010") and len(csvs) != 5:
            warnings.append(f"Esperados 5 CSVs para AUX_MOD_10; encontrados {len(csvs)}.")
        if module_normalized.startswith("MOD010") and len(xlsx_files) != 1:
            warnings.append(f"Esperada 1 planilha AUX_MOD_10; encontradas {len(xlsx_files)}.")
        return {
            "module": self._module,
            "input_dir": str(self._input_dir),
            "profile": self._profile,
            "model_override": self._model_override,
            "timeout": self._timeout,
            "max_retries": self._max_retries,
            "sherlock_mode": self._sherlock_mode,
            "csv_count": len(csvs),
            "xlsx_count": len(xlsx_files),
            "catalog_present": catalog_json is not None,
            "csv_files": [
                {
                    "name": p.name,
                    "size_bytes": p.stat().st_size,
                    "lines": content.count("\n"),
                }
                for p, (_, content) in zip(csv_files, csvs, strict=False)
            ],
            "xlsx_files": [
                {"name": p.name, "size_bytes": p.stat().st_size}
                for p in xlsx_files
            ],
            "warnings": warnings,
        }

    def _write_preflight(self) -> None:
        preflight = self._result.preflight
        lines = [
            "# Preflight — Pipeline de Bancada",
            "",
            f"**Módulo:** {preflight['module']}",
            f"**Perfil:** {preflight['profile']}",
            f"**Modelo override:** {preflight['model_override'] or '(agents_spec.yaml)'}",
            f"**Timeout:** {preflight['timeout']}s",
            f"**Retries:** {preflight['max_retries']}",
            f"**Modo Sherlock:** {preflight['sherlock_mode']}",
            f"**CSVs:** {preflight['csv_count']}",
            f"**XLSX:** {preflight['xlsx_count']}",
            f"**CATALOGO.json:** {'sim' if preflight['catalog_present'] else 'não'}",
            "",
            "## Arquivos XLSX",
            "",
        ]
        for item in preflight["xlsx_files"]:
            lines.append(f"- {item['name']} ({item['size_bytes']} bytes)")
        lines.extend(["", "## Arquivos CSV", ""])
        for item in preflight["csv_files"]:
            lines.append(f"- {item['name']} ({item['lines']} linhas, {item['size_bytes']} bytes)")
        if preflight["warnings"]:
            lines.extend(["", "## Avisos", ""])
            for warning in preflight["warnings"]:
                lines.append(f"- {warning}")
        (self._output_dir / "00_preflight.md").write_text("\n".join(lines), encoding="utf-8")

    def _save_step(self, filename: str, result: StepResult, console_callback=None) -> None:
        safe_name = "".join(c if c.isalnum() or c in "._-" else "_" for c in filename)
        out_path = self._output_dir / safe_name
        content = result.response_text if result.success else f"# ERRO\n\n{result.error}"
        out_path.write_text(content, encoding="utf-8")
        result.output_path = str(out_path)
        self._write_progress_report(result)
        self._write_live_status(result.step_name, "saved")
        if self._pre_report and console_callback:
            console_callback(self._format_step_pre_report(result))

    def _write_progress_report(self, result: StepResult) -> None:
        progress_dir = self._output_dir / "progress"
        progress_dir.mkdir(parents=True, exist_ok=True)
        idx = len(self._result.steps)
        status = "OK" if result.api_success else "ERRO"
        if result.semantic_status == "limited":
            status = "LIMITADO"
        lines = [
            f"# Pré-relatório {idx:02d} — {result.step_name}",
            "",
            f"**Agente:** {result.agent}",
            f"**Call type:** {result.call_type}",
            f"**Modelo:** {result.model}",
            f"**Status API:** {'OK' if result.api_success else 'ERRO'}",
            f"**Status semântico:** {result.semantic_status}",
            f"**Bloqueante:** {'sim' if result.blocking else 'não'}",
            f"**Tentativas:** {result.attempts}",
            f"**Duração:** {result.duration_s:.1f}s",
            f"**Tokens:** {result.prompt_tokens:,} input + {result.completion_tokens:,} output",
            f"**Arquivo:** {result.output_path}",
            "",
            "## Erro",
            "",
            result.error or "(nenhum)",
        ]
        filename = f"{idx:02d}_{result.step_name}_{status.lower()}.md"
        (progress_dir / filename).write_text("\n".join(lines), encoding="utf-8")

    def _write_live_status(self, current_step: str, state: str) -> None:
        payload = {
            "pipeline_id": self._bench_id,
            "module": self._module,
            "profile": self._profile,
            "current_step": current_step,
            "state": state,
            "updated_at": datetime.now(UTC).isoformat(),
            "output_dir": str(self._output_dir),
            "steps_done": len(self._result.steps),
            "steps": [
                {
                    "name": s.step_name,
                    "agent": s.agent,
                    "model": s.model,
                    "api_success": s.api_success,
                    "semantic_status": s.semantic_status,
                    "blocking": s.blocking,
                    "attempts": s.attempts,
                    "duration_s": round(s.duration_s, 1),
                    "error": s.error or None,
                    "output_path": s.output_path or None,
                }
                for s in self._result.steps
            ],
        }
        (self._output_dir / "_live_status.json").write_text(
            json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    def _format_pre_report(self, label: str, preflight: dict[str, Any]) -> str:
        warnings = len(preflight.get("warnings") or [])
        return (
            f"Pré-relatório — {label}: "
            f"{preflight['csv_count']} CSVs, {preflight['xlsx_count']} XLSX, "
            f"perfil={preflight['profile']}, modelo={preflight['model_override'] or 'spec'}, "
            f"avisos={warnings}"
        )

    def _format_step_pre_report(self, result: StepResult) -> str:
        status = "OK" if result.api_success else "ERRO"
        if result.semantic_status == "limited":
            status = "LIMITADO"
        return (
            f"Pré-relatório — {result.step_name}: {status} | "
            f"{result.duration_s:.1f}s | tentativas={result.attempts} | "
            f"tokens={result.prompt_tokens:,}+{result.completion_tokens:,}"
        )

    def _write_audit(self) -> None:
        audit: dict[str, Any] = {
            "pipeline_id": self._bench_id,
            "module": self._module,
            "profile": self._profile,
            "model_override": self._model_override,
            "timeout": self._timeout,
            "max_retries": self._max_retries,
            "sherlock_mode": self._sherlock_mode,
            "started_at": self._result.started_at,
            "finished_at": self._result.finished_at,
            "total_duration_s": round(self._result.total_duration_s, 1),
            "total_prompt_tokens": self._result.total_prompt_tokens,
            "total_completion_tokens": self._result.total_completion_tokens,
            "all_success": self._result.success,
            "api_success": self._result.api_success,
            "has_limitations": self._result.has_limitations,
            "preflight": self._result.preflight,
            "steps": [],
        }
        for step in self._result.steps:
            audit["steps"].append({
                "name": step.step_name,
                "agent": step.agent,
                "call_type": step.call_type,
                "model": step.model,
                "success": step.success,
                "api_success": step.api_success,
                "semantic_status": step.semantic_status,
                "blocking": step.blocking,
                "attempts": step.attempts,
                "duration_s": round(step.duration_s, 1),
                "prompt_tokens": step.prompt_tokens,
                "completion_tokens": step.completion_tokens,
                "system_chars": step.system_chars,
                "user_chars": step.user_chars,
                "error": step.error or None,
                "response_length": len(step.response_text),
                "output_path": step.output_path or None,
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
            status = "✅" if step.api_success else f"❌ {step.error[:30]}"
            if step.semantic_status == "limited":
                status = "⚠ limitado"
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

    def _write_final_audit(self) -> None:
        baseline = self._find_baseline_audit()
        lines = [
            "# AUDITORIA BENCH GPT-5.4 RERUN",
            "",
            f"**Pipeline:** {self._bench_id}",
            f"**Módulo:** {self._module}",
            f"**Perfil:** {self._profile}",
            f"**Modelo:** {self._model_override or '(agents_spec.yaml)'}",
            f"**Sherlock:** {self._sherlock_mode}",
            f"**Status API:** {'100% OK' if self._result.api_success else 'com falhas'}",
            f"**Status semântico:** {'com limitações' if self._result.has_limitations else 'sem limitações detectadas'}",
            f"**Duração:** {self._result.total_duration_s:.1f}s",
            f"**Tokens:** {self._result.total_prompt_tokens:,} input + {self._result.total_completion_tokens:,} output",
            "",
            "## Baseline",
            "",
        ]
        if baseline:
            lines.append(f"Baseline localizado: `{baseline}`.")
        else:
            lines.append("Baseline `AUDITORIA_BENCH_GPT54.md` não localizado para comparação automática.")

        lines.extend([
            "",
            "## Escopo",
            "",
            f"- XLSX: {self._result.preflight.get('xlsx_count', 0)}",
            f"- CSVs: {self._result.preflight.get('csv_count', 0)}",
            f"- CATALOGO.json: {'sim' if self._result.preflight.get('catalog_present') else 'não'}",
            "",
            "## Etapas",
            "",
            "| # | Etapa | Agente | Status API | Status semântico | Tentativas | Duração | Tokens |",
            "|---|-------|--------|------------|------------------|------------|---------|--------|",
        ])
        for i, step in enumerate(self._result.steps, 1):
            lines.append(
                f"| {i} | {step.step_name} | {step.agent} | "
                f"{'OK' if step.api_success else 'ERRO'} | {step.semantic_status} | "
                f"{step.attempts} | {step.duration_s:.1f}s | "
                f"{step.prompt_tokens:,}+{step.completion_tokens:,} |"
            )

        limitations = [s for s in self._result.steps if s.semantic_status == "limited"]
        if limitations:
            lines.extend(["", "## Limitações Catalogadas", ""])
            for step in limitations:
                lines.append(
                    f"- `{step.step_name}` executou, mas indicou limitação metodológica; "
                    "não tratar como validação protocolar plena."
                )

        errors = [s for s in self._result.steps if not s.api_success]
        if errors:
            lines.extend(["", "## Erros", ""])
            for step in errors:
                lines.append(f"- `{step.step_name}`: {step.error}")

        lines.extend([
            "",
            "## Próximos Ajustes",
            "",
            "- Repetir a bancada após cada ajuste de prompt/modelo para comparar com este rerun.",
            "- Se Sherlock precisar validação protocolar, fornecer pacote metodológico mínimo do módulo.",
            "- Manter `stable-gpt54` como perfil de confiabilidade da bancada até novo benchmark superior.",
            "",
            f"*Gerado em {datetime.now(UTC).isoformat()}*",
        ])
        (self._output_dir / "AUDITORIA_BENCH_GPT54_RERUN.md").write_text(
            "\n".join(lines), encoding="utf-8"
        )

    def _find_baseline_audit(self) -> str | None:
        bench_root = self._output_dir.parent
        matches = sorted(bench_root.glob("pipeline_*/AUDITORIA_BENCH_GPT54.md"))
        return str(matches[-1]) if matches else None
