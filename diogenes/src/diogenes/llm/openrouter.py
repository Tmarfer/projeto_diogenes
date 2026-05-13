"""
llm/openrouter.py — DVA-CBS | Projeto Diógenes
OpenRouterClient — implementação concreta do LLMClient para o piloto local.

Usa o openai SDK com base_url configurável (SDD Bloco 1.2.4).
Referência normativa: Bloco 6.4 (SDD v0.1)
"""
from __future__ import annotations

import hashlib
import json
import time
from datetime import UTC, datetime
from pathlib import Path

import httpx
from openai import APIConnectionError, APIStatusError, APITimeoutError, OpenAI, RateLimitError

from diogenes.config import DiogenesConfig
from diogenes.llm.exceptions import LLMCallError, LLMCostLimitError, LLMTimeoutError
from diogenes.models import LLMCall, LLMResponse


class OpenRouterClient:
    def __init__(self, cfg: DiogenesConfig, cycle_id: str, runtime_dir: Path) -> None:
        self._cfg = cfg
        self._cycle_id = cycle_id
        self._llm_calls_dir = runtime_dir / "llm_calls"
        self._llm_calls_dir.mkdir(parents=True, exist_ok=True)
        self._custo_acumulado_usd: float = 0.0
        self._client = OpenAI(
            api_key=cfg.llm.api_key,
            base_url=cfg.llm.base_url,
            default_headers={
                "HTTP-Referer": cfg.llm.openrouter_site_url,
                "X-Title": cfg.llm.openrouter_app_name,
            },
            timeout=None,
            http_client=httpx.Client(verify=cfg.llm.ssl_verify),
        )

    def complete(self, call: LLMCall) -> LLMResponse:
        # Verificar teto de custo (0.0 = sem limite — fase A free)
        teto = self._cfg.agentes.teto_custo_ciclo_usd
        if teto > 0.0 and self._custo_acumulado_usd >= teto:
            raise LLMCostLimitError(
                f"Teto de custo atingido: USD {self._custo_acumulado_usd:.4f} "
                f">= USD {teto:.2f}."
            )

        last_exc: Exception | None = None
        attempt = 0
        while attempt <= call.max_tentativas_retry:
            t0 = time.monotonic()
            try:
                raw = self._client.chat.completions.create(
                    model=call.model,
                    messages=[{"role": m.role, "content": m.content} for m in call.messages],
                    temperature=call.temperature,
                    max_tokens=call.max_tokens,
                    seed=call.seed,
                    timeout=call.timeout_segundos,
                )
                latency_ms = int((time.monotonic() - t0) * 1000)
                content = raw.choices[0].message.content or ""
                usage = raw.usage
                cost = self._calcular_custo(call.model, usage.prompt_tokens, usage.completion_tokens)
                self._custo_acumulado_usd += cost

                resp = LLMResponse(
                    content=content,
                    call_id=call.call_id,
                    model_used=raw.model,
                    system_fingerprint=getattr(raw, "system_fingerprint", None),
                    prompt_tokens=usage.prompt_tokens,
                    completion_tokens=usage.completion_tokens,
                    total_tokens=usage.total_tokens,
                    cost_usd=cost,
                    latency_ms=latency_ms,
                    retry_attempts=attempt,
                    http_status=200,
                )
                self._persistir_trace(call, resp, 200)
                return resp

            except APITimeoutError as exc:
                last_exc = exc
                self._persistir_trace_falha(call, attempt, "TIMEOUT", str(exc))
                if attempt >= call.max_tentativas_retry:
                    raise LLMTimeoutError(
                        f"Timeout após {attempt+1} tentativa(s) em {call.call_id}."
                    ) from exc

            except RateLimitError as exc:
                last_exc = exc
                self._persistir_trace_falha(call, attempt, "RATE_LIMIT", str(exc))
                if attempt >= call.max_tentativas_retry:
                    raise LLMCallError(
                        f"Rate limit após {attempt+1} tentativa(s) em {call.call_id}."
                    ) from exc

            except APIConnectionError as exc:
                last_exc = exc
                self._persistir_trace_falha(call, attempt, "CONNECTION_ERROR", str(exc))
                if attempt >= call.max_tentativas_retry:
                    raise LLMCallError(
                        f"Erro de conexão persistente em {call.call_id}."
                    ) from exc

            except APIStatusError as exc:
                self._persistir_trace_falha(call, attempt, f"HTTP_{exc.status_code}", str(exc))
                if exc.status_code < 500:
                    raise LLMCallError(
                        f"Erro HTTP {exc.status_code} em {call.call_id}: {exc.message}"
                    ) from exc
                if attempt >= call.max_tentativas_retry:
                    raise LLMCallError(
                        f"Erro 5xx persistente após {attempt+1} tentativa(s) em {call.call_id}."
                    ) from exc

            attempt += 1
            time.sleep(call.backoff_segundos * attempt)

        raise LLMCallError(f"Falha inesperada em {call.call_id}.") from last_exc

    def custo_acumulado(self) -> float:
        return self._custo_acumulado_usd

    def _calcular_custo(self, model: str, prompt_tokens: int, completion_tokens: int) -> float:
        if model.endswith(":free"):
            return 0.0
        return 0.0  # fallback seguro; tabela de preços a implementar por fase

    def _persistir_trace(self, call: LLMCall, resp: LLMResponse, http_status: int) -> None:
        trace = {
            "call_id": call.call_id,
            "cycle_id": call.cycle_id,
            "phase": call.phase,
            "agent": call.agent,
            "call_type": call.call_type,
            "timestamp_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "provider": "openrouter",
            "model": call.model,
            "temperatura": call.temperature,
            "max_tokens": call.max_tokens,
            "seed": call.seed,
            "system_prompt_hash": _hash_prompt(call.messages[0].content),
            "user_prompt_hash": _hash_prompt(call.messages[-1].content),
            "system_prompt": call.messages[0].content,
            "user_prompt": call.messages[-1].content,
            "response_raw": resp.content,
            "response_parsed_ok": True,
            "usage": {
                "prompt_tokens": resp.prompt_tokens,
                "completion_tokens": resp.completion_tokens,
                "total_tokens": resp.total_tokens,
            },
            "cost_usd": resp.cost_usd,
            "latency_ms": resp.latency_ms,
            "http_status": http_status,
            "system_fingerprint": resp.system_fingerprint,
            "retry_attempt": resp.retry_attempts,
        }
        (self._llm_calls_dir / f"{call.call_id}.json").write_text(
            json.dumps(trace, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def _persistir_trace_falha(self, call: LLMCall, attempt: int, etype: str, emsg: str) -> None:
        trace = {
            "call_id": f"{call.call_id}_falha_{attempt}",
            "cycle_id": call.cycle_id, "agent": call.agent,
            "call_type": call.call_type,
            "timestamp_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "model": call.model, "error_type": etype,
            "error_message": emsg, "retry_attempt": attempt,
        }
        (self._llm_calls_dir / f"{call.call_id}_falha_{attempt}.json").write_text(
            json.dumps(trace, ensure_ascii=False, indent=2), encoding="utf-8"
        )


def _hash_prompt(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
