"""
tests/unit/test_bench_delivery.py — DVA-CBS | Projeto Diógenes
Testes do loader multi-tipo da bancada (_load_delivery) e dos prompts estendidos.
"""
from __future__ import annotations

import json
from pathlib import Path

from diogenes.bench.pipeline import BenchPipeline
from diogenes.bench.prompt_builder import (
    build_user_mycroft_tasks,
    build_user_sherlock,
    build_user_watson_analise,
    rotulo_tipo,
)


def _make_delivery(root: Path) -> Path:
    """Monta uma entrega com um arquivo de cada tipo + ruído a ser ignorado."""
    delivery = root / "MOD_X" / "2026_04_27"
    delivery.mkdir(parents=True)
    (delivery / "metodologia.md").write_text("# Metodologia\nRegra de negócio.", encoding="utf-8")
    (delivery / "extracao.sql").write_text("select * from base;", encoding="utf-8")
    (delivery / "transforma.py").write_text("x = 1\n", encoding="utf-8")
    (delivery / "dados.csv").write_text("id;valor\n1;10\n", encoding="utf-8")
    (delivery / "planilha.xlsx").write_bytes(b"PK\x03\x04fake")
    nb = {
        "cells": [
            {"cell_type": "code", "source": "print(1)", "metadata": {}, "outputs": [], "execution_count": None}
        ],
        "metadata": {},
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    (delivery / "analise.ipynb").write_text(json.dumps(nb), encoding="utf-8")
    # Ruído: diretório e arquivos de metadados que NÃO devem ser analisados.
    logs = delivery / "03_LOGS"
    logs.mkdir()
    (logs / "ignorar.md").write_text("não analisar", encoding="utf-8")
    (delivery / "metadados.json").write_text("{}", encoding="utf-8")
    (delivery / "CATALOGO.json").write_text("{}", encoding="utf-8")
    return delivery


def _pipeline(module: str, delivery: Path, out: Path, **kw) -> BenchPipeline:
    return BenchPipeline(module, delivery_dir=delivery, output_dir=out, **kw)


def test_rotulo_tipo():
    assert rotulo_tipo("a.sql") == "sql"
    assert rotulo_tipo("a.ipynb") == "notebook"
    assert rotulo_tipo("a.py") == "script"
    assert rotulo_tipo("a.csv") == "csv"
    assert rotulo_tipo("a.xlsx") == "planilha"
    assert rotulo_tipo("a.md") == "documento"


def test_load_delivery_cobre_tipos_e_ignora_ruido(env_vars, workspace, tmp_path):
    delivery = _make_delivery(tmp_path)
    pipe = _pipeline("MOD_X", delivery, tmp_path / "out")

    files = pipe._load_delivery()
    nomes = {name for name, _t, _c in files}
    tipos = {tipo for _n, tipo, _c in files}

    # Um de cada tipo analisável
    assert tipos == {"documento", "sql", "notebook", "script", "csv", "planilha"}
    # Ruído excluído
    assert not any("03_LOGS" in n for n in nomes)
    assert "metadados.json" not in nomes
    assert "CATALOGO.json" not in nomes
    # Ordem: documentação antes de csv (cadeia de produção)
    ordem = [tipo for _n, tipo, _c in files]
    assert ordem.index("documento") < ordem.index("csv")


def test_amostrar_por_tipo_garante_um_de_cada():
    files = [
        ("a.csv", "csv", ""), ("b.csv", "csv", ""), ("c.csv", "csv", ""),
        ("d.sql", "sql", ""), ("e.md", "documento", ""),
    ]
    amostra = BenchPipeline._amostrar_por_tipo(files, 3)
    tipos = {t for _n, t, _c in amostra}
    assert len(amostra) == 3
    assert tipos == {"csv", "sql", "documento"}


def test_prompt_watson_inclui_tipo_e_cerca():
    out = build_user_watson_analise("extracao.sql", "select 1;", "sql")
    assert "Tipo identificado:** sql" in out
    assert "```sql" in out


def test_prompt_sherlock_injeta_metodologia_e_corpus():
    out = build_user_sherlock("consolidado watson", "decisao mycroft", "META", "CORPUS")
    assert "Metodologia e regra de negócio" in out
    assert "META" in out
    assert "Arcabouço jurídico curado" in out
    assert "CORPUS" in out


def test_prompt_mycroft_tasks_inclui_docs():
    out = build_user_mycroft_tasks("- a.sql [sql] (1 linhas)", "MOD_X", "briefing do modulo")
    assert "Inventário da entrega" in out
    assert "briefing do modulo" in out
