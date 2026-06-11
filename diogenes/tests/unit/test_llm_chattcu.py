"""
tests/unit/test_llm_chattcu.py — DVA-CBS | Projeto Diógenes
Testes unitários do ChatTCUClient.

Estratégia de mock:
  - MSAL: duck-typing — qualquer objeto com obter_token() -> str serve como auth.
  - HTTP: unittest.mock.patch em requests.post (ChatTCU usa requests, não httpx).
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from diogenes.llm.chattcu import ChatTCUClient
from diogenes.models import LLMCall, LLMMessage, LLMResponse

# ── Fixtures ─────────────────────────────────────────────────────────────────

class _FakeAuth:
    """Auth stub — retorna token fixo sem MSAL."""
    def __init__(self, token: str = "test-bearer-token") -> None:
        self._token = token
        self.call_count = 0

    def obter_token(self) -> str:
        self.call_count += 1
        return self._token


def _call(model: str = "Claude 4.6 Sonnet", max_tokens: int = 100) -> LLMCall:
    return LLMCall(
        call_id="20260530T000000Z_mycroft_consolidar_0001",
        cycle_id="MOD_010_A1_20260530T000000Z",
        phase="watson_integridade",
        agent="mycroft",
        call_type="consolidar",
        model=model,
        temperature=0.0,
        max_tokens=max_tokens,
        seed=42,
        messages=[
            LLMMessage(role="system", content="Você é Mycroft Holmes."),
            LLMMessage(role="user", content="Consolide os outputs."),
        ],
        timeout_segundos=180,
        max_tentativas_retry=2,
        backoff_segundos=10,
    )


def _client(tmp_path: Path) -> ChatTCUClient:
    return ChatTCUClient(
        base_url="https://chat-tcu.apps.tcu.gov.br",
        cycle_id="MOD_010_A1_20260530T000000Z",
        runtime_dir=tmp_path / "_runtime",
        auth=_FakeAuth(),
    )


def _mock_resp(content: str = "Resultado consolidado.", status: int = 200) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status
    resp.json.return_value = {
        "response": content,
        "chat_id": "chat-abc-123",
        "tokens": {
            "prompt_tokens": 120,
            "completion_tokens": 80,
            "total_tokens": 200,
            "reasoning_tokens": 0,
        },
    }
    resp.text = ""
    return resp


# ── Testes: chamada bem-sucedida ──────────────────────────────────────────────

class TestChatTCUClientSucesso:

    def test_complete_retorna_llm_response(self, tmp_path: Path) -> None:
        client = _client(tmp_path)
        call = _call()
        with patch("requests.post", return_value=_mock_resp()):
            resp = client.complete(call)

        assert isinstance(resp, LLMResponse)
        assert resp.content == "Resultado consolidado."
        assert resp.model_used == "Claude 4.6 Sonnet"
        assert resp.prompt_tokens == 120
        assert resp.completion_tokens == 80
        assert resp.total_tokens == 200
        assert resp.cost_usd == 0.0
        assert resp.http_status == 200
        assert resp.finish_reason == "stop"
        assert resp.retry_attempts == 0

    def test_body_correto_enviado(self, tmp_path: Path) -> None:
        client = _client(tmp_path)
        call = _call(model="Claude 4.6 Sonnet", max_tokens=8000)
        with patch("requests.post", return_value=_mock_resp()) as mock_post:
            client.complete(call)

        _, kwargs = mock_post.call_args
        body = kwargs["json"]
        assert body["prompt_sistema"] == "Você é Mycroft Holmes."
        assert body["prompt_usuario"] == "Consolide os outputs."
        assert body["parametro_modelo_llm"] == "Claude 4.6 Sonnet"
        assert body["max_tokens"] == 8000
        assert body["stream"] is False
        assert body["busca_web"] is False
        assert body["raciocinio"] is True

    def test_body_respeita_raciocinio_false(self, tmp_path: Path) -> None:
        client = _client(tmp_path)
        call = _call().model_copy(update={"raciocinio": False})
        with patch("requests.post", return_value=_mock_resp()) as mock_post:
            client.complete(call)

        _, kwargs = mock_post.call_args
        assert kwargs["json"]["raciocinio"] is False

    def test_header_authorization_bearer(self, tmp_path: Path) -> None:
        auth = _FakeAuth("meu-token-jwt-123")
        client = ChatTCUClient(
            base_url="https://chat-tcu.apps.tcu.gov.br",
            cycle_id="MOD_010_A1_20260530T000000Z",
            runtime_dir=tmp_path / "_runtime",
            auth=auth,
        )
        with patch("requests.post", return_value=_mock_resp()) as mock_post:
            client.complete(_call())

        _, kwargs = mock_post.call_args
        assert kwargs["headers"]["Authorization"] == "Bearer meu-token-jwt-123"
        assert kwargs["headers"]["Content-Type"] == "application/json"

    def test_system_fingerprint_eh_chat_id(self, tmp_path: Path) -> None:
        client = _client(tmp_path)
        with patch("requests.post", return_value=_mock_resp()):
            resp = client.complete(_call())
        assert resp.system_fingerprint == "chat-abc-123"

    def test_log_chamada_gravado(self, tmp_path: Path) -> None:
        import json
        client = _client(tmp_path)
        with patch("requests.post", return_value=_mock_resp()):
            client.complete(_call())

        log_path = tmp_path / "_runtime" / "llm_calls.jsonl"
        assert log_path.exists()
        entry = json.loads(log_path.read_text())
        assert entry["provider"] == "chattcu"
        assert entry["model"] == "Claude 4.6 Sonnet"

    def test_listar_modelos_parseia_catalogo(self, tmp_path: Path) -> None:
        client = _client(tmp_path)
        resp = MagicMock()
        resp.ok = True
        resp.json.return_value = {
            "modelos": [
                {"name": "Claude 4.6 Sonnet", "display_name": "Claude"},
                {"id": "gemini-3.1-flash-lite"},
            ]
        }
        with patch("requests.get", return_value=resp) as mock_get:
            modelos = client.listar_modelos()

        assert modelos[0]["name"] == "Claude 4.6 Sonnet"
        assert modelos[1]["id"] == "gemini-3.1-flash-lite"
        _, kwargs = mock_get.call_args
        assert kwargs["headers"]["Authorization"] == "Bearer test-bearer-token"

    def test_extrair_prompts_sem_system(self, tmp_path: Path) -> None:
        """Se não há mensagem system, prompt_sistema vai vazio."""
        call = LLMCall(
            call_id="x", cycle_id="c", phase="p", agent="a", call_type="t",
            model="m", temperature=0.0, max_tokens=100, seed=0,
            messages=[LLMMessage(role="user", content="Somente user")],
            timeout_segundos=30, max_tentativas_retry=1, backoff_segundos=1,
        )
        client = _client(tmp_path)
        with patch("requests.post", return_value=_mock_resp()) as mock_post:
            client.complete(call)
        _, kwargs = mock_post.call_args
        assert kwargs["json"]["prompt_sistema"] == ""
        assert kwargs["json"]["prompt_usuario"] == "Somente user"


# ── Testes: erros HTTP ────────────────────────────────────────────────────────

class TestChatTCUClientErros:

    def test_4xx_levanta_sem_retry(self, tmp_path: Path) -> None:
        from diogenes.llm.exceptions import LLMCallError
        client = _client(tmp_path)
        resp_401 = _mock_resp(status=401)
        resp_401.text = "Unauthorized"
        with (
            patch("requests.post", return_value=resp_401) as mock_post,
            pytest.raises(LLMCallError, match="401"),
        ):
            client.complete(_call())
        assert mock_post.call_count == 1  # sem retry

    def test_5xx_faz_retry_ate_max(self, tmp_path: Path) -> None:
        from diogenes.llm.exceptions import LLMCallError
        client = _client(tmp_path)
        resp_503 = _mock_resp(status=503)
        resp_503.text = "Service Unavailable"
        with (
            patch("requests.post", return_value=resp_503) as mock_post,
            patch("time.sleep"),
            pytest.raises(LLMCallError, match="503"),
        ):
            client.complete(_call())
        assert mock_post.call_count == 2  # max_tentativas_retry=2

    def test_5xx_depois_sucesso_retorna_ok(self, tmp_path: Path) -> None:
        """Primeira tentativa 503, segunda 200 — deve retornar LLMResponse."""
        client = _client(tmp_path)
        resp_503 = _mock_resp(status=503)
        resp_503.text = "fail"
        resp_200 = _mock_resp()
        with patch("requests.post", side_effect=[resp_503, resp_200]), patch("time.sleep"):
            resp = client.complete(_call())
        assert resp.content == "Resultado consolidado."
        assert resp.retry_attempts == 1

    def test_resposta_vazia_faz_retry_depois_sucesso(self, tmp_path: Path) -> None:
        """2xx com response vazio é falha transitória — retry até obter conteúdo."""
        client = _client(tmp_path)
        resp_vazia = _mock_resp(content="")
        resp_ok = _mock_resp()
        with patch("requests.post", side_effect=[resp_vazia, resp_ok]), patch("time.sleep"):
            resp = client.complete(_call())
        assert resp.content == "Resultado consolidado."
        assert resp.retry_attempts == 1

    def test_resposta_vazia_persistente_degrada_sem_levantar(self, tmp_path: Path) -> None:
        """Vazio em todas as tentativas: devolve a resposta vazia (degradação graciosa,
        o Orquestrador trata o arquivo como não analisado) em vez de abortar o ciclo."""
        client = _client(tmp_path)
        resp_vazia = _mock_resp(content="")
        with patch("requests.post", return_value=resp_vazia) as mock_post, patch("time.sleep"):
            resp = client.complete(_call())
        assert mock_post.call_count == 2  # max_tentativas_retry=2
        assert resp.content == ""
        assert resp.retry_attempts == 1

    def test_connection_error_faz_retry(self, tmp_path: Path) -> None:
        import requests as req

        from diogenes.llm.exceptions import LLMCallError
        client = _client(tmp_path)
        with (
            patch("requests.post", side_effect=req.ConnectionError("timeout")),
            patch("time.sleep"),
            pytest.raises(LLMCallError, match="conexão persistente"),
        ):
            client.complete(_call())

    def test_provider_invalido_levanta_value_error(self, monkeypatch) -> None:
        """Factory get_llm_client deve levantar ConfigError para provider inválido."""
        monkeypatch.setenv("DIOGENES_LLM_PROVIDER", "provedor_nao_existe")
        from diogenes.config import ConfigError, get_config
        from diogenes.llm.base import get_llm_client
        cfg = get_config()
        with pytest.raises(ConfigError, match="não reconhecido"):
            get_llm_client(cfg)
