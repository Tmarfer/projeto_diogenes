"""
bench/output_validator.py — DVA-CBS | Projeto Diógenes
Validação estrutural de outputs dos agentes (sem LLM).

Verifica propriedades de formato e completude dos arquivos produzidos pelos agentes
em um ciclo: contadores inteiros, classificações válidas, citações obrigatórias,
seções obrigatórias, ausência de PII literal.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path


# ── Constantes ────────────────────────────────────────────────────────────

_CLASSIFICACOES_VALIDAS = frozenset({
    "ATENDIDO",
    "ATENDIDO_PARCIALMENTE",
    "DIVERGENCIA",
    "ATENCAO",
    "LIMITACAO",
    "NAO_VERIFICAVEL",
})

_IMPACTOS_VALIDOS = frozenset({"Alto", "Médio", "Baixo"})

_RE_PII_CPF   = re.compile(r"\d{3}\.\d{3}\.\d{3}-\d{2}")
_RE_PII_CNPJ  = re.compile(r"\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}")

_RE_CRITICA_COUNTER     = re.compile(r"\*\*Alertas CRITICA:\*\*\s+(.+)")
_RE_RESULTADO_MYCROFT   = re.compile(r"\*\*resultado:\*\*\s+(\S+)")
_RE_OVERRULE            = re.compile(r"\*\*Overrule Mycroft sobre (Watson|Sherlock):\*\*\s+(\S+)")
_RE_CLASSIFICACAO       = re.compile(r"\*\*Classificação:\*\*\s+(\S+)")
_RE_IMPACTO             = re.compile(r"\*\*Impacto potencial:\*\*\s+(\S+)")
_RE_CITACAO_ACORDAO     = re.compile(r"\[Acórdão 2833/2025")
_RE_CITACAO_LC          = re.compile(r"\[LC 214/2025")
_RE_SECAO_10            = re.compile(r"### 10\.(\d+)")
_RE_NOTA_METODOLOGICA   = re.compile(r"Nota metodológica com alteração detectada:")


# ── Dataclasses ───────────────────────────────────────────────────────────

@dataclass
class Violation:
    file: str
    rule: str
    detail: str

    def __str__(self) -> str:
        return f"[{self.file}] {self.rule}: {self.detail}"


@dataclass
class ValidationResult:
    cycle_id: str
    files_checked: int = 0
    violations: list[Violation] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not self.violations

    def by_file(self) -> dict[str, list[Violation]]:
        result: dict[str, list[Violation]] = {}
        for v in self.violations:
            result.setdefault(v.file, []).append(v)
        return result


# ── Ponto de entrada ──────────────────────────────────────────────────────

def validate_cycle(cycle_dir: Path) -> ValidationResult:
    """
    Valida todos os outputs de agentes encontrados no diretório do ciclo.

    Procura recursivamente por arquivos .md com prefixos de agente
    (watson_*, sherlock_*, MC_*) e aplica os validators correspondentes.
    """
    result = ValidationResult(cycle_id=cycle_dir.name)

    if not cycle_dir.is_dir():
        result.violations.append(Violation(
            file="(ciclo)",
            rule="CYCLE_DIR_NOT_FOUND",
            detail=f"Diretório do ciclo não encontrado: {cycle_dir}",
        ))
        return result

    for md_file in sorted(cycle_dir.rglob("*.md")):
        name = md_file.name
        if name.startswith("watson_"):
            result.files_checked += 1
            _validate_watson(md_file, result.violations)
        elif name.startswith("sherlock_"):
            result.files_checked += 1
            _validate_sherlock(md_file, result.violations)
        elif name.startswith("MC_"):
            result.files_checked += 1
            _validate_mycroft(md_file, result.violations)

    return result


# ── Validators por agente ─────────────────────────────────────────────────

def _validate_watson(path: Path, violations: list[Violation]) -> None:
    name = path.name
    text = path.read_text(encoding="utf-8")

    _check_pii(name, text, violations)

    # Contadores CRITICA devem ser inteiros literais
    for m in _RE_CRITICA_COUNTER.finditer(text):
        valor = m.group(1).strip()
        if not valor.isdigit():
            violations.append(Violation(
                file=name,
                rule="WATSON_COUNTER_CRITICA_NAO_INTEIRO",
                detail=f"**Alertas CRITICA:** contém '{valor}' — deve ser inteiro literal (ex: 3).",
            ))

    if name == "watson_consolidado.md":
        if not _RE_NOTA_METODOLOGICA.search(text):
            violations.append(Violation(
                file=name,
                rule="WATSON_CAMPO_NOTA_METODOLOGICA_AUSENTE",
                detail="Campo 'Nota metodológica com alteração detectada:' não encontrado.",
            ))


def _validate_sherlock(path: Path, violations: list[Violation]) -> None:
    name = path.name
    text = path.read_text(encoding="utf-8")

    _check_pii(name, text, violations)

    if name.startswith("sherlock_ponto_"):
        m_class = _RE_CLASSIFICACAO.search(text)
        if m_class:
            classificacao = m_class.group(1).strip().rstrip(".")
            if classificacao not in _CLASSIFICACOES_VALIDAS:
                violations.append(Violation(
                    file=name,
                    rule="SHERLOCK_CLASSIFICACAO_INVALIDA",
                    detail=f"'{classificacao}' não é um dos 6 valores válidos.",
                ))
            if classificacao == "DIVERGENCIA":
                if not _RE_CITACAO_ACORDAO.search(text) and not _RE_CITACAO_LC.search(text):
                    violations.append(Violation(
                        file=name,
                        rule="SHERLOCK_DIVERGENCIA_SEM_CITACAO",
                        detail="DIVERGENCIA sem citação [Acórdão 2833/2025 | ou [LC 214/2025 |.",
                    ))
        else:
            violations.append(Violation(
                file=name,
                rule="SHERLOCK_CAMPO_CLASSIFICACAO_AUSENTE",
                detail="Campo '**Classificação:**' não encontrado.",
            ))

        m_imp = _RE_IMPACTO.search(text)
        if m_imp:
            impacto = m_imp.group(1).strip().rstrip(".")
            if impacto not in _IMPACTOS_VALIDOS:
                violations.append(Violation(
                    file=name,
                    rule="SHERLOCK_IMPACTO_INVALIDO",
                    detail=f"Impacto potencial '{impacto}' deve ser Alto, Médio ou Baixo.",
                ))

    if name == "sherlock_consolidado.md":
        secoes_presentes = {int(m.group(1)) for m in _RE_SECAO_10.finditer(text)}
        for i in range(1, 12):
            if i not in secoes_presentes:
                violations.append(Violation(
                    file=name,
                    rule="SHERLOCK_SECAO_RELATORIO_AUSENTE",
                    detail=f"Seção 10.{i} do Relatório Estruturado não encontrada.",
                ))
        if "## 11." not in text and "```json" not in text:
            violations.append(Violation(
                file=name,
                rule="SHERLOCK_JSON_OCORRENCIAS_AUSENTE",
                detail="Seção 11 (JSON de ocorrências para dashboard) não encontrada.",
            ))


def _validate_mycroft(path: Path, violations: list[Violation]) -> None:
    name = path.name
    text = path.read_text(encoding="utf-8")

    _check_pii(name, text, violations)

    if name.startswith("MC_avaliacao_"):
        m = _RE_RESULTADO_MYCROFT.search(text)
        if m:
            resultado = m.group(1).strip()
            if resultado not in ("APROVADO", "CRITICA"):
                violations.append(Violation(
                    file=name,
                    rule="MYCROFT_RESULTADO_INVALIDO",
                    detail=f"**resultado:** '{resultado}' deve ser APROVADO ou CRITICA.",
                ))
        else:
            violations.append(Violation(
                file=name,
                rule="MYCROFT_CAMPO_RESULTADO_AUSENTE",
                detail="Campo '**resultado:**' não encontrado.",
            ))

    if name == "MC_consolidado.md":
        for m in _RE_OVERRULE.finditer(text):
            agente, valor = m.group(1), m.group(2).strip()
            if valor not in ("Sim", "Não"):
                violations.append(Violation(
                    file=name,
                    rule="MYCROFT_OVERRULE_VALOR_INVALIDO",
                    detail=f"Overrule sobre {agente}: '{valor}' deve ser Sim ou Não.",
                ))


# ── Helper ────────────────────────────────────────────────────────────────

def _check_pii(file_name: str, text: str, violations: list[Violation]) -> None:
    if _RE_PII_CPF.search(text):
        violations.append(Violation(
            file=file_name,
            rule="PII_CPF_LITERAL",
            detail="CPF em formato literal detectado. Mascarar com ***.***.***-**",
        ))
    if _RE_PII_CNPJ.search(text):
        violations.append(Violation(
            file=file_name,
            rule="PII_CNPJ_LITERAL",
            detail="CNPJ em formato literal detectado. Mascarar com **.***.***/****-**",
        ))
