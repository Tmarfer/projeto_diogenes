"""
llm/chattcu.py — DVA-CBS | Projeto Diógenes
Cliente HTTP para a API proprietária do ChatTCU.

Implementa o mesmo Protocol LLMClient que OpenRouterClient — interface
idêntica: complete(call: LLMCall) -> LLMResponse.

O ChatTCU NÃO é OpenAI-compatible. Não usa o openai SDK. Autenticação
via MSAL (Bearer JWT), endpoint POST /api/v1/chats/, corpo proprietário.

Referência de implementação: irene/llm_client.py (ChatTCUBackend) e
irene/auth_chattcu.py — adaptado ao contrato de tipos do Diógenes
(LLMCall / LLMResponse em vez de (system, user) -> (texto, tp, tr)).

Constantes da plataforma ChatTCU (não são segredos — fixas para todos
os usuários do TCU):
  CLIENT_ID  = 2acacabe-783e-4fd2-a9d8-cb2d783d55f0
  AUTHORITY  = login.microsoftonline.com / bf158188-...
  SCOPES     = api://d17f9b30-.../.default

Cache MSAL em ~/.diogenes/msal_cache.json. Na primeira execução, o
browser é aberto para login interativo com a conta @tcu.gov.br.
Execuções subsequentes renovam o token silenciosamente.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

import msal
import requests

from diogenes.models import LLMCall, LLMResponse

logger = logging.getLogger(__name__)

# ── Tabela de preços de referência (USD por 1M tokens) ──────────────────────
_PRECOS = {
    "Claude 4.6 Sonnet":      (3.00, 15.00),
    "claude-4-8-opus":        (5.00, 25.00),
    "claude-4-7-opus":        (5.00, 25.00),
    "claude-4-6-opus":        (5.00, 25.00),
    "gpt-5.5-thinking":       (5.00, 30.00),

    "gpt-5.4-thinking":       (2.50, 15.00),
    "gpt-5.3-instant":        (0.75,  4.50),
    "gpt-5.2-thinking":       (1.75, 14.00),
    "gpt-5.2-instant":        (0.75,  4.50),
    "GPT-4.1":                (2.00,  8.00),
    "GPT-4o":                 (2.50, 10.00),
    "o1":                    (15.00, 60.00),
    "o3":                    (10.00, 40.00),
    "o4-mini":                (1.10,  4.40),
    "gemini-3.1-pro-preview": (2.00, 12.00),
    "gemini-3.1-flash-lite":  (0.10,  0.40),
    "gemini-3-flash":         (0.50,  3.00),
    "DeepSeek R1":            (0.55,  2.19),
}


def _log_chamada_llm(agente: str, modelo: str, tokens_input: int, tokens_output: int, elapsed_s: float) -> None:
    """Log de observabilidade pós-chamada ao ChatTCU com design visual premium (estilo Claude Code)."""
    preco_in, preco_out = _PRECOS.get(modelo, (0.0, 0.0))
    custo = (tokens_input * preco_in + tokens_output * preco_out) / 1_000_000
    linha = (
        f"[LLM] agente={agente} | modelo={modelo} | "
        f"input={tokens_input:,} | output={tokens_output:,} | "
        f"tempo={elapsed_s:.1f}s | custo_ref=USD {custo:.6f}"
    )
    logger.info(linha)

    try:
        from rich.console import Console
        from rich.panel import Panel
        from rich.columns import Columns

        console = Console()

        agente_nome = agente.lower()
        if agente_nome == "mycroft":
            avatar = (
                "[yellow]  ▗███▖  [/yellow]\n"
                "[yellow] ▐  🧠 ▌ [/yellow]\n"
                "[yellow]  ▝███▘  [/yellow]"
            )
            cor = "yellow"
            desc = "[bold yellow]MYCROFT[/bold yellow] — Auditor Chefe"
        elif agente_nome == "watson":
            avatar = (
                "[magenta]  ▗███▖  [/magenta]\n"
                "[magenta] ▐ 👨‍⚕️ ▌ [/magenta]\n"
                "[magenta]  ▝███▘  [/magenta]"
            )
            cor = "magenta"
            desc = "[bold magenta]WATSON[/bold magenta] — Integridade Técnica"
        elif agente_nome == "sherlock":
            avatar = (
                "[green]  ▗███▖  [/green]\n"
                "[green] ▐ 🕵️ ▌_̅o[/green]\n"
                "[green]  ▝███▘  [/green]"
            )
            cor = "green"
            desc = "[bold green]SHERLOCK[/bold green] — Validação Metodológica"
        elif agente_nome == "irene":
            avatar = (
                "[cyan]  ▗███▖  [/cyan]\n"
                "[cyan] ▐ 👩‍💻 ▌ [/cyan]\n"
                "[cyan]  ▝███▘  [/cyan]"
            )
            cor = "cyan"
            desc = "[bold cyan]IRENE[/bold cyan] — Catalogadora Semântica"
        else:
            avatar = (
                "[blue]  ▗███▖  [/blue]\n"
                "[blue] ▐  👮 ▌ [/blue]\n"
                "[blue]  ▝███▘  [/blue]"
            )
            cor = "blue"
            desc = f"[bold blue]{agente.upper()}[/bold blue]"

        info_texto = (
            f"{desc}\n"
            f"[dim]Modelo: {modelo}[/dim]\n"
            f"[bold]Métricas:[/bold] [cyan]{tokens_input:,}[/cyan] in ➔ [cyan]{tokens_output:,}[/cyan] out | [green]{elapsed_s:.1f}s[/green]\n"
            f"[bold]Custo de Referência:[/bold] [yellow]USD {custo:.6f}[/yellow]"
        )

        panel_avatar = Panel(avatar, border_style=cor, padding=(0, 1))
        panel_info = Panel(info_texto, border_style="dim", expand=True)

        console.print(Columns([panel_avatar, panel_info], expand=True))
    except Exception:  # noqa: BLE001
        print(linha)


def _parse_lista(data: Any, chave_preferida: str | None = None) -> list:
    """Normaliza respostas de catálogo da API ChatTCU."""
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        if chave_preferida and data.get(chave_preferida):
            return data[chave_preferida]
        for key in ("modelos", "data", "bases"):
            if data.get(key):
                return data[key]
        if data:
            first = next(iter(data.values()))
            return first if isinstance(first, list) else [first]
    return []

# ── Constantes da plataforma ChatTCU ────────────────────────────────────────

_CLIENT_ID = "2acacabe-783e-4fd2-a9d8-cb2d783d55f0"
_AUTHORITY  = "https://login.microsoftonline.com/bf158188-9a11-44c2-b7fc-21e85613ba27"
_SCOPES     = ["api://d17f9b30-94ec-4e8b-8ff8-998c1bf741cd/.default"]
_CACHE_PATH = Path.home() / ".diogenes" / "msal_cache.json"
_ENDPOINT   = "/api/v1/chats/"


# ── Auth ─────────────────────────────────────────────────────────────────────

class _ChatTCUAuth:
    """
    Gerenciador de token MSAL para o ChatTCU.

    Reutiliza o mesmo fluxo validado em irene/auth_chattcu.py,
    mas com cache separado (~/.diogenes/) para isolamento entre
    os dois processos. Compartilha os mesmos CLIENT_ID/AUTHORITY/SCOPES,
    portanto tecnicamente o mesmo token JWT serve para ambos — mas o
    cache separado evita dependência de tempo de vida entre Diógenes e Irene.
    """

    def __init__(self, cache_path: Path = _CACHE_PATH) -> None:
        self._cache_path = cache_path
        self._cache = self._carregar_cache()
        self._app = msal.PublicClientApplication(
            client_id=_CLIENT_ID,
            authority=_AUTHORITY,
            token_cache=self._cache,
        )

    def obter_token(self) -> str:
        contas = self._app.get_accounts()
        if contas:
            resultado = self._app.acquire_token_silent(_SCOPES, account=contas[0])
            if resultado and "access_token" in resultado:
                logger.debug("[ChatTCUAuth/Diogenes] Token obtido do cache (silent).")
                self._persistir_cache()
                return resultado["access_token"]
            logger.warning(
                "[ChatTCUAuth/Diogenes] acquire_token_silent falhou: %s. "
                "Tentando fluxo interativo.",
                resultado.get("error_description") if resultado else "sem resultado",
            )

        logger.info(
            "[ChatTCUAuth/Diogenes] Abrindo browser para login com conta @tcu.gov.br. "
            "Isso ocorre apenas uma vez (token cacheado em %s).", self._cache_path,
        )
        resultado = self._app.acquire_token_interactive(scopes=_SCOPES)

        if not resultado or "access_token" not in resultado:
            erro = (
                resultado.get("error_description", "sem detalhes")
                if resultado else "sem resultado"
            )
            raise RuntimeError(
                f"[ChatTCUAuth/Diogenes] Falha ao obter token do ChatTCU. "
                f"Detalhes: {erro}. "
                f"Verifique se o acesso PIM 'NIA - Acesso a API do ChatTCU' "
                f"está ativo em portal.azure.com."
            )

        self._persistir_cache()
        logger.info("[ChatTCUAuth/Diogenes] Token obtido. Cache persistido em %s.", self._cache_path)
        return resultado["access_token"]

    def _carregar_cache(self) -> msal.SerializableTokenCache:
        cache = msal.SerializableTokenCache()
        if self._cache_path.exists():
            try:
                cache.deserialize(self._cache_path.read_text(encoding="utf-8"))
            except Exception as exc:
                logger.warning(
                    "[ChatTCUAuth/Diogenes] Falha ao carregar cache em %s: %s. "
                    "Iniciando com cache vazio.", self._cache_path, exc,
                )
        return cache

    def _persistir_cache(self) -> None:
        if self._cache.has_state_changed:
            self._cache_path.parent.mkdir(parents=True, exist_ok=True)
            self._cache_path.write_text(self._cache.serialize(), encoding="utf-8")
            try:
                self._cache_path.chmod(0o600)
            except OSError:
                logger.warning(
                    "[ChatTCUAuth/Diogenes] Não foi possível ajustar permissão 600 em %s.",
                    self._cache_path,
                )


# ── Cliente ──────────────────────────────────────────────────────────────────

class ChatTCUClient:
    """
    Cliente LLM para o ChatTCU — implementa o Protocol LLMClient.

    Converte LLMCall (contrato Diógenes) para o formato da API do ChatTCU
    e converte a resposta de volta para LLMResponse.

    Extração de system/user: o LLMCall sempre tem exatamente uma mensagem
    system e uma mensagem user (padrão dos agentes Diógenes). Mensagens em
    ordem diferente ou papéis adicionais são tratadas de forma defensiva.

    NOTA sobre tokens: o ChatTCU retorna reasoning_tokens sempre 0 via API
    (raciocínio interno não exposto). completion_tokens inclui raciocínio
    interno (~3800 tok/chamada com Opus, ~900 com GPT-5.4). Não interpretar
    como volume de texto útil gerado.

    NOTA sobre cost_usd: o ChatTCU não cobra por chamada individual —
    é um serviço institucional do TCU. cost_usd sempre retorna 0.0.
    """

    def __init__(
        self,
        base_url: str,
        cycle_id: str,
        runtime_dir: Path,
        auth: object | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._cycle_id = cycle_id
        self._runtime_dir = runtime_dir
        self._auth: object | None = auth

    def complete(self, call: LLMCall) -> LLMResponse:
        """
        Executa chamada ao ChatTCU e retorna LLMResponse.

        Retry:
          - HTTP 4xx: permanente, sem retry.
          - HTTP 5xx: até call.max_tentativas_retry tentativas,
                      sleep call.backoff_segundos entre cada uma.
          - Erro de conexão (requests.RequestException): mesma política que 5xx.

        Timeout: call.timeout_segundos (modelos thinking podem levar ~2 min).
        """
        system_prompt, user_prompt = self._extrair_prompts(call)

        body = {
            "prompt_sistema":       system_prompt,
            "prompt_usuario":       user_prompt,
            "parametro_modelo_llm": call.model,
            "stream":               False,
            "busca_web":            False,
            "raciocinio":           call.raciocinio,
            "max_tokens":           call.max_tokens,
        }

        url = self._base_url + _ENDPOINT
        # Dev mode: fast iteration with reduced timeout and single attempt
        _dev_mode = os.environ.get("DIOGENES_DEV_MODE", "").lower() in ("true", "1")
        max_tentativas = 1 if _dev_mode else max(1, call.max_tentativas_retry)
        _timeout = min(call.timeout_segundos, 30) if _dev_mode else call.timeout_segundos
        retry_count = 0

        import time as _time
        t0 = _time.monotonic()

        for tentativa in range(1, max_tentativas + 1):
            token = self._obter_token()
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type":  "application/json",
            }
            try:
                resp = requests.post(
                    url, json=body, headers=headers,
                    timeout=_timeout,
                )

                if 400 <= resp.status_code < 500:
                    from diogenes.llm.exceptions import LLMCallError
                    raise LLMCallError(
                        f"ChatTCU: erro permanente HTTP {resp.status_code} "
                        f"(call_id={call.call_id}). Corpo: {resp.text[:400]}"
                    )

                if resp.status_code >= 500:
                    logger.warning(
                        "[ChatTCUClient] Tentativa %d/%d — HTTP %d: %s",
                        tentativa, max_tentativas, resp.status_code, resp.text[:200],
                    )
                    if tentativa < max_tentativas:
                        retry_count += 1
                        _time.sleep(call.backoff_segundos)
                        continue
                    from diogenes.llm.exceptions import LLMCallError
                    raise LLMCallError(
                        f"ChatTCU: HTTP {resp.status_code} persistente após "
                        f"{max_tentativas} tentativas (call_id={call.call_id})."
                    )

                # 2xx — sucesso
                dados = resp.json()
                texto = dados.get("response", "")
                tokens_obj        = dados.get("tokens") or {}
                total             = tokens_obj.get("total_tokens", 0)
                prompt_tokens     = tokens_obj.get("prompt_tokens", total)
                completion_tokens = tokens_obj.get("completion_tokens", 0)
                chat_id = dados.get("chat_id", "")

                latencia_ms = int((_time.monotonic() - t0) * 1000)
                logger.debug(
                    "[ChatTCUClient] OK — call_id=%s chat_id=%s "
                    "tokens=%d+%d latencia=%dms",
                    call.call_id, chat_id, prompt_tokens, completion_tokens, latencia_ms,
                )

                self._gravar_log_chamada(call, texto, prompt_tokens, completion_tokens)

                # Observabilidade — log de custo de referência
                _log_chamada_llm(
                    agente=call.agent,
                    modelo=call.model,
                    tokens_input=prompt_tokens,
                    tokens_output=completion_tokens,
                    elapsed_s=(_time.monotonic() - t0),
                )

                return LLMResponse(
                    content=texto,
                    call_id=call.call_id,
                    model_used=call.model,
                    system_fingerprint=chat_id or None,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=total,
                    cost_usd=0.0,           # ChatTCU é serviço institucional — sem cobrança por chamada
                    latency_ms=latencia_ms,
                    retry_attempts=retry_count,
                    http_status=resp.status_code,
                    finish_reason="stop",   # ChatTCU não expõe finish_reason
                )

            except requests.RequestException as exc:
                logger.warning(
                    "[ChatTCUClient] Tentativa %d/%d — erro de conexão: %s",
                    tentativa, max_tentativas, exc,
                )
                if tentativa < max_tentativas:
                    retry_count += 1
                    _time.sleep(call.backoff_segundos)
                else:
                    from diogenes.llm.exceptions import LLMCallError
                    raise LLMCallError(
                        f"ChatTCU: erro de conexão persistente após "
                        f"{max_tentativas} tentativas. Último erro: {exc}"
                    ) from exc

        from diogenes.llm.exceptions import LLMCallError
        raise LLMCallError(f"ChatTCU: falha inesperada (call_id={call.call_id}).")

    def listar_modelos(self, timeout: int = 60) -> list[dict[str, Any]]:
        """Lista modelos disponíveis no ChatTCU via GET /api/v1/models/."""
        token = self._obter_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        resp = requests.get(
            f"{self._base_url}/api/v1/models/",
            headers=headers,
            timeout=timeout,
        )
        if not resp.ok:
            resp.raise_for_status()
        modelos = _parse_lista(resp.json(), "modelos")
        return [m for m in modelos if isinstance(m, dict)]

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _obter_token(self) -> str:
        if self._auth is None:
            self._auth = _ChatTCUAuth()
        return self._auth.obter_token()  # type: ignore[attr-defined]

    @staticmethod
    def _extrair_prompts(call: LLMCall) -> tuple[str, str]:
        """
        Extrai (system_prompt, user_prompt) de call.messages.

        Os agentes do Diógenes constroem sempre: [system, user].
        Extração defensiva: busca pela role, não pela posição.
        Se não houver system, usa string vazia (ChatTCU aceita prompt_sistema vazio).
        Se não houver user, concatena todas as mensagens não-system.
        """
        system = ""
        user_parts: list[str] = []
        for msg in call.messages:
            if msg.role == "system":
                system = msg.content
            else:
                user_parts.append(msg.content)
        return system, "\n\n".join(user_parts)

    def _gravar_log_chamada(
        self,
        call: LLMCall,
        texto: str,
        prompt_tokens: int,
        completion_tokens: int,
    ) -> None:
        """Grava JSONL de chamada em _runtime/llm_calls.jsonl (mesmo padrão do OpenRouter)."""
        import json
        from datetime import UTC, datetime
        entry = {
            "call_id": call.call_id,
            "cycle_id": call.cycle_id,
            "timestamp_utc": datetime.now(UTC).isoformat(),
            "provider": "chattcu",
            "model": call.model,
            "phase": call.phase,
            "agent": call.agent,
            "call_type": call.call_type,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "cost_usd": 0.0,
            "response_length": len(texto),
        }
        try:
            self._runtime_dir.mkdir(parents=True, exist_ok=True)
            with open(self._runtime_dir / "llm_calls.jsonl", "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except OSError:
            pass  # log não pode bloquear execução
