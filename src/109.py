"""
DF-109: Cape-Coral-Relocation-Phase-Monitor [CRUX-MK]

Phase-Monitor fuer Cape-Coral-Relocation (DE -> FL USA).
K_0-HARD: NICHT Decision-Maker.
Wegzug-Timing bleibt Martin-Phronesis (L13).

Welle: 23-B | Domain: K_0 | Status: SKELETON-CONDITIONAL
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import List

# ---------------------------------------------------------------------------
# Patch P2: AStG-Version-Lock (PFLICHT — vor allem anderen)
# ---------------------------------------------------------------------------
BMF_FORM_VERSION: str = "2025_v1"
_VALID_BMF_VERSIONS: frozenset = frozenset({"2025_v1"})


class SourceType(str, Enum):
    """K12 Provenance: approved source types per dimension."""
    MOCK = "mock"
    REAL_GOVERNMENT = "real-government"
    REAL_TAX_ADVISOR = "real-tax-advisor"


class Dimension(str, Enum):
    """3 Pareto-Dimensionen (K_0-Guard + E-2-Visa + § 6 AStG)."""
    K0_GUARD = "k0_guard"
    E2_VISA = "e2_visa"
    ASTG_6 = "astg_6"


# ---------------------------------------------------------------------------
# Patch P1: Negative-RegEx-Validation
# ---------------------------------------------------------------------------
_NEGATIVE_PATTERNS: tuple = (
    re.compile(r"(?i)\bdecision\s+made\b"),
    re.compile(r"(?i)\bwegzug\s+am\s+\d"),
    re.compile(r"(?i)\bauto(?:matically)?\s+trigger\b"),
    re.compile(r"(?i)\bexecute\s+(?:wegzug|transfer|move)\b"),
    re.compile(r"(?i)\bk[_\s]?0\s+verletzt\b"),
)


@dataclass
class DimensionHealth:
    dimension: Dimension
    score: float          # clamped [0.0, 1.0]
    source: SourceType
    notes: str = ""
    issues: List[str] = field(default_factory=list)


@dataclass
class PhaseHealth:
    phase_name: str
    bmf_form_version: str
    dimensions: List[DimensionHealth] = field(default_factory=list)

    @property
    def overall_score(self) -> float:
        """Mean health score across all dimensions."""
        if not self.dimensions:
            return 0.0
        return sum(d.score for d in self.dimensions) / len(self.dimensions)

    @property
    def is_k0_decision_blocked(self) -> bool:
        """
        K_0-HARD invariant: DF-109 is a monitor, never a decision-maker.
        Wegzug-Timing bleibt Martin-Phronesis (L13). Always True.
        """
        return True

    def dimension_score(self, dim: Dimension) -> float:
        for d in self.dimensions:
            if d.dimension == dim:
                return d.score
        return 0.0


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def verify_astg_version(version: str) -> bool:
    """Patch P2: AStG-Version-Lock. True iff version in approved set."""
    return version in _VALID_BMF_VERSIONS


def validate_source_field(source: str) -> bool:
    """K12 Provenance: source must be an approved SourceType value."""
    return source in {s.value for s in SourceType}


def check_negative_patterns(text: str) -> List[str]:
    """
    Patch P1: Scan text for forbidden decision-trigger phrases.
    Returns list of matched pattern strings (empty = clean).
    """
    return [p.pattern for p in _NEGATIVE_PATTERNS if p.search(text)]


def aggregate_phase_health(
    state_data: dict,
    source: SourceType = SourceType.MOCK,
    bmf_version: str = BMF_FORM_VERSION,
) -> PhaseHealth:
    """
    Aggregate phase health from a state_data dict (read-only, K_0-HARD).

    Expected format::

        {
            "phase_name": "phase-1",
            "k0_guard":   {"score": 0.8, "notes": "capital protected"},
            "e2_visa":    {"score": 0.6, "notes": "I-526 pending"},
            "astg_6":     {"score": 0.9, "notes": "paragraph-6 done"},
        }

    Raises ValueError on AStG-Version-Lock violation (Patch P2/K13_PAV)
    or K12 provenance failure.
    """
    # Patch P2 — AStG-Version-Lock: FIRST, before any other processing
    if not verify_astg_version(bmf_version):
        raise ValueError(
            f"AStG-Version-Lock (K13_PAV) violation: "
            f"received '{bmf_version}', accepted {sorted(_VALID_BMF_VERSIONS)}"
        )

    # K12 — Provenance check
    src_val = source.value if isinstance(source, SourceType) else str(source)
    if not validate_source_field(src_val):
        raise ValueError(
            f"K12 Provenance violation: invalid source '{src_val}'. "
            f"Allowed: {[s.value for s in SourceType]}"
        )

    phase_name: str = state_data.get("phase_name", "unknown")
    dimensions: List[DimensionHealth] = []

    for dim in Dimension:
        dim_data: dict = state_data.get(dim.value, {})
        raw_score = float(dim_data.get("score", 0.0))
        score = max(0.0, min(1.0, raw_score))       # clamp [0, 1]
        notes: str = str(dim_data.get("notes", ""))

        # Patch P1 — Negative-RegEx-Validation on notes
        flagged = check_negative_patterns(notes)
        issues = [f"NegativePattern: {pat}" for pat in flagged]

        effective_source = source if isinstance(source, SourceType) else SourceType(src_val)
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


def render_report(health: PhaseHealth) -> str:
    """Read-only text report. K_0-DECISION-BLOCKED notice always present."""
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
    for d in health.dimensions:
        issue_tag = f"  !! {d.issues}" if d.issues else ""
        lines.append(
            f"  {d.dimension.value:<12}: score={d.score:.2f}"
            f"  source={d.source.value}{issue_tag}"
        )
    return "\n".join(lines)
# [CRUX-MK]
