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

from diogenes.agents.contexto_metodologico import (
    carregar_corpus_juridico,
    carregar_metodologia_modulo,
)
from diogenes.agents.file_prep import (
    EXTENSOES_ANALISE,
    classificar,
    preparar_arquivo,
    rotulo_tipo,
)
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

# Teto de caracteres do manifesto de entrega exibido no preflight.
_MAX_CHARS_DELIVERY_MANIFEST = 6_000


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
        delivery_dir: Path | None = None,
        legal_corpus_dir: Path | None = None,
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
        # Pasta da entrega a varrer. Default: workspace/input/{module}; --delivery
        # permite apontar direto para um pacote preparado (ex: _teste_inputs/.../<data>).
        self._delivery_dir = Path(delivery_dir).expanduser().resolve() if delivery_dir else self._input_dir
        self._legal_corpus_dir = (
            Path(legal_corpus_dir).expanduser().resolve() if legal_corpus_dir else None
        )
        if not self._delivery_dir.is_dir():
            raise FileNotFoundError(
                f"Diretório de entrega não encontrado: {self._delivery_dir}"
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

        # Carrega o universo da entrega (cat. A+B+docs) via file_prep
        files = self._load_delivery()
        if self._limit and self._limit > 0:
            files = self._amostrar_por_tipo(files, self._limit)
        catalog_json = self._load_catalog()
        module_docs = self._load_module_docs()
        legal_corpus = self._load_legal_corpus()
        delivery_manifest = self._load_delivery_manifest()
        self._module_docs = module_docs
        self._legal_corpus = legal_corpus

        self._result.preflight = self._build_preflight(
            files, catalog_json, module_docs, legal_corpus, delivery_manifest
        )
        self._write_preflight()
        self._write_live_status("preflight", "completed")
        _log(f"📂 Entrega: {len(files)} arquivos carregados ({self._contagem_por_tipo(files)})")
        _log(self._format_pre_report("Preflight", self._result.preflight))

        # build_user_irene_catalog / inventário esperam pares (nome, conteúdo)
        files_2t = [(name, content) for name, _tipo, content in files]

        # Step 1: Irene (catalog via LLM)
        _log("\n━━━ Passo 1/8: Irene — Classificação de abas ━━━")
        irene_result = self._step_irene(files_2t, catalog_json)
        self._save_step("01_irene_catalog.md", irene_result, console_callback)

        # Step 2: Mycroft definir_tasks_watson
        _log("\n━━━ Passo 2/8: Mycroft — Definir tarefas Watson ━━━")
        tasks_result = self._step_mycroft_tasks(irene_result.response_text, files, module_docs)
        self._save_step("02_mycroft_tasks.md", tasks_result, console_callback)

        # Step 3: Watson análise por arquivo
        _log(f"\n━━━ Passo 3/8: Watson — Análise de {len(files)} arquivos ━━━")
        watson_analises = []
        for i, (filename, tipo, content) in enumerate(files, 1):
            _log(f"  [{i}/{len(files)}] {filename} ({tipo})")
            step = self._step_watson_analise(filename, content, tipo, i)
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

    def _step_mycroft_tasks(
        self,
        irene_output: str,
        files: list[tuple[str, str, str]],
        module_docs: str,
    ) -> StepResult:
        system = build_reduced_system("mycroft", "definir_tasks_watson")
        catalog_summary = "\n".join(
            f"- {name} [{tipo}] ({content.count(chr(10))} linhas)"
            for name, tipo, content in files
        )
        docs_resumo = module_docs[:4000] if module_docs else None
        user = build_user_mycroft_tasks(catalog_summary, self._module, docs_resumo)
        if irene_output:
            user += f"\n\n## Classificação Irene\n{irene_output[:3000]}"
        return self._call("mycroft_tasks", "mycroft", "definir_tasks_watson", system, user)

    def _step_watson_analise(self, filename: str, content: str, tipo: str, idx: int) -> StepResult:
        system = build_reduced_system("watson", "analise_inicial")
        user = build_user_watson_analise(filename, content, tipo)
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
        metodologia = getattr(self, "_module_docs", "") or None
        corpus = getattr(self, "_legal_corpus", "") or None
        user = build_user_sherlock(watson_consolidado, mycroft_decisao, metodologia, corpus)
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

    def _iter_arquivos_analise(self):
        """Itera arquivos da entrega elegíveis para análise (cat. A+B+docs)."""
        for p in sorted(self._delivery_dir.rglob("*")):
            if not p.is_file():
                continue
            analisavel, _tipo = classificar(p.relative_to(self._delivery_dir))
            if analisavel:
                yield p

    def _load_delivery(self) -> list[tuple[str, str, str]]:
        """Carrega o universo da entrega como (nome_relativo, tipo, texto).

        Usa file_prep.preparar_arquivo para converter cada arquivo (xlsx/sql/ipynb/pdf)
        ou ler texto (csv/md/py). Varre recursivamente respeitando allowlist de
        extensões e denylist de diretórios/arquivos de metadados.
        """
        arquivos: list[tuple[str, str, str]] = []
        for p in self._iter_arquivos_analise():
            rel = p.relative_to(self._delivery_dir).as_posix()
            tipo = rotulo_tipo(p.name)
            texto = preparar_arquivo(p)
            arquivos.append((rel, tipo, texto))
        if not arquivos:
            raise FileNotFoundError(
                f"Nenhum arquivo analisável encontrado em {self._delivery_dir} "
                f"(extensões aceitas: {sorted(EXTENSOES_ANALISE)})."
            )
        # Ordem: tipo (cadeia de produção) e depois nome.
        ordem_tipo = {"documento": 0, "sql": 1, "notebook": 2, "script": 3,
                      "esquema": 4, "planilha": 5, "csv": 6}
        arquivos.sort(key=lambda t: (ordem_tipo.get(t[1], 9), t[0]))
        return arquivos

    @staticmethod
    def _amostrar_por_tipo(
        files: list[tuple[str, str, str]], limit: int
    ) -> list[tuple[str, str, str]]:
        """Amostra até `limit` arquivos garantindo ≥1 de cada tipo (round-robin)."""
        if limit <= 0 or len(files) <= limit:
            return files[:limit] if limit > 0 else files
        por_tipo: dict[str, list[tuple[str, str, str]]] = {}
        for entry in files:
            por_tipo.setdefault(entry[1], []).append(entry)
        selecionados: list[tuple[str, str, str]] = []
        # round-robin entre os tipos até atingir o limite
        while len(selecionados) < limit and any(por_tipo.values()):
            for tipo in list(por_tipo.keys()):
                if por_tipo[tipo]:
                    selecionados.append(por_tipo[tipo].pop(0))
                    if len(selecionados) >= limit:
                        break
        # preserva a ordem original (cadeia de produção)
        selecionados_set = set(id(e) for e in selecionados)
        return [e for e in files if id(e) in selecionados_set]

    @staticmethod
    def _contagem_por_tipo(files: list[tuple[str, str, str]]) -> str:
        contagem: dict[str, int] = {}
        for _name, tipo, _content in files:
            contagem[tipo] = contagem.get(tipo, 0) + 1
        return ", ".join(f"{t}={n}" for t, n in sorted(contagem.items()))

    def _load_catalog(self) -> str | None:
        """Catálogo Irene (CATALOGO.json) — busca em todos os layouts conhecidos."""
        # Busca rglob primeiro: acha _CATALOGO/CATALOGO.json em qualquer subpasta da entrega
        for p in sorted(self._delivery_dir.rglob("CATALOGO.json")):
            return p.read_text(encoding="utf-8")
        for candidate in (
            self._delivery_dir / "CSV" / "_CATALOGO" / "CATALOGO.json",
            self._delivery_dir / "CSV" / "CATALOGO.json",
            self._input_dir / "CSV" / "CATALOGO.json",
        ):
            if candidate.is_file():
                return candidate.read_text(encoding="utf-8")
        return None

    def _load_module_docs(self) -> str:
        """Metodologia/RN do módulo (cat. C) — fonte única em contexto_metodologico."""
        return carregar_metodologia_modulo(self._delivery_dir)

    def _load_legal_corpus(self) -> str:
        """Recorte curado do arcabouço jurídico do módulo (cat. D) — fonte única."""
        return carregar_corpus_juridico(self._legal_corpus_dir, self._module)

    def _load_delivery_manifest(self) -> str:
        """Manifesto de entrega (cat. E): protocolo_recebimento / metadados, se houver."""
        partes: list[str] = []
        for nome in ("protocolo_recebimento.md", "metadados.json"):
            matches = sorted(self._delivery_dir.rglob(nome))
            if matches:
                texto = matches[0].read_text(encoding="utf-8", errors="replace")
                partes.append(f"### {nome}\n{texto}")
        manifesto = "\n\n".join(partes)
        return manifesto[:_MAX_CHARS_DELIVERY_MANIFEST]

    def _build_preflight(
        self,
        files: list[tuple[str, str, str]],
        catalog_json: str | None,
        module_docs: str = "",
        legal_corpus: str = "",
        delivery_manifest: str = "",
    ) -> dict[str, Any]:
        by_type: dict[str, int] = {}
        for _name, tipo, _content in files:
            by_type[tipo] = by_type.get(tipo, 0) + 1
        warnings: list[str] = []
        if module_docs == "":
            warnings.append("Documentação do módulo (cat. C) não encontrada — Sherlock sem metodologia.")
        if legal_corpus == "":
            warnings.append("Corpus jurídico (cat. D) ausente — informe --legal-corpus para validação metodológica plena.")
        return {
            "module": self._module,
            "input_dir": str(self._input_dir),
            "delivery_dir": str(self._delivery_dir),
            "legal_corpus_dir": str(self._legal_corpus_dir) if self._legal_corpus_dir else None,
            "profile": self._profile,
            "model_override": self._model_override,
            "timeout": self._timeout,
            "max_retries": self._max_retries,
            "sherlock_mode": self._sherlock_mode,
            "total_files": len(files),
            "by_type": by_type,
            # Mantidos para compatibilidade com _write_final_audit:
            "csv_count": by_type.get("csv", 0),
            "xlsx_count": by_type.get("planilha", 0),
            "catalog_present": catalog_json is not None,
            "module_docs_chars": len(module_docs),
            "legal_corpus_chars": len(legal_corpus),
            "delivery_manifest_present": bool(delivery_manifest),
            "files": [{"name": name, "tipo": tipo, "chars": len(content)} for name, tipo, content in files],
            "warnings": warnings,
        }

    def _write_preflight(self) -> None:
        preflight = self._result.preflight
        by_type = preflight.get("by_type", {})
        lines = [
            "# Preflight — Pipeline de Bancada",
            "",
            f"**Módulo:** {preflight['module']}",
            f"**Entrega:** {preflight['delivery_dir']}",
            f"**Corpus jurídico:** {preflight.get('legal_corpus_dir') or '(não fornecido)'}",
            f"**Perfil:** {preflight['profile']}",
            f"**Modelo override:** {preflight['model_override'] or '(agents_spec.yaml)'}",
            f"**Timeout:** {preflight['timeout']}s",
            f"**Retries:** {preflight['max_retries']}",
            f"**Modo Sherlock:** {preflight['sherlock_mode']}",
            f"**Total de arquivos:** {preflight['total_files']}",
            f"**Por tipo:** {', '.join(f'{t}={n}' for t, n in sorted(by_type.items())) or '—'}",
            f"**CATALOGO.json:** {'sim' if preflight['catalog_present'] else 'não'}",
            f"**Doc. módulo (cat. C):** {preflight['module_docs_chars']:,} chars",
            f"**Corpus jurídico (cat. D):** {preflight['legal_corpus_chars']:,} chars",
            f"**Manifesto de entrega:** {'sim' if preflight['delivery_manifest_present'] else 'não'}",
            "",
            "## Arquivos por análise",
            "",
        ]
        for item in preflight["files"]:
            lines.append(f"- [{item['tipo']}] {item['name']} ({item['chars']:,} chars)")
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
        by_type = preflight.get("by_type", {})
        tipos = ", ".join(f"{t}={n}" for t, n in sorted(by_type.items())) or "—"
        return (
            f"Pré-relatório — {label}: "
            f"{preflight['total_files']} arquivos ({tipos}), "
            f"doc_modulo={preflight['module_docs_chars']}c, "
            f"corpus_juridico={preflight['legal_corpus_chars']}c, "
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
            "# Auditoria — Pipeline de Bancada",
            "",
            f"**Pipeline:** {self._bench_id}",
            f"**Módulo:** {self._module}",
            f"**Início:** {self._result.started_at}",
            f"**Fim:** {self._result.finished_at}",
            f"**Duração total:** {self._result.total_duration_s:.1f}s",
            f"**Tokens input:** {self._result.total_prompt_tokens:,}",
            f"**Tokens output:** {self._result.total_completion_tokens:,}",
            f"**Status:** {'✅ Completo' if self._result.success else '⚠ Com erros'}",
            "",
            "## Passos",
            "",
            "| # | Passo | Agente | Modelo | Duração | Tokens | Status |",
            "|---|-------|--------|--------|---------|--------|--------|",
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
