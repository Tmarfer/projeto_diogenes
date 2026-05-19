"""
agents/heartbeat.py — DVA-CBS | Projeto Diógenes
Carregamento e extração de seções do heartbeat por call_type.

O invocador injeta apenas a seção correspondente ao call_type atual no
início do user_prompt, antes dos demais inputs (SDD Bloco 6, Bloco 9).

Referência normativa: Bloco 1.1 (PRD v0.1), Paperclip framework (SDD intro)
"""
from __future__ import annotations

from pathlib import Path

# Mapeamento call_type (código) → nome da seção no heartbeat.md
# Necessário porque os nomes divergem em dois casos:
#   analise_inicial  → analise_arquivo  (heartbeat usa terminologia per-file)
#   validacao_inicial → verificar_ponto  (heartbeat usa terminologia per-point)
# Para Mycroft: avaliar_sherlock e fixar_decisao_sherlock reutilizam as
# mesmas seções de avaliar_agente e fixar_decisao (o contexto da chamada
# diferencia qual agente está sendo avaliado).
CALL_TYPE_TO_SECTION: dict[str, str] = {
    # Watson
    "analise_inicial":               "analise_arquivo",
    "consolidar_watson":             "consolidar_watson",
    "validacao_planilha_rn":         "validacao_planilha_rn",
    "resposta_r1":                   "resposta_r1",
    "resposta_r2":                   "resposta_r2",
    # Mycroft
    "definir_tasks_watson":          "definir_tasks_watson",
    "avaliar_agente":                "avaliar_agente",
    "avaliar_sherlock":              "avaliar_agente",             # mesma seção
    "fixar_decisao":                 "fixar_decisao",
    "fixar_decisao_sherlock":        "fixar_decisao",              # mesma seção
    "montar_pacote_sherlock":        "montar_pacote_sherlock",
    "consolidar":                    "consolidar",
    # Sherlock
    "validacao_inicial":             "verificar_ponto",
    "validacao_planilha_rn_sherlock": "validacao_planilha_rn_sherlock",
    "consolidar_sherlock":           "consolidar_sherlock",
    # resposta_r1 e resposta_r2 já coincidem com o nome da seção
}


class HeartbeatLoader:
    """
    Lê um arquivo heartbeat.md e extrai seções por nome de call_type.

    Formato esperado do arquivo:
        # Heartbeat de {Agente} — {nome_secao}
        ... conteúdo da seção ...
        ---
        # Heartbeat de {Agente} — {próxima_seção}
        ...

    Uso:
        loader = HeartbeatLoader(docs_dir / "heartbeat.md")
        hb = loader.get_section("analise_inicial")
        user_prompt = f"{hb}\\n\\n---\\n\\n{conteudo_real}"
    """

    def __init__(self, heartbeat_path: Path) -> None:
        self._path = heartbeat_path
        self._sections: dict[str, str] = {}
        if heartbeat_path.exists():
            self._sections = _parse_heartbeat(heartbeat_path.read_text(encoding="utf-8"))

    def get_section(self, call_type: str) -> str:
        """
        Retorna o texto da seção heartbeat para o call_type dado.
        Aplica o mapeamento CALL_TYPE_TO_SECTION quando necessário.
        Retorna string vazia se a seção não for encontrada (não bloqueia a chamada).
        """
        section_name = CALL_TYPE_TO_SECTION.get(call_type, call_type)
        return self._sections.get(section_name, "")

    def available_sections(self) -> list[str]:
        return list(self._sections.keys())


def _parse_heartbeat(content: str) -> dict[str, str]:
    """
    Parseia o conteúdo do heartbeat.md e retorna um dicionário
    {nome_da_seção: conteúdo_da_seção}.

    Cabeçalho de seção: linha que começa com "# Heartbeat de"
    e contém " — " seguido do nome da seção.
    """
    sections: dict[str, str] = {}
    current_name: str | None = None
    current_lines: list[str] = []

    for line in content.splitlines():
        if line.startswith("# Heartbeat de") and " — " in line:
            # Salvar seção anterior
            if current_name is not None:
                sections[current_name] = _limpar_secao("\n".join(current_lines))
            # Iniciar nova seção
            current_name = line.split(" — ", 1)[1].strip()
            current_lines = []
        elif current_name is not None:
            current_lines.append(line)

    # Última seção
    if current_name is not None:
        sections[current_name] = _limpar_secao("\n".join(current_lines))

    return sections


def _limpar_secao(texto: str) -> str:
    """Remove separadores e espaços em branco excessivos no final da seção."""
    linhas = texto.rstrip().splitlines()
    # Remover separadores finais (--- ou linhas de rodapé)
    while linhas and linhas[-1].strip() in ("---", ""):
        linhas.pop()
    return "\n".join(linhas).strip()


def injetar_heartbeat(heartbeat_secao: str, user_prompt: str) -> str:
    """
    Prepend do heartbeat ao user_prompt com separador visual.
    Retorna user_prompt inalterado se heartbeat_secao estiver vazio.
    """
    if not heartbeat_secao:
        return user_prompt
    return f"{heartbeat_secao}\n\n---\n\n{user_prompt}"
