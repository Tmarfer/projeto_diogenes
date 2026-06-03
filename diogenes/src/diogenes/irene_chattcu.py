"""
irene_chattcu.py — DVA-CBS | Projeto Diógenes

Adaptador que conecta o pacote `irene` (standalone) ao ChatTCU.

Motivação: a versão standalone do `irene` (v1.0.0) faz a classificação semântica
(C4) via SDK OpenAI (`OpenAI(api_key, base_url).chat.completions.create`), que NÃO
é compatível com o ChatTCU (endpoint proprietário `/api/v1/chats/`, auth MSAL).

Este módulo, sem alterar o pacote `irene` no disco:
  1. `garantir_irene_no_path()` — injeta o diretório do pacote `irene` no sys.path.
  2. `patch_c4_para_chattcu()` — substitui `irene.semantica._chamar` por uma função
     que roteia a chamada do C4 pelo `LLMClient` do Diógenes (ChatTCU), reusando
     auth, retry e logging já validados.

A assinatura preservada é a de `irene.semantica._chamar`:
    _chamar(client, system, user, modelo, tentativas=2) -> (texto, prompt_tokens, completion_tokens)
O argumento `client` (instância OpenAI construída em semantica.executar) é ignorado.
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

from diogenes.llm.base import LLMClient
from diogenes.llm.call_id import gerar_call_id
from diogenes.llm.seed import calcular_seed
from diogenes.models import LLMCall, LLMMessage

logger = logging.getLogger(__name__)

FASE_IRENE = "irene_catalogacao"
_CALL_TYPE_C4 = "c4_semantica"


def garantir_irene_no_path(package_dir: Path | None) -> None:
    """Insere o diretório-raiz do pacote `irene` no sys.path, se necessário.

    `package_dir` deve ser o diretório que CONTÉM a pasta `irene/` (ex.:
    .../irene_standalone). Levanta ImportError com mensagem clara se o pacote
    não for localizável — assim o orquestrador transiciona para ABORTADO_FALHA_AGENTE
    com diagnóstico útil em vez de um ModuleNotFoundError silencioso.
    """
    # Já importável? Nada a fazer.
    try:
        import irene  # noqa: F401
        return
    except ImportError:
        pass

    if package_dir is None:
        raise ImportError(
            "Pacote `irene` não importável e IRENE_PACKAGE_DIR não definido. "
            "Defina IRENE_PACKAGE_DIR no .env apontando para o diretório que contém a pasta `irene/`."
        )

    raiz = Path(package_dir)
    if not (raiz / "irene" / "__init__.py").exists():
        raise ImportError(
            f"IRENE_PACKAGE_DIR='{raiz}' não contém um pacote `irene/` (falta irene/__init__.py)."
        )

    if str(raiz) not in sys.path:
        sys.path.insert(0, str(raiz))
        logger.info("[Irene] Pacote `irene` adicionado ao sys.path a partir de %s", raiz)

    # Validar import efetivo
    import irene  # noqa: F401


def patch_c4_para_chattcu(
    llm_client: LLMClient,
    model: str,
    cycle_id: str,
    *,
    timeout_segundos: int = 180,
    max_tentativas_retry: int = 4,
    backoff_segundos: int = 30,
    raciocinio: bool = True,
    max_tokens: int = 4000,
) -> None:
    """Monkeypatcha o client do Irene para usar o ChatTCU via LLMClient do Diógenes.

    Compatível com Irene v1.0.0/v1.2.0 (que usavam semantica._chamar) e Irene v1.3.0+
    (que usam criar_cliente).
    """
    import irene.semantica
    import irene.llm_client

    class DiogenesIreneClientWrapper:
        def __init__(
            self,
            llm_client: LLMClient,
            model: str,
            cycle_id: str,
            timeout_segundos: int,
            max_tentativas_retry: int,
            backoff_segundos: int,
            raciocinio: bool,
            max_tokens: int,
        ) -> None:
            self.llm_client = llm_client
            self.model = model
            self.cycle_id = cycle_id
            self.timeout_segundos = timeout_segundos
            self.max_tentativas_retry = max_tentativas_retry
            self.backoff_segundos = backoff_segundos
            self.raciocinio = raciocinio
            self.max_tokens = max_tokens

        def completar(self, system_prompt: str, user_prompt: str) -> tuple[str, int, int]:
            from irene.llm_client import LLMCallError

            call = LLMCall(
                call_id=gerar_call_id("irene", _CALL_TYPE_C4),
                cycle_id=self.cycle_id,
                phase=FASE_IRENE,
                agent="irene",
                call_type=_CALL_TYPE_C4,
                model=self.model,
                temperature=0.1,
                max_tokens=self.max_tokens,
                seed=calcular_seed(42, self.cycle_id, FASE_IRENE, _CALL_TYPE_C4),
                raciocinio=self.raciocinio,
                messages=[
                    LLMMessage(role="system", content=system_prompt),
                    LLMMessage(role="user", content=user_prompt),
                ],
                timeout_segundos=self.timeout_segundos,
                max_tentativas_retry=self.max_tentativas_retry,
                backoff_segundos=self.backoff_segundos,
            )
            try:
                resp = self.llm_client.complete(call)
                return resp.content, resp.prompt_tokens, resp.completion_tokens
            except Exception as exc:
                raise LLMCallError(f"Erro na chamada do Diogenes LLMClient: {exc}") from exc

    def custom_criar_cliente(config) -> DiogenesIreneClientWrapper:  # noqa: ANN001
        modelo_efetivo = getattr(config, "model", None) or model
        return DiogenesIreneClientWrapper(
            llm_client=llm_client,
            model=modelo_efetivo,
            cycle_id=cycle_id,
            timeout_segundos=timeout_segundos,
            max_tentativas_retry=max_tentativas_retry,
            backoff_segundos=backoff_segundos,
            raciocinio=raciocinio,
            max_tokens=max_tokens,
        )

    # 1. Se usar a nova API com criar_cliente (v1.3.0+)
    patched_new = False
    if hasattr(irene.semantica, "criar_cliente"):
        irene.semantica.criar_cliente = custom_criar_cliente  # type: ignore[attr-defined]
        patched_new = True
    if hasattr(irene.llm_client, "criar_cliente"):
        irene.llm_client.criar_cliente = custom_criar_cliente
        patched_new = True

    if patched_new:
        logger.info(
            "[Irene] C4 roteado para ChatTCU (modelo=%s) via LLMClient do Diógenes (criar_cliente patched).",
            model,
        )

    # 2. Se usar a antiga API com _chamar (v1.0.0 / v1.2.0)
    if hasattr(irene.semantica, "_chamar"):
        def _chamar_chattcu(client, system, user, modelo, tentativas=2):  # noqa: ANN001, ARG001
            modelo_efetivo = modelo or model
            call = LLMCall(
                call_id=gerar_call_id("irene", _CALL_TYPE_C4),
                cycle_id=cycle_id,
                phase=FASE_IRENE,
                agent="irene",
                call_type=_CALL_TYPE_C4,
                model=modelo_efetivo,
                temperature=0.1,
                max_tokens=max_tokens,
                seed=calcular_seed(42, cycle_id, FASE_IRENE, _CALL_TYPE_C4),
                raciocinio=raciocinio,
                messages=[
                    LLMMessage(role="system", content=system),
                    LLMMessage(role="user", content=user),
                ],
                timeout_segundos=timeout_segundos,
                max_tentativas_retry=max_tentativas_retry,
                backoff_segundos=backoff_segundos,
            )
            resp = llm_client.complete(call)
            return resp.content, resp.prompt_tokens, resp.completion_tokens

        irene.semantica._chamar = _chamar_chattcu  # type: ignore[attr-defined]
        logger.info(
            "[Irene] C4 roteado para ChatTCU (modelo=%s) via LLMClient do Diógenes (_chamar patched).",
            model,
        )
