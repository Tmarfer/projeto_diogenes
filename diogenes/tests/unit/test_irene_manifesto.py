"""
tests/unit/test_irene_manifesto.py — DVA-CBS | Projeto Diógenes
Testa _derivar_manifesto_irene() com workspace sintético.
"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml


class TestDerivarManifestoIrene:

    def test_manifesto_basico_com_xlsx(self, tmp_path: Path) -> None:
        """Workspace com XLSXs gera manifesto correto."""
        from diogenes.irene import _derivar_manifesto_irene

        workspace = tmp_path / "workspace"
        xlsx_dir = workspace / "input" / "MOD_010" / "XLSX"
        xlsx_dir.mkdir(parents=True)
        (xlsx_dir / "planilha_a.xlsx").write_bytes(b"PK\x03\x04fake")
        (xlsx_dir / "planilha_b.xlsx").write_bytes(b"PK\x03\x04fake")
        csv_dir = workspace / "input" / "MOD_010" / "CSV"
        csv_dir.mkdir(parents=True)

        cycle_id = "MOD_010_A1_20260530T120000Z"
        resultado = _derivar_manifesto_irene(cycle_id, workspace)

        assert resultado.exists()
        dados = yaml.safe_load(resultado.read_text(encoding="utf-8"))
        assert dados["modulo"] == "MOD_010"
        assert len(dados["arquivos_xlsx"]) == 2
        assert dados["arquivos_csv"] == []
        assert "catalogo_json" not in dados

    def test_manifesto_inclui_csvs(self, tmp_path: Path) -> None:
        """CSVs presentes em CSV/ são listados em arquivos_csv para C2/C3."""
        from diogenes.irene import _derivar_manifesto_irene

        workspace = tmp_path / "workspace"
        xlsx_dir = workspace / "input" / "MOD_010" / "XLSX"
        xlsx_dir.mkdir(parents=True)
        (xlsx_dir / "planilha.xlsx").write_bytes(b"PK\x03\x04fake")
        csv_dir = workspace / "input" / "MOD_010" / "CSV"
        csv_dir.mkdir(parents=True)
        (csv_dir / "planilha__aba1.csv").write_text("col\n1", encoding="utf-8")
        (csv_dir / "planilha__aba2.csv").write_text("col\n2", encoding="utf-8")

        cycle_id = "MOD_010_A1_20260530T120000Z"
        resultado = _derivar_manifesto_irene(cycle_id, workspace)

        dados = yaml.safe_load(resultado.read_text(encoding="utf-8"))
        assert len(dados["arquivos_csv"]) == 2
        nomes = {e["nome"] for e in dados["arquivos_csv"]}
        assert "planilha__aba1.csv" in nomes
        assert "planilha__aba2.csv" in nomes
        for entry in dados["arquivos_csv"]:
            assert entry["caminho_relativo"].startswith("input/MOD_010/CSV/")

    def test_manifesto_com_catalogo_json(self, tmp_path: Path) -> None:
        """CATALOGO.json presente aparece no manifesto."""
        from diogenes.irene import _derivar_manifesto_irene

        workspace = tmp_path / "workspace"
        xlsx_dir = workspace / "input" / "MOD_010" / "XLSX"
        xlsx_dir.mkdir(parents=True)
        (xlsx_dir / "base.xlsx").write_bytes(b"PK\x03\x04fake")
        catalogo_dir = workspace / "input" / "MOD_010" / "CSV" / "_CATALOGO"
        catalogo_dir.mkdir(parents=True)
        (catalogo_dir / "CATALOGO.json").write_text('{"versao": "1.0"}', encoding="utf-8")

        cycle_id = "MOD_010_A1_20260530T120000Z"
        resultado = _derivar_manifesto_irene(cycle_id, workspace)

        dados = yaml.safe_load(resultado.read_text(encoding="utf-8"))
        assert "catalogo_json" in dados
        assert "CATALOGO.json" in dados["catalogo_json"]["caminho_relativo"]

    def test_manifesto_xlsx_vazio(self, tmp_path: Path) -> None:
        """Workspace sem XLSXs gera manifesto com lista vazia."""
        from diogenes.irene import _derivar_manifesto_irene

        workspace = tmp_path / "workspace"
        xlsx_dir = workspace / "input" / "MOD_010" / "XLSX"
        xlsx_dir.mkdir(parents=True)
        csv_dir = workspace / "input" / "MOD_010" / "CSV"
        csv_dir.mkdir(parents=True)

        cycle_id = "MOD_010_A1_20260530T120000Z"
        resultado = _derivar_manifesto_irene(cycle_id, workspace)

        dados = yaml.safe_load(resultado.read_text(encoding="utf-8"))
        assert dados["arquivos_xlsx"] == []

    def test_manifesto_xlsx_dir_inexistente(self, tmp_path: Path) -> None:
        """Workspace sem diretório XLSX/ gera manifesto sem erro."""
        from diogenes.irene import _derivar_manifesto_irene

        workspace = tmp_path / "workspace"
        workspace.mkdir(parents=True)

        cycle_id = "MOD_010_A1_20260530T120000Z"
        resultado = _derivar_manifesto_irene(cycle_id, workspace)

        dados = yaml.safe_load(resultado.read_text(encoding="utf-8"))
        assert dados["modulo"] == "MOD_010"
        assert dados["arquivos_xlsx"] == []

    def test_cycle_id_extrapolacao_modulo(self, tmp_path: Path) -> None:
        """cycle_id com diferentes formatos extrai module_id correto."""
        from diogenes.irene import _derivar_manifesto_irene

        workspace = tmp_path / "workspace"
        workspace.mkdir(parents=True)

        cycle_id = "MOD_042_A2_20260530T120000Z"
        resultado = _derivar_manifesto_irene(cycle_id, workspace)
        dados = yaml.safe_load(resultado.read_text(encoding="utf-8"))
        assert dados["modulo"] == "MOD_042"


class TestVerificarCatalogoExistente:

    def test_detecta_catalogo_em_workspace_modulo(self, tmp_path: Path) -> None:
        """Catálogo em workspace/MOD_010/ é detectado (caminho real do orquestrador)."""
        from diogenes.irene import verificar_catalogo_existente

        workspace = tmp_path / "workspace"
        catalog_dir = workspace / "MOD_010"
        catalog_dir.mkdir(parents=True)
        catalog = catalog_dir / "irene_catalog.yaml"
        catalog.write_text(
            "modulo: MOD_010\nversao_irene: 1.3.0\nscore_consolidado: 0.97\n",
            encoding="utf-8",
        )

        existe, caminho = verificar_catalogo_existente("MOD_010", workspace)

        assert existe is True
        assert "MOD_010" in caminho
        assert caminho.endswith("irene_catalog.yaml")

    def test_detecta_catalogo_em_irene_out(self, tmp_path: Path) -> None:
        """Catálogo em workspace/IRENE_OUT/MOD_010/ também é detectado (compatibilidade)."""
        from diogenes.irene import verificar_catalogo_existente

        workspace = tmp_path / "workspace"
        catalog_dir = workspace / "IRENE_OUT" / "MOD_010"
        catalog_dir.mkdir(parents=True)
        catalog = catalog_dir / "irene_catalog.yaml"
        catalog.write_text(
            "modulo: MOD_010\nversao_irene: 1.3.0\nscore_consolidado: 0.95\n",
            encoding="utf-8",
        )

        existe, caminho = verificar_catalogo_existente("MOD_010", workspace)

        assert existe is True
        assert "irene_catalog.yaml" in caminho

    def test_sample_c4_dev_limita_abas(
        self, env_vars, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from diogenes.config import get_config
        from diogenes.irene import _sample_c4_dev

        monkeypatch.setenv("DIOGENES_DEV_MODE", "true")
        monkeypatch.setenv("IRENE_C4_SAMPLE_N", "2")
        get_config.cache_clear()

        resultado = _sample_c4_dev(["p1", "p2", "p3"], ["a1", "a2", "a3"])

        assert resultado["sample_mode"] is True
        assert resultado["sample_n"] == 2
        assert resultado["abas_total_original"] == 3
        assert resultado["perfis"] == ["p1", "p2"]
        assert resultado["amostragens"] == ["a1", "a2"]

    def test_sample_c4_ignorado_fora_dev_mode(
        self, env_vars, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from diogenes.config import get_config
        from diogenes.irene import _sample_c4_dev

        monkeypatch.setenv("DIOGENES_DEV_MODE", "false")
        monkeypatch.setenv("IRENE_C4_SAMPLE_N", "2")
        get_config.cache_clear()

        resultado = _sample_c4_dev(["p1", "p2", "p3"], ["a1", "a2", "a3"])

        assert resultado["sample_mode"] is False
        assert resultado["sample_n"] == 0
        assert resultado["perfis"] == ["p1", "p2", "p3"]

    def test_catalogo_ausente_retorna_false(self, tmp_path: Path) -> None:
        """Sem catálogo, retorna (False, '')."""
        from diogenes.irene import verificar_catalogo_existente

        workspace = tmp_path / "workspace"
        workspace.mkdir()

        existe, caminho = verificar_catalogo_existente("MOD_010", workspace)

        assert existe is False
        assert caminho == ""

    def test_catalogo_versao_antiga_retorna_false(self, tmp_path: Path) -> None:
        """Catálogo com versão desatualizada não é reutilizado."""
        from diogenes.irene import verificar_catalogo_existente

        workspace = tmp_path / "workspace"
        catalog_dir = workspace / "MOD_010"
        catalog_dir.mkdir(parents=True)
        catalog = catalog_dir / "irene_catalog.yaml"
        catalog.write_text(
            "modulo: MOD_010\nversao_irene: 0.1.0\nscore_consolidado: 0.80\n",
            encoding="utf-8",
        )

        existe, caminho = verificar_catalogo_existente("MOD_010", workspace)

        assert existe is False


class TestCopiarCatalogoParaCiclo:

    def test_copia_catalogo_existente(self, tmp_path: Path) -> None:
        """Catálogo existente é copiado para cycles/."""
        from diogenes.irene import copiar_catalogo_para_ciclo

        workspace = tmp_path / "workspace"
        irene_out = workspace / "IRENE_OUT" / "MOD_010"
        irene_out.mkdir(parents=True)
        catalog_source = irene_out / "irene_catalog.yaml"
        catalog_source.write_text("modulo: MOD_010\nscore_consolidado: 0.97\n", encoding="utf-8")

        metricas = {"artefatos": {"catalog": str(catalog_source)}}
        resultado = copiar_catalogo_para_ciclo(metricas, "CYC_001", workspace)

        assert resultado is not None
        assert resultado.exists()
        assert resultado.name == "irene_catalog.yaml"
        assert "CYC_001" in str(resultado)

    def test_catalogo_inexistente_retorna_none(self, tmp_path: Path) -> None:
        """Catálogo não encontrado retorna None sem erro."""
        from diogenes.irene import copiar_catalogo_para_ciclo

        workspace = tmp_path / "workspace"
        workspace.mkdir()
        metricas = {"artefatos": {"catalog": "/inexistente/irene_catalog.yaml"}}
        resultado = copiar_catalogo_para_ciclo(metricas, "CYC_001", workspace)
        assert resultado is None

    def test_metricas_sem_artefatos_retorna_none(self, tmp_path: Path) -> None:
        """Métricas sem campo artefatos retorna None."""
        from diogenes.irene import copiar_catalogo_para_ciclo

        workspace = tmp_path / "workspace"
        workspace.mkdir()
        resultado = copiar_catalogo_para_ciclo({}, "CYC_001", workspace)
        assert resultado is None


class TestArquivarInputsExistentes:

    def test_arquiva_inputs_com_conteudo(self, tmp_path: Path) -> None:
        """Inputs existentes são movidos para _ARCHIVE/."""
        from diogenes.irene import arquivar_inputs_existentes

        input_dir = tmp_path / "input"
        input_dir.mkdir()
        (input_dir / "file1.csv").write_text("data", encoding="utf-8")
        (input_dir / "file2.csv").write_text("data", encoding="utf-8")

        arquivar_inputs_existentes(input_dir)

        assert not (input_dir / "file1.csv").exists()
        assert not (input_dir / "file2.csv").exists()
        archive = input_dir / "_ARCHIVE"
        assert archive.exists()
        subdirs = list(archive.iterdir())
        assert len(subdirs) == 1
        assert (subdirs[0] / "file1.csv").exists()

    def test_dir_vazio_nao_faz_nada(self, tmp_path: Path) -> None:
        """Diretório vazio não cria _ARCHIVE."""
        from diogenes.irene import arquivar_inputs_existentes

        input_dir = tmp_path / "input"
        input_dir.mkdir()

        arquivar_inputs_existentes(input_dir)
        assert not (input_dir / "_ARCHIVE").exists()

    def test_dir_inexistente_nao_faz_nada(self, tmp_path: Path) -> None:
        """Diretório inexistente não gera erro."""
        from diogenes.irene import arquivar_inputs_existentes

        input_dir = tmp_path / "inexistente"
        arquivar_inputs_existentes(input_dir)  # não levanta exceção
