"""
orchestrator/stranger_room.py — Protocolo de persistência da Stranger's Room.
Imutabilidade (Artigo 11), frontmatter YAML, content_hash.
Referência normativa: RF-SR-01 a RF-SR-06 (PRD v0.1), Bloco 10 (SDD v0.1)
"""
from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path

import frontmatter

from diogenes.config import DiogenesConfig
from diogenes.models import DecisaoFinal
from diogenes.orchestrator.exceptions import StrangerRoomValidationError, StrangerRoomWriteError

_PREFIXOS: dict[str, str] = {
    "apresentacao":  "01",
    "critica_r1":    "02",
    "resposta_r1":   "03",
    "critica_r2":    "04",
    "resposta_r2":   "05",
    "decisao_final": "99",
}

_NOMES: dict[str, str] = {
    "apresentacao":  "apresentacao",
    "critica_r1":    "critica_mycroft_r1",
    "resposta_r1":   "resposta_r1",
    "critica_r2":    "critica_mycroft_r2",
    "resposta_r2":   "resposta_r2",
    "decisao_final": "decisao_final",
}

_ROLES: dict[str, str] = {
    "mycroft":  "Auditor Chefe",
    "watson":   "Auditor de Integridade Técnica",
    "sherlock": "Auditor de Validação Metodológica CBS",
}


class StrangerRoom:
    def __init__(self, cycle_id: str, stranger_room_dir: Path, cfg: DiogenesConfig) -> None:
        self._cycle_id = cycle_id
        self._sr_dir = stranger_room_dir
        self._cfg = cfg

    # ── Escrita ───────────────────────────────────────────────

    def escrever_apresentacao(self, fase: str, author: str, content: str) -> Path:
        return self._escrever(fase, "apresentacao", None, author, content, {})

    def escrever_critica(self, fase: str, rodada: int, author: str, content: str) -> Path:
        return self._escrever(fase, f"critica_r{rodada}", rodada, author, content, {})

    def escrever_resposta(self, fase: str, rodada: int, author: str, content: str) -> Path:
        return self._escrever(fase, f"resposta_r{rodada}", rodada, author, content, {})

    def escrever_decisao_final(self, fase: str, author: str, decisao: DecisaoFinal) -> Path:
        campos: dict = {"mycroft_overruled": decisao.mycroft_overruled}
        if fase == "watson_integridade":
            campos["has_critical_alert"] = decisao.has_critical_alert
            campos["critical_alerts_count"] = decisao.critical_alerts_count
        if fase == "sherlock_validacao":
            campos["has_dilemma"] = decisao.has_dilemma
            campos["dilemmas_count"] = decisao.dilemmas_count
        return self._escrever(fase, "decisao_final", None, author, decisao.texto, campos)

    # ── Leitura ───────────────────────────────────────────────

    def ler_apresentacao(self, fase: str) -> str:
        """Retorna o conteúdo (sem frontmatter YAML) do arquivo de apresentação da fase."""
        path = self._path_para(fase, "apresentacao")
        if not path.exists():
            return ""
        post = frontmatter.load(str(path))
        return post.content

    def ler_decisao_final(self, fase: str) -> DecisaoFinal:
        path = self._path_para(fase, "decisao_final")
        if not path.exists():
            raise FileNotFoundError(f"Decisão final ausente: '{path}'")
        post = frontmatter.load(str(path))
        m = post.metadata
        return DecisaoFinal(
            texto=post.content,
            mycroft_overruled=bool(m.get("mycroft_overruled")),
            has_critical_alert=bool(m.get("has_critical_alert")),
            critical_alerts_count=int(m.get("critical_alerts_count") or 0),
            has_dilemma=bool(m.get("has_dilemma")),
            dilemmas_count=int(m.get("dilemmas_count") or 0),
        )

    def listar_arquivos_fase(self, fase: str) -> list[Path]:
        fase_dir = self._sr_dir / fase
        return sorted(fase_dir.glob("*.md")) if fase_dir.is_dir() else []

    def validar_fase_completa(self, fase: str) -> None:
        nomes = {p.name for p in self.listar_arquivos_fase(fase)}
        obrig = {"01_apresentacao.md", "99_decisao_final.md"}
        faltando = obrig - nomes
        if faltando:
            raise StrangerRoomValidationError(
                f"Fase '{fase}' incompleta. Faltando: {sorted(faltando)}"
            )

    # ── Núcleo privado ────────────────────────────────────────

    def _escrever(self, fase: str, file_type: str, round_num: int | None,
                  author: str, content: str, campos_semanticos: dict) -> Path:
        path = self._path_para(fase, file_type)
        if path.exists():
            raise StrangerRoomWriteError(
                f"Tentativa de sobrescrever arquivo imutável: '{path}' (Artigo 11)."
            )
        now = datetime.now(UTC).strftime(self._cfg.persistencia.timestamp_iso_format)
        fm: dict = {
            "cycle_id": self._cycle_id,
            "phase": fase,
            "file_type": file_type,
            "round": round_num,
            "author": author,
            "role": _ROLES[author],
            "timestamp_utc": now,
            "content_hash": _calcular_hash(content),
            "has_critical_alert": None,
            "critical_alerts_count": None,
            "has_dilemma": None,
            "dilemmas_count": None,
            "mycroft_overruled": None,
        }
        fm.update(campos_semanticos)
        post = frontmatter.Post(content=content, **fm)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(frontmatter.dumps(post) + "\n",
                        encoding=self._cfg.persistencia.encoding)
        return path

    def _path_para(self, fase: str, file_type: str) -> Path:
        prefixo = _PREFIXOS[file_type]
        nome = _NOMES[file_type]
        return self._sr_dir / fase / f"{prefixo}_{nome}.md"


def _calcular_hash(content: str) -> str:
    return "sha256:" + hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]
