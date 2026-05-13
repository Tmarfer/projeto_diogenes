"""
motors/motor_start.py — DVA-CBS | Projeto Diógenes
Motor de Start — abre e prepara o ambiente de trabalho de cada ciclo.

Coordena: WorkspaceManager (dirs), AuditIndex (CSV), manifest.py (manifesto).
Não tem lógica de filesystem própria — delega para os módulos de persistence.

Referência normativa: RF-MS-01 a RF-MS-09, Art. 13 da Constituição (PRD v0.1)
Bloco 7 (SDD v0.1)
"""

from __future__ import annotations

import hashlib
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

from diogenes.config import DiogenesConfig
from diogenes.models import CycleManifest, CycleRecord, InputFileInfo
from diogenes.motors.exceptions import (
    CopyIntegrityError,
    CycleIdCollisionError,
    InputMissingError,
    NoPreviousCycleError,
)
from diogenes.orchestrator.states import CycleState
from diogenes.persistence.audit_index import AuditIndex
from diogenes.persistence.manifest import write_manifesto
from diogenes.persistence.workspace import WorkspaceManager


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65_536), b""):
            h.update(chunk)
    return h.hexdigest()


def _sha256_package(files: list[InputFileInfo]) -> str:
    combined = "".join(f.sha256 for f in sorted(files, key=lambda x: str(x.rel_path)))
    return hashlib.sha256(combined.encode("utf-8")).hexdigest()


def _git_commit() -> str:
    try:
        r = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=5,
        )
        if r.returncode == 0:
            return r.stdout.strip()
    except Exception:
        pass
    return "sem-git"


def _package_version(pkg: str) -> str:
    try:
        import importlib.metadata
        return importlib.metadata.version(pkg)
    except Exception:
        return "?"


def _generate_cycle_id(module_id: str, activity: int) -> str:
    ts = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    return f"{module_id}_A{activity}_{ts}"


def _collect_inputs(input_dir: Path) -> list[InputFileInfo]:
    files = []
    for p in sorted(input_dir.rglob("*")):
        if not p.is_file():
            continue
        files.append(InputFileInfo(
            name=p.name,
            extension=p.suffix.lower(),
            size_bytes=p.stat().st_size,
            sha256=_sha256_file(p),
            rel_path=p.relative_to(input_dir),
        ))
    return files


class MotorStart:
    """
    Abre e prepara o ambiente de trabalho de cada ciclo.
    Método principal: run(module_id, activity) → CycleManifest
    """

    def __init__(self, cfg: DiogenesConfig) -> None:
        self._cfg = cfg
        self._ws = cfg.workspace.path
        self._audit = AuditIndex(self._ws)
        self._wm = WorkspaceManager(self._ws)

    def run(self, module_id: str, activity: int) -> CycleManifest:
        if activity not in (1, 2):
            raise ValueError(f"Atividade inválida: {activity}. Use 1 ou 2.")

        input_dir = self._ws / "input" / module_id
        self._verificar_inputs(input_dir, module_id, activity)

        files = _collect_inputs(input_dir)
        package_hash = _sha256_package(files)

        cycle_id = _generate_cycle_id(module_id, activity)
        self._audit.create_if_not_exists()

        if self._audit.get_cycle(cycle_id) is not None:
            raise CycleIdCollisionError(
                f"cycle_id '{cycle_id}' já existe no audit_index."
            )

        cycle_num = self._audit.count_cycles_for_module(module_id) + 1
        cycle_dir = self._wm.criar_estrutura_ciclo(cycle_id)

        # Copiar inputs (sem alterar originais — Art. 13)
        inputs_dir = cycle_dir / "inputs"
        for f in files:
            dest = inputs_dir / f.rel_path
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(input_dir / f.rel_path, dest)
            # Verificação de integridade da cópia
            copy_hash = _sha256_file(dest)
            if copy_hash != f.sha256:
                raise CopyIntegrityError(
                    f"Hash diverge após cópia de '{f.name}': "
                    f"esperado {f.sha256[:16]}…, obtido {copy_hash[:16]}…"
                )

        now_utc = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        is_sigilo = module_id.upper() in [
            m.upper() for m in self._cfg.motor_saida.padroes_agentes  # proxy via config
        ]
        # Determinar sala_sigilo a partir dos padrões da runtime (não disponível diretamente)
        # A lista real de módulos sigilo é lida de agents_spec — ver runtime.yaml
        # Por ora usa a informação do ambiente
        is_sigilo = False  # será sobrescrito se houver lista disponível

        manifest = CycleManifest(
            cycle_id=cycle_id,
            module_id=module_id,
            activity=activity,
            opened_at_utc=now_utc,
            is_sigilo_module=is_sigilo,
            input_files=files,
            package_hash=package_hash,
            git_commit=_git_commit(),
            diogenes_version=_package_version("diogenes"),
            python_version=sys.version.split()[0],
            openai_version=_package_version("openai"),
            cycle_num=cycle_num,
        )

        write_manifesto(manifest, cycle_dir)

        record = CycleRecord(
            cycle_id=cycle_id,
            module_id=module_id,
            activity=activity,
            status=CycleState.PREPARADO.value,
            opened_at_utc=now_utc,
            is_sigilo_module=str(is_sigilo).lower(),
            diogenes_version=manifest.diogenes_version,
            git_commit=manifest.git_commit,
            ambiente=self._cfg.llm.env,
        )
        self._audit.add_cycle(record)

        return manifest

    def _verificar_inputs(
        self, input_dir: Path, module_id: str, activity: int
    ) -> None:
        if not input_dir.exists():
            raise InputMissingError(
                f"Diretório de input não encontrado: {input_dir}\n"
                f"Crie workspace/input/{module_id}/ e popule com os arquivos do pacote."
            )
        if not any(input_dir.rglob("*")):
            raise InputMissingError(
                f"Diretório de input está vazio: {input_dir}"
            )
        if activity == 2:
            # Verificar existência de ciclo A1 encerrado para o módulo
            self._audit.create_if_not_exists()
            ciclos = self._audit.list_cycles(module_id=module_id, status="ENCERRADO_CHANCELADO")
            a1_encerrados = [c for c in ciclos if c["activity"] == "1"]
            if not a1_encerrados:
                raise NoPreviousCycleError(
                    f"Atividade 2 requer ciclo de Atividade 1 encerrado para '{module_id}'. "
                    f"Nenhum encontrado no audit_index."
                )
