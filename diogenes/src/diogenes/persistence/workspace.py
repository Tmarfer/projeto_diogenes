"""
persistence/workspace.py — DVA-CBS | Projeto Diógenes
Criação e gestão dos diretórios de ciclo no workspace.

WorkspaceManager é separado do MotorStart para permitir testes
independentes da criação de estrutura (SDD Bloco 7.5).

Usa pathlib.Path exclusivamente — sem os.path (RNF-PORT-01).
"""

from __future__ import annotations

import shutil
from pathlib import Path

from diogenes.models import InputFileInfo


class WorkspaceManager:

    def __init__(self, workspace_root: Path) -> None:
        self._root = workspace_root

    def criar_estrutura_ciclo(self, cycle_id: str) -> Path:
        """
        Cria o diretório de trabalho do ciclo com toda a estrutura interna.
        Levanta FileExistsError se o diretório já existir.
        """
        cycle_dir = self._root / "cycles" / cycle_id
        if cycle_dir.exists():
            raise FileExistsError(
                f"Diretório do ciclo já existe: '{cycle_dir}'. "
                f"Verifique o audit_index."
            )
        for subdir in [
            "inputs",
            "stranger_room/watson_integridade",
            "stranger_room/sherlock_validacao",
            "output",
            "_runtime",
            "_runtime/llm_calls",
        ]:
            (cycle_dir / subdir).mkdir(parents=True, exist_ok=False)
        return cycle_dir

    def get_cycle_dir(self, cycle_id: str) -> Path:
        cycle_dir = self._root / "cycles" / cycle_id
        if not cycle_dir.is_dir():
            raise FileNotFoundError(
                f"Diretório do ciclo não encontrado: '{cycle_dir}'."
            )
        return cycle_dir

    def copiar_inputs(self, files: list[InputFileInfo], cycle_dir: Path) -> None:
        """Copia arquivos de input para inputs/ do ciclo (sem alterar originais)."""
        inputs_dir = cycle_dir / "inputs"
        for f in files:
            dest = inputs_dir / f.rel_path
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(f.rel_path.parent / f.name if False else f.rel_path, dest)

    def inicializar_workspace(self) -> None:
        """Cria input/ e cycles/ se não existirem. Idempotente."""
        (self._root / "input").mkdir(parents=True, exist_ok=True)
        (self._root / "cycles").mkdir(parents=True, exist_ok=True)
