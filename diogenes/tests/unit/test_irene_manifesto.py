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
        assert "catalogo_json" not in dados

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
