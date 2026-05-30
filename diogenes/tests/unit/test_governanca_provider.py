"""
test_governanca_provider.py

Garante que o sistema NUNCA roda com OpenRouter.
Dados fiscais do TC 015.848/2025-6 só podem trafegar
pela infraestrutura interna do TCU (ChatTCU).
"""
import pytest
from diogenes.config import ConfigError


class TestGovernancaProvider:

    def test_openrouter_levanta_config_error(self, monkeypatch):
        """OpenRouter deve ser rejeitado com mensagem clara de governança."""
        monkeypatch.setenv("DIOGENES_LLM_PROVIDER", "openrouter")
        monkeypatch.setenv("DIOGENES_LLM_API_KEY", "sk-or-v1-qualquer")
        monkeypatch.setenv(
            "DIOGENES_CHATTCU_BASE_URL", "https://chat-tcu.apps.tcu.gov.br"
        )
        from diogenes.config import get_config
        from diogenes.llm.base import get_llm_client

        cfg = get_config()
        with pytest.raises(ConfigError, match="não é permitido"):
            get_llm_client(cfg)

    def test_provider_vazio_usa_chattcu(self, monkeypatch):
        """Sem DIOGENES_LLM_PROVIDER definido, o default é chattcu."""
        monkeypatch.delenv("DIOGENES_LLM_PROVIDER", raising=False)
        monkeypatch.setenv(
            "DIOGENES_CHATTCU_BASE_URL", "https://chat-tcu.apps.tcu.gov.br"
        )
        from diogenes.config import get_config

        cfg = get_config()
        assert cfg.llm_provider == "chattcu"

    def test_provider_invalido_levanta_config_error(self, monkeypatch):
        """Provider desconhecido deve ser rejeitado com mensagem clara."""
        monkeypatch.setenv("DIOGENES_LLM_PROVIDER", "gemini-direto")
        monkeypatch.setenv(
            "DIOGENES_CHATTCU_BASE_URL", "https://chat-tcu.apps.tcu.gov.br"
        )
        from diogenes.config import get_config
        from diogenes.llm.base import get_llm_client

        cfg = get_config()
        with pytest.raises(ConfigError, match="não reconhecido"):
            get_llm_client(cfg)

    def test_chattcu_sem_api_key_nao_levanta_erro(self, monkeypatch):
        """ChatTCU não usa API key — ausência de DIOGENES_LLM_API_KEY é normal."""
        monkeypatch.setenv("DIOGENES_LLM_PROVIDER", "chattcu")
        monkeypatch.delenv("DIOGENES_LLM_API_KEY", raising=False)
        monkeypatch.setenv(
            "DIOGENES_CHATTCU_BASE_URL", "https://chat-tcu.apps.tcu.gov.br"
        )
        from diogenes.config import get_config

        # Não deve levantar nenhuma exceção
        cfg = get_config()
        assert cfg.llm_provider == "chattcu"
