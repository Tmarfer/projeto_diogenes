"""
irene.py — DVA-CBS | Projeto Diógenes
Wrapper de biblioteca para o pipeline Irene v1.3.1.

Responsabilidade: chamar os estágios C1-C5 do Irene como biblioteca Python
(não como CLI), retornar (estado, metricas) no formato esperado pelo
Orquestrador conforme INTEGRACAO_DIOGENES.md seção 5.1.

O `irene/run.py` foi projetado para uso via CLI (retorna int exit code).
Este módulo acessa os estágios diretamente para obter os dados estruturados
necessários ao Orquestrador sem precisar subprocessar o CLI.

Versão mínima aceita do catálogo: VERSAO_IRENE_MINIMA (abaixo).
Versões anteriores devem ser rejeitadas — reexecução com nova versão requerida.

Referência normativa: INTEGRACAO_DIOGENES.md seções 4-9, SDD Bloco 15.
"""
from __future__ import annotations

import logging
import os
import shutil
from datetime import date, datetime, timezone
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)

VERSAO_IRENE_MINIMA = "1.3.0"

# Mapeamento exit code Irene → estado Diógenes
_CODIGO_PARA_ESTADO: dict[int, str] = {
    0: "IRENE_APROVADO",
    1: "IRENE_ALERTA",
    2: "IRENE_BLOQUEADO",
    3: "IRENE_ERRO_FATAL",
}


def executar_irene(
    caminho_manifesto: Path,
    modulo: str,
    dir_saida: Path | None = None,
    descricao_modulo: str = "",
    verbose: bool = False,
) -> tuple[str, dict]:
    """
    Executa o pipeline Irene (C1-C5) e retorna (estado, metricas).

    Parâmetros:
        caminho_manifesto: caminho para o manifesto YAML de Lestrade.
        modulo:            identificador do módulo (ex: MOD_010_Pessoa_Fisica).
        dir_saida:         override do diretório de saída; se None, usa
                           {raiz_projeto}/IRENE_OUT/{modulo}.
        descricao_modulo:  contexto adicional para o prompt de C4 (Semântica).
        verbose:           ativa logging DEBUG no pipeline Irene.

    Retorno:
        estado:  "IRENE_APROVADO" | "IRENE_ALERTA" | "IRENE_BLOQUEADO" | "IRENE_ERRO_FATAL"
        metricas: dict com score_consolidado, recomendacao, versao_irene,
                  abas_classificadas, abas_total, tokens_total, dir_saida, artefatos, etc.
                  Vazio em caso de IRENE_ERRO_FATAL.

    Exceções:
        Não propaga — captura tudo e retorna "IRENE_ERRO_FATAL" com metricas vazias.
        O Orquestrador é responsável por transicionar para ABORTADO_FALHA_AGENTE.
    """
    logger.info("[Irene] Iniciando pipeline — manifesto=%s módulo=%s", caminho_manifesto, modulo)
    print(f"\n{'='*60}")
    print(f"  INICIALIZANDO PIPELINE IRENE — {modulo}")
    print(f"{'='*60}\n")

    try:
        # ── Forçar desativação do Excel MCP Server ────────────────────────────
        # Evita travamento: se mcp Python SDK estiver instalado mas o servidor
        # npx não estiver disponível/configurado, o pipeline ficaria suspenso.
        # Irene usará fallback openpyxl (leitura direta, sem dependência externa).
        os.environ["IRENE_EXCEL_MCP_COMMAND"] = ""
        logger.info("[Irene] MCP Excel forçadamente desabilitado — usando openpyxl")

        from irene import __version__ as versao_irene
        from irene.config import carregar_config as carregar_config_irene
        from irene import manifesto as c1, profiling as c2, amostragem as c3, artefatos as c5

        # Resetar cache do MCP no módulo amostragem (evita estado stale)
        if hasattr(c3, '_MCP_DISPONIVEL'):
            c3._MCP_DISPONIVEL = None

        config = carregar_config_irene()

        # ── C1 — Manifesto ────────────────────────────────────────────────────
        logger.info("[Irene] C1 — Manifesto")
        try:
            inventario = c1.executar(caminho_manifesto, raiz_override=None)
        except RuntimeError as exc:
            logger.error("[Irene] C1 BLOQUEADO: %s", exc)
            return "IRENE_ERRO_FATAL", {}
        except Exception as exc:
            logger.error("[Irene] C1 ERRO FATAL: %s", exc)
            return "IRENE_ERRO_FATAL", {}

        dir_saida_efetivo: Path = (
            dir_saida / modulo if dir_saida
            else inventario.raiz_projeto / "IRENE_OUT" / modulo
        )

        # ── C2 — Profiling ────────────────────────────────────────────────────
        logger.info("[Irene] C2 — Profiling")
        try:
            perfis = c2.executar(inventario)
        except Exception as exc:
            logger.error("[Irene] C2 ERRO FATAL: %s", exc)
            return "IRENE_ERRO_FATAL", {}

        # ── C3 — Amostragem ───────────────────────────────────────────────────
        logger.info("[Irene] C3 — Amostragem")
        print("[Irene] C3 — Amostragem (openpyxl fallback, sem MCP)")

        # Adicionar handler stdout temporário para ver progresso do C3
        _c3_handler = logging.StreamHandler()
        _c3_handler.setLevel(logging.WARNING)
        _c3_handler.setFormatter(logging.Formatter("  %(message)s"))
        _irene_c3_logger = logging.getLogger("irene.amostragem")
        _irene_c3_logger.addHandler(_c3_handler)
        _irene_c3_logger.setLevel(logging.WARNING)

        import time as _time
        _t0_c3 = _time.time()
        try:
            amostragens = c3.executar(perfis, config)
        except Exception as exc:
            logger.error("[Irene] C3 ERRO FATAL: %s", exc)
            _irene_c3_logger.removeHandler(_c3_handler)
            return "IRENE_ERRO_FATAL", {}
        _irene_c3_logger.removeHandler(_c3_handler)
        _elapsed_c3 = _time.time() - _t0_c3
        print(f"[Irene] C3 — Concluída em {_elapsed_c3:.1f}s ({len(amostragens)} abas processadas)")
        logger.info("[Irene] C3 concluída em %.1fs", _elapsed_c3)

        # ── C4 — Semântica via LLM ────────────────────────────────────────────
        logger.info("[Irene] C4 — Semântica via LLM")
        n_processaveis = sum(1 for p in perfis if p.processavel)
        print(f"[Irene] C4 — Semântica via LLM (ChatTCU) — {n_processaveis} abas a classificar")
        print(f"[Irene] C4 — Modelo: {config.model} | Timeout: 180s/chamada")

        # Adicionar handler stdout temporário para ver progresso do C4
        _c4_handler = logging.StreamHandler()
        _c4_handler.setLevel(logging.INFO)
        _c4_handler.setFormatter(logging.Formatter("  %(message)s"))
        _irene_logger = logging.getLogger("irene")
        _irene_logger.addHandler(_c4_handler)
        _irene_logger.setLevel(logging.INFO)

        _t0_c4 = _time.time()
        try:
            from irene import semantica as c4
            classificacoes = c4.executar(
                perfis, amostragens,
                modulo, descricao_modulo or f"Módulo {modulo}",
                config,
            )
        except Exception as exc:
            logger.error("[Irene] C4 ERRO FATAL: %s", exc)
            _irene_logger.removeHandler(_c4_handler)
            return "IRENE_ERRO_FATAL", {}

        _irene_logger.removeHandler(_c4_handler)
        _elapsed_c4 = _time.time() - _t0_c4
        print(f"[Irene] C4 — Concluída em {_elapsed_c4:.1f}s ({len(classificacoes)} classificações)")
        logger.info("[Irene] C4 concluída em %.1fs", _elapsed_c4)

        # ── C5 — Artefatos ────────────────────────────────────────────────────
        logger.info("[Irene] C5 — Artefatos")
        print("[Irene] C5 — Artefatos (consolidação)")
        try:
            rec, gerados = c5.executar(
                inventario=inventario, perfis=perfis,
                amostragens=amostragens, classificacoes=classificacoes,
                dir_saida=dir_saida_efetivo, config=config,
            )
        except Exception as exc:
            logger.error("[Irene] C5 ERRO FATAL: %s", exc)
            return "IRENE_ERRO_FATAL", {}

        # ── Consolidação ──────────────────────────────────────────────────────
        recomendacao_str = rec.recomendacao.value   # "APROVADO" | "ALERTA" | "BLOQUEADO"
        estado = f"IRENE_{recomendacao_str}"

        abas_total = len(perfis)
        abas_classificadas = len([c for c in classificacoes if c is not None]) if classificacoes else 0
        tokens_total = sum(
            getattr(c, "tokens_prompt", 0) + getattr(c, "tokens_resposta", 0)
            for c in (classificacoes or [])
            if c is not None
        )

        metricas: dict = {
            "score_consolidado": rec.score_consolidado,
            "recomendacao": recomendacao_str,
            "versao_irene": versao_irene,
            "abas_classificadas": abas_classificadas,
            "abas_total": abas_total,
            "tokens_total": tokens_total,
            "dir_saida": str(dir_saida_efetivo),
            "artefatos": {
                "catalog":    str(dir_saida_efetivo / "irene_catalog.yaml"),
                "confidence": str(dir_saida_efetivo / "irene_confidence.md"),
                "formulas":   str(dir_saida_efetivo / "irene_formulas.md"),
                "extrato":    str(dir_saida_efetivo / f"irene_extrato_{modulo}.md"),
                "log":        str(dir_saida_efetivo / "irene_execution.log"),
            },
        }

        logger.info(
            "[Irene] Pipeline concluído — estado=%s score=%.4f abas=%d/%d",
            estado, rec.score_consolidado, abas_classificadas, abas_total,
        )
        return estado, metricas

    except Exception as exc:
        logger.error("[Irene] Falha não capturada: %s", exc, exc_info=True)
        return "IRENE_ERRO_FATAL", {}


def verificar_catalogo_existente(
    module_id: str,
    workspace_path: Path,
) -> tuple[bool, str]:
    """
    Verifica se existe um catálogo Irene válido (>= VERSAO_IRENE_MINIMA)
    para este módulo no workspace.

    Retorno:
        (existe_valido: bool, caminho_catalogo: str)
        Se não existe ou está desatualizado: (False, "")
    """
    # Procura o catálogo nos diretórios de saída possíveis.
    # O orquestrador chama executar_irene(dir_saida=workspace_path), então
    # dir_saida_efetivo = workspace_path / module_id — esse é o caminho real.
    # Os candidatos IRENE_OUT são mantidos para compatibilidade retroativa.
    candidatos = [
        workspace_path / module_id / "irene_catalog.yaml",
        workspace_path / "IRENE_OUT" / module_id / "irene_catalog.yaml",
        workspace_path.parent / "IRENE_OUT" / module_id / "irene_catalog.yaml",
    ]

    for caminho in candidatos:
        if not caminho.exists():
            continue
        try:
            import yaml
            dados = yaml.safe_load(caminho.read_text(encoding="utf-8"))
            versao = dados.get("versao_irene", "0.0.0")
            if _versao_valida(versao):
                logger.info(
                    "[Irene] Catálogo existente encontrado: %s (versão %s)",
                    caminho, versao,
                )
                return True, str(caminho)
            else:
                logger.warning(
                    "[Irene] Catálogo desatualizado em %s (versão %s < mínima %s). "
                    "Reexecutar Irene.",
                    caminho, versao, VERSAO_IRENE_MINIMA,
                )
        except Exception as exc:
            logger.warning("[Irene] Falha ao ler catálogo em %s: %s", caminho, exc)

    return False, ""


def _versao_valida(versao: str) -> bool:
    """Retorna True se versao >= VERSAO_IRENE_MINIMA (comparação semântica simples)."""
    def _partes(v: str) -> tuple[int, ...]:
        try:
            return tuple(int(x) for x in v.split("."))
        except ValueError:
            return (0,)

    return _partes(versao) >= _partes(VERSAO_IRENE_MINIMA)


def _derivar_manifesto_irene(cycle_id: str, workspace_path: Path) -> Path:
    """
    Deriva o irene_manifesto.yaml a partir do conteúdo do workspace.

    Estrutura esperada no workspace:
        input/MOD_010/XLSX/   → arquivos .xlsx
        input/MOD_010/CSV/    → arquivos .csv (listados em arquivos_csv para C2/C3)

    O CATALOGO.json é opcional — se não existir, C3 opera em modo degradado.
    """
    module_id = cycle_id.split("_A")[0]  # MOD_010_A1_... → MOD_010
    input_dir = workspace_path / "input" / module_id

    xlsx_dir = input_dir / "XLSX"
    csv_dir = input_dir / "CSV"

    arquivos_xlsx = sorted(xlsx_dir.glob("*.xlsx")) if xlsx_dir.exists() else []
    arquivos_csv = sorted(csv_dir.glob("*.csv")) if csv_dir.exists() else []
    # CATALOGO.json pode estar direto em CSV/ ou em CSV/_CATALOGO/
    catalogo_path = csv_dir / "CATALOGO.json"
    if not catalogo_path.exists():
        catalogo_path = csv_dir / "_CATALOGO" / "CATALOGO.json"

    manifesto = {
        "modulo": module_id,
        "data_entrega": date.today().isoformat(),
        "raiz_projeto": str(workspace_path),
        "arquivos_xlsx": [
            {
                "nome": f.name,
                "caminho_relativo": str(f.relative_to(workspace_path)),
            }
            for f in arquivos_xlsx
        ],
        "arquivos_csv": [
            {
                "nome": f.name,
                "caminho_relativo": str(f.relative_to(workspace_path)),
            }
            for f in arquivos_csv
        ],
    }

    if catalogo_path.exists():
        manifesto["catalogo_json"] = {
            "caminho_relativo": str(catalogo_path.relative_to(workspace_path))
        }

    # Gravar em cycles/{cycle_id}/irene_manifesto.yaml
    manifesto_path = workspace_path / "cycles" / cycle_id / "irene_manifesto.yaml"
    manifesto_path.parent.mkdir(parents=True, exist_ok=True)
    manifesto_path.write_text(
        yaml.dump(manifesto, allow_unicode=True, default_flow_style=False),
        encoding="utf-8",
    )
    logger.info("[Irene] Manifesto derivado gravado em %s", manifesto_path)
    return manifesto_path


def copiar_catalogo_para_ciclo(
    metricas: dict,
    cycle_id: str,
    workspace_path: Path,
) -> Path | None:
    """
    Copia irene_catalog.yaml do IRENE_OUT para cycles/{cycle_id}/
    para que o Orquestrador o inclua no contexto de definir_tasks_watson.

    Retorna o caminho do catálogo copiado ou None se não encontrado.
    """
    artefatos = metricas.get("artefatos", {})
    catalog_source = artefatos.get("catalog", "")

    if not catalog_source:
        logger.warning("[Irene] Catálogo não encontrado nas métricas de retorno.")
        return None

    source_path = Path(catalog_source)
    if not source_path.exists():
        logger.warning("[Irene] Catálogo em %s não existe em disco.", source_path)
        return None

    dest_dir = workspace_path / "cycles" / cycle_id
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_path = dest_dir / "irene_catalog.yaml"

    shutil.copy2(str(source_path), str(dest_path))
    logger.info("[Irene] Catálogo copiado para %s", dest_path)
    return dest_path


def arquivar_inputs_existentes(input_dir: Path) -> None:
    """
    Se input_dir não estiver vazio, move conteúdo para
    input_dir/_ARCHIVE/YYYYMMDD_HHMMSS/ antes de nova execução.
    """
    if not input_dir.exists():
        return
    itens = [i for i in input_dir.iterdir() if i.name != "_ARCHIVE"]
    if not itens:
        return
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    archive = input_dir / "_ARCHIVE" / timestamp
    archive.mkdir(parents=True, exist_ok=True)
    for item in itens:
        item.rename(archive / item.name)
    logger.info("[Irene] Inputs existentes arquivados em %s", archive)
