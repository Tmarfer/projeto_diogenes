"""
tests/unit/test_bench_pipeline.py — DVA-CBS | Projeto Diógenes
Testes da bancada ponta a ponta com prompts reduzidos.
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from diogenes.bench.pipeline import BenchPipeline, resolve_bench_profile
from diogenes.models import LLMResponse


def _make_mod010_input(workspace: Path, module: str = "MOD010MCP3") -> None:
    mod = workspace / "input" / module
    csv_dir = mod / "CSV"
    xlsx_dir = mod / "XLSX"
    csv_dir.mkdir(parents=True)
    xlsx_dir.mkdir()
    (xlsx_dir / "AUX_MOD_10 PF - execução.xlsx").write_bytes(b"PK\x03\x04fake")
    for i in range(5):
        suffix = "" if i == 0 else f"_{i}"
        (csv_dir / f"aux_mod_10_pf_execucao__aux_mod_10{suffix}.csv").write_text(
            "id;valor\n1;10\n", encoding="utf-8"
        )
    (csv_dir / "CATALOGO.json").write_text('{"abas": 5}', encoding="utf-8")


def _response(call, content: str = "OK") -> LLMResponse:
    return LLMResponse(
        content=content,
        call_id=call.call_id,
        model_used=call.model,
        system_fingerprint="bench-test",
        prompt_tokens=10,
        completion_tokens=3,
        total_tokens=13,
        cost_usd=0.0,
        latency_ms=1,
        retry_attempts=0,
        http_status=200,
        finish_reason="stop",
    )


def test_resolve_stable_gpt54_profile():
    profile = resolve_bench_profile("stable-gpt54")

    assert profile.model_override == "gpt-5.4-thinking"
    assert profile.timeout == 600
    assert profile.max_retries == 2
    assert profile.sherlock_mode == "freeform_aux_only"


def test_resolve_stable_gpt55_profile():
    profile = resolve_bench_profile("stable-gpt55")

    assert profile.model_override == "gpt-5.5-thinking"
    assert profile.timeout == 600
    assert profile.max_retries == 2
    assert profile.sherlock_mode == "freeform_aux_only"


def test_pipeline_preflight_progress_retry_and_limitation(env_vars, workspace, tmp_path, monkeypatch):
    _make_mod010_input(workspace)
    calls: dict[str, int] = {}

    def _fake_complete(self, call):
        calls[call.call_id] = calls.get(call.call_id, 0) + 1
        if "watson_analise_01" in call.call_id and calls[call.call_id] == 1:
            raise RuntimeError("HTTP 500 transient")
        if "sherlock_validacao" in call.call_id:
            return _response(
                call,
                "Executado em modo reduzido. Há limitação por falta de insumos metodológicos.",
            )
        return _response(call)

    out_dir = tmp_path / "bench_run"
    monkeypatch.setattr("diogenes.bench.pipeline.time.sleep", lambda _seconds: None)
    with patch("diogenes.llm.chattcu.ChatTCUClient.complete", _fake_complete):
        result = BenchPipeline(
            "MOD010MCP3",
            profile="stable-gpt54",
            output_dir=out_dir,
            pre_report=True,
        ).run()

    assert result.api_success is True
    assert result.success is True
    assert result.has_limitations is True
    assert len(result.steps) == 12
    assert result.steps[2].attempts == 2
    assert {step.model for step in result.steps} == {"gpt-5.4-thinking"}

    assert (out_dir / "00_preflight.md").is_file()
    assert (out_dir / "_live_status.json").is_file()
    assert (out_dir / "AUDITORIA_BENCH_GPT54_RERUN.md").is_file()
    progress_files = sorted((out_dir / "progress").glob("*.md"))
    assert len(progress_files) == 12

    audit = json.loads((out_dir / "_audit.json").read_text(encoding="utf-8"))
    assert audit["profile"] == "stable-gpt54"
    assert audit["api_success"] is True
    assert audit["has_limitations"] is True
    assert audit["steps"][2]["attempts"] == 2


def test_pipeline_cli_accepts_stable_profile(env_vars, workspace, tmp_path):
    from typer.testing import CliRunner

    from diogenes.cli.app import app

    _make_mod010_input(workspace)

    def _fake_run(self, console_callback=None):
        from diogenes.bench.pipeline import PipelineResult

        return PipelineResult(
            module="MOD010MCP3",
            output_dir=tmp_path,
            profile="stable-gpt54",
            model_override="gpt-5.4-thinking",
            timeout=240,
            max_retries=2,
            success=True,
        )

    with patch("diogenes.bench.pipeline.BenchPipeline.run", _fake_run):
        result = CliRunner().invoke(
            app,
            [
                "bench",
                "pipeline",
                "MOD010MCP3",
                "--profile",
                "stable-gpt54",
                "--pre-report",
            ],
        )

    assert result.exit_code == 0
    assert "stable-gpt54" in result.stdout
