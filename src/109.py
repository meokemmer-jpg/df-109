"""
DF-109: Cape-Coral-Relocation-Phase-Monitor [CRUX-MK]

Phase monitor for Cape-Coral relocation (DE -> FL USA).
K_0-HARD: monitor only, never a decision-maker.
Wegzug timing remains Martin-Phronesis (L13).
"""
from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Mapping

BMF_FORM_VERSION: str = "2025_v1"
_VALID_BMF_VERSIONS: frozenset[str] = frozenset({"2025_v1"})


class SourceType(str, Enum):
    """K12 provenance: approved source types per dimension."""

    MOCK = "mock"
    REAL_GOVERNMENT = "real-government"
    REAL_TAX_ADVISOR = "real-tax-advisor"


class Dimension(str, Enum):
    """Pareto dimensions for the K_0 guard, E-2 visa, and AStG section 6."""

    K0_GUARD = "k0_guard"
    E2_VISA = "e2_visa"
    ASTG_6 = "astg_6"


_NEGATIVE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"(?i)\bdecision\s+made\b"),
    re.compile(r"(?i)\bwegzug\s+am\s+\d"),
    re.compile(r"(?i)\bauto(?:matically)?\s+trigger\b"),
    re.compile(r"(?i)\bexecute\s+(?:wegzug|transfer|move)\b"),
    re.compile(r"(?i)\bk[_\s]?0\s+verletzt\b"),
)


@dataclass(frozen=True)
class DimensionHealth:
    dimension: Dimension
    score: float
    source: SourceType
    notes: str = ""
    issues: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class PhaseHealth:
    phase_name: str
    bmf_form_version: str
    dimensions: list[DimensionHealth] = field(default_factory=list)

    @property
    def overall_score(self) -> float:
        if not self.dimensions:
            return 0.0
        return sum(d.score for d in self.dimensions) / len(self.dimensions)

    @property
    def is_k0_decision_blocked(self) -> bool:
        return True

    def dimension_score(self, dim: Dimension) -> float:
        for item in self.dimensions:
            if item.dimension == dim:
                return item.score
        return 0.0


@dataclass(frozen=True)
class MonitorVerdict:
    phase_name: str
    status: str
    overall_score: float
    adjusted_score: float
    issue_count: int
    discriminators: list[str]
    k0_decision_blocked: bool
    bmf_form_version: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def verify_astg_version(version: str) -> bool:
    """AStG version lock. True only for approved BMF form versions."""

    return version in _VALID_BMF_VERSIONS


def validate_source_field(source: str) -> bool:
    """K12 provenance check."""

    return source in {item.value for item in SourceType}


def check_negative_patterns(text: str) -> list[str]:
    """Return forbidden decision-trigger pattern strings found in text."""

    return [pattern.pattern for pattern in _NEGATIVE_PATTERNS if pattern.search(text)]


def _coerce_source(source: SourceType | str) -> SourceType:
    src_val = source.value if isinstance(source, SourceType) else str(source)
    if not validate_source_field(src_val):
        raise ValueError(
            f"K12 Provenance violation: invalid source '{src_val}'. "
            f"Allowed: {[item.value for item in SourceType]}"
        )
    return SourceType(src_val)


def _coerce_score(raw_score: Any) -> float:
    try:
        score = float(raw_score)
    except (TypeError, ValueError):
        score = 0.0
    return max(0.0, min(1.0, score))


def aggregate_phase_health(
    state_data: Mapping[str, Any],
    source: SourceType | str = SourceType.MOCK,
    bmf_version: str = BMF_FORM_VERSION,
) -> PhaseHealth:
    """
    Aggregate phase health from supplied state data.

    The function is read-only. It validates the BMF version before touching
    state payload details and never emits a relocation decision.
    """

    if not verify_astg_version(bmf_version):
        raise ValueError(
            f"AStG-Version-Lock (K13_PAV) violation: "
            f"received '{bmf_version}', accepted {sorted(_VALID_BMF_VERSIONS)}"
        )

    effective_source = _coerce_source(source)
    phase_name = str(state_data.get("phase_name", "unknown"))
    dimensions: list[DimensionHealth] = []

    for dim in Dimension:
        dim_data = state_data.get(dim.value, {})
        if not isinstance(dim_data, Mapping):
            dim_data = {}

        score = _coerce_score(dim_data.get("score", 0.0))
        notes = str(dim_data.get("notes", ""))
        flagged = check_negative_patterns(notes)
        issues = [f"NegativePattern:{pattern}" for pattern in flagged]

        dimensions.append(
            DimensionHealth(
                dimension=dim,
                score=score,
                source=effective_source,
                notes=notes,
                issues=issues,
            )
        )

    return PhaseHealth(
        phase_name=phase_name,
        bmf_form_version=bmf_version,
        dimensions=dimensions,
    )


def _dimension_payload(dimension: DimensionHealth) -> dict[str, Any]:
    return {
        "dimension": dimension.dimension.value,
        "score": dimension.score,
        "source": dimension.source.value,
        "notes": dimension.notes,
        "issues": list(dimension.issues),
    }


def classify_phase_health(health: PhaseHealth) -> MonitorVerdict:
    """
    Convert measured phase health into a discriminating monitor verdict.

    Clean inputs can be monitor-clear. Inputs containing decision-trigger text
    are blocked and receive a lower adjusted score derived from the findings.
    """

    discriminators: list[str] = []
    for dimension in health.dimensions:
        for issue in dimension.issues:
            discriminators.append(f"{dimension.dimension.value}:{issue}")

    issue_count = len(discriminators)
    adjusted_score = max(0.0, health.overall_score - (issue_count / max(1, len(Dimension))))

    if issue_count:
        status = "blocked-adversarial-input"
    elif health.overall_score >= 0.75:
        status = "monitor-clear"
    elif health.overall_score > 0.0:
        status = "monitor-watch"
    else:
        status = "monitor-empty"

    return MonitorVerdict(
        phase_name=health.phase_name,
        status=status,
        overall_score=round(health.overall_score, 6),
        adjusted_score=round(adjusted_score, 6),
        issue_count=issue_count,
        discriminators=discriminators,
        k0_decision_blocked=health.is_k0_decision_blocked,
        bmf_form_version=health.bmf_form_version,
    )


def load_phase_state(path: str | Path) -> dict[str, Any]:
    """Load real JSON phase input from disk."""

    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("phase state JSON must contain an object")
    return payload


def monitor_phase_file(
    path: str | Path,
    source: SourceType | str = SourceType.REAL_TAX_ADVISOR,
    bmf_version: str = BMF_FORM_VERSION,
) -> MonitorVerdict:
    """File-backed public function used by stress tests and callers."""

    state_data = load_phase_state(path)
    health = aggregate_phase_health(
        state_data=state_data,
        source=source,
        bmf_version=bmf_version,
    )
    return classify_phase_health(health)


def render_report(health: PhaseHealth) -> str:
    """Read-only text report with the K_0 decision-blocked notice present."""

    lines = [
        "=== DF-109 Cape-Coral-Phase-Monitor Report ===",
        f"Phase          : {health.phase_name}",
        f"BMF-Form       : {health.bmf_form_version} [LOCKED]",
        f"Overall Score  : {health.overall_score:.2f}",
        (
            f"K0-BLOCKED     : {health.is_k0_decision_blocked}"
            " (Wegzug-Timing bleibt Martin-Phronesis L13)"
        ),
        "",
        "Dimensions:",
    ]
    for dimension in health.dimensions:
        issue_tag = f"  !! {dimension.issues}" if dimension.issues else ""
        lines.append(
            f"  {dimension.dimension.value:<12}: score={dimension.score:.2f}"
            f"  source={dimension.source.value}{issue_tag}"
        )
    return "\n".join(lines)
