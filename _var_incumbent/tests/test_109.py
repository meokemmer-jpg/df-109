import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
# [CRUX-MK]
# `from 109 import ...` — numerischer Modulname erfordert importlib
import importlib
import sys
from pathlib import Path

import pytest

# Sicherstellen dass das Verzeichnis mit 109.py im sys.path liegt
_here = Path(__file__).resolve().parent
if str(_here) not in sys.path:
    sys.path.insert(0, str(_here))

# from 109 import (Aequivalent via importlib)
_m = importlib.import_module("109")

BMF_FORM_VERSION        = _m.BMF_FORM_VERSION
SourceType              = _m.SourceType
Dimension               = _m.Dimension
PhaseHealth             = _m.PhaseHealth
DimensionHealth         = _m.DimensionHealth
verify_astg_version     = _m.verify_astg_version
validate_source_field   = _m.validate_source_field
check_negative_patterns = _m.check_negative_patterns
aggregate_phase_health  = _m.aggregate_phase_health
render_report           = _m.render_report


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _state(
    phase_name="phase-1",
    k0_score=0.8,
    e2_score=0.6,
    astg6_score=0.9,
    k0_notes="capital protected",
    e2_notes="I-526 pending",
    astg6_notes="paragraph-6 checklist done",
) -> dict:
    return {
        "phase_name": phase_name,
        "k0_guard": {"score": k0_score,   "notes": k0_notes},
        "e2_visa":  {"score": e2_score,   "notes": e2_notes},
        "astg_6":   {"score": astg6_score,"notes": astg6_notes},
    }


# ---------------------------------------------------------------------------
# Patch P2: AStG-Version-Lock
# ---------------------------------------------------------------------------

class TestAStGVersionLock:
    def test_canonical_version_accepted(self):
        assert verify_astg_version("2025_v1") is True

    def test_wrong_version_rejected(self):
        assert verify_astg_version("2024_v1") is False
        assert verify_astg_version("2025_v2") is False
        assert verify_astg_version("") is False
        assert verify_astg_version("latest") is False

    def test_module_constant_is_itself_valid(self):
        """BMF_FORM_VERSION exported by the module must pass its own lock."""
        assert verify_astg_version(BMF_FORM_VERSION) is True

    def test_aggregate_raises_on_stale_version(self):
        with pytest.raises(ValueError, match="AStG-Version-Lock"):
            aggregate_phase_health(_state(), bmf_version="2024_v1")

    def test_aggregate_raises_on_empty_version(self):
        with pytest.raises(ValueError, match="AStG-Version-Lock"):
            aggregate_phase_health(_state(), bmf_version="")

    def test_error_message_contains_k13_pav(self):
        with pytest.raises(ValueError, match="K13_PAV"):
            aggregate_phase_health(_state(), bmf_version="2024_v1")


# ---------------------------------------------------------------------------
# K12 Provenance
# ---------------------------------------------------------------------------

class TestK12Provenance:
    def test_all_valid_source_values_accepted(self):
        for src in ("mock", "real-government", "real-tax-advisor"):
            assert validate_source_field(src) is True

    def test_invalid_sources_rejected(self):
        for bad in ("unknown", "", "llm", "claude", "auto"):
            assert validate_source_field(bad) is False

    def test_aggregate_raises_on_invalid_source_string(self):
        with pytest.raises((ValueError, Exception)):
            aggregate_phase_health(_state(), source="bad-source")  # type: ignore


# ---------------------------------------------------------------------------
# Patch P1: Negative-RegEx-Validation
# ---------------------------------------------------------------------------

class TestNegativePatterns:
    def test_clean_notes_return_empty_list(self):
        assert check_negative_patterns("I-526 pending, no issues") == []
        assert check_negative_patterns("§6 AStG checklist reviewed by advisor") == []
        assert check_negative_patterns("") == []
        assert check_negative_patterns("capital maintained above K_0 threshold") == []

    def test_decision_made_flagged(self):
        assert len(check_negative_patterns("decision made by DF-109")) > 0

    def test_wegzug_date_flagged(self):
        assert len(check_negative_patterns("Wegzug am 2026-09-01")) > 0

    def test_auto_trigger_flagged(self):
        assert len(check_negative_patterns("automatically trigger relocation")) > 0

    def test_execute_wegzug_flagged(self):
        assert len(check_negative_patterns("execute Wegzug now")) > 0
        assert len(check_negative_patterns("execute transfer immediately")) > 0

    def test_flagged_notes_surface_in_dimension_issues(self):
        state = _state(k0_notes="decision made automatically")
        health = aggregate_phase_health(state)
        k0 = next(d for d in health.dimensions if d.dimension == Dimension.K0_GUARD)
        assert k0.issues, "flagged note must produce non-empty issues list"
        assert any("NegativePattern" in i for i in k0.issues)

    def test_clean_notes_produce_no_issues(self):
        health = aggregate_phase_health(_state())
        for d in health.dimensions:
            assert d.issues == []


# ---------------------------------------------------------------------------
# aggregate_phase_health — core behaviour
# ---------------------------------------------------------------------------

class TestAggregatePhaseHealth:
    def test_returns_phase_health_instance(self):
        assert isinstance(aggregate_phase_health(_state()), PhaseHealth)

    def test_phase_name_preserved(self):
        h = aggregate_phase_health(_state(phase_name="pre-departure"))
        assert h.phase_name == "pre-departure"

    def test_unknown_phase_name_when_missing(self):
        h = aggregate_phase_health({})
        assert h.phase_name == "unknown"

    def test_bmf_version_preserved_in_result(self):
        h = aggregate_phase_health(_state())
        assert h.bmf_form_version == BMF_FORM_VERSION

    def test_all_three_dimensions_present(self):
        h = aggregate_phase_health(_state())
        found = {d.dimension for d in h.dimensions}
        assert found == {Dimension.K0_GUARD, Dimension.E2_VISA, Dimension.ASTG_6}

    def test_overall_score_is_arithmetic_mean(self):
        h = aggregate_phase_health(_state(k0_score=0.8, e2_score=0.6, astg6_score=1.0))
        expected = (0.8 + 0.6 + 1.0) / 3
        assert abs(h.overall_score - expected) < 1e-9

    def test_score_clamped_above_one(self):
        h = aggregate_phase_health(_state(k0_score=2.5))
        k0 = next(d for d in h.dimensions if d.dimension == Dimension.K0_GUARD)
        assert k0.score == 1.0

    def test_score_clamped_below_zero(self):
        h = aggregate_phase_health(_state(e2_score=-0.5))
        e2 = next(d for d in h.dimensions if d.dimension == Dimension.E2_VISA)
        assert e2.score == 0.0

    def test_all_scores_within_unit_interval(self):
        h = aggregate_phase_health(_state(k0_score=99, e2_score=-99, astg6_score=0.5))
        for d in h.dimensions:
            assert 0.0 <= d.score <= 1.0

    def test_default_source_is_mock(self):
        h = aggregate_phase_health(_state())
        for d in h.dimensions:
            assert d.source == SourceType.MOCK

    def test_real_tax_advisor_source_propagates(self):
        h = aggregate_phase_health(_state(), source=SourceType.REAL_TAX_ADVISOR)
        for d in h.dimensions:
            assert d.source == SourceType.REAL_TAX_ADVISOR

    def test_missing_dimension_data_defaults_score_to_zero(self):
        h = aggregate_phase_health({"phase_name": "minimal"})
        for d in h.dimensions:
            assert d.score == 0.0

    def test_dimension_score_helper(self):
        h = aggregate_phase_health(_state(k0_score=0.75))
        assert abs(h.dimension_score(Dimension.K0_GUARD) - 0.75) < 1e-9

    def test_dimension_score_returns_zero_for_missing(self):
        h = PhaseHealth(phase_name="x", bmf_form_version=BMF_FORM_VERSION)
        assert h.dimension_score(Dimension.E2_VISA) == 0.0


# ---------------------------------------------------------------------------
# K_0-HARD invariant
# ---------------------------------------------------------------------------

class TestK0HardInvariant:
    def test_decision_blocked_standard(self):
        h = aggregate_phase_health(_state())
        assert h.is_k0_decision_blocked is True

    def test_decision_blocked_even_at_perfect_score(self):
        h = aggregate_phase_health(_state(k0_score=1.0, e2_score=1.0, astg6_score=1.0))
        assert h.is_k0_decision_blocked is True

    def test_decision_blocked_at_zero_score(self):
        h = aggregate_phase_health(_state(k0_score=0.0, e2_score=0.0, astg6_score=0.0))
        assert h.is_k0_decision_blocked is True


# ---------------------------------------------------------------------------
# render_report
# ---------------------------------------------------------------------------

class TestRenderReport:
    def _health(self):
        return aggregate_phase_health(_state())

    def test_returns_string(self):
        assert isinstance(render_report(self._health()), str)

    def test_contains_k0_blocked_and_phronesis_notice(self):
        r = render_report(self._health())
        assert "K0-BLOCKED" in r
        assert "Phronesis" in r or "Martin" in r

    def test_contains_locked_bmf_version(self):
        r = render_report(self._health())
        assert BMF_FORM_VERSION in r
        assert "LOCKED" in r

    def test_contains_all_dimension_names(self):
        r = render_report(self._health())
        for dim in Dimension:
            assert dim.value in r

    def test_contains_overall_score(self):
        h = self._health()
        r = render_report(h)
        assert f"{h.overall_score:.2f}" in r

    def test_issues_appear_in_report(self):
        h = aggregate_phase_health(_state(astg6_notes="decision made by system"))
        r = render_report(h)
        assert "!!" in r

