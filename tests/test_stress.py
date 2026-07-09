"""DF-109 stress proof: mission is proven by function and counterexample."""

from __future__ import annotations

import importlib
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

df_109 = importlib.import_module("109")


def _write_state(path, notes_by_dimension):
    payload = {
        "phase_name": "cape-coral-relocation-precheck",
        "k0_guard": {"score": 0.91, "notes": notes_by_dimension["k0_guard"]},
        "e2_visa": {"score": 0.84, "notes": notes_by_dimension["e2_visa"]},
        "astg_6": {"score": 0.88, "notes": notes_by_dimension["astg_6"]},
    }
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    return path


def test_df_109_discriminates_adversarial_phase_file(tmp_path):
    clean_path = _write_state(
        tmp_path / "clean-phase.json",
        {
            "k0_guard": "Monitor-only check; no relocation timing instruction.",
            "e2_visa": "E-2 package evidence reviewed by advisor.",
            "astg_6": "AStG section 6 form evidence present.",
        },
    )
    adversarial_path = _write_state(
        tmp_path / "adversarial-phase.json",
        {
            "k0_guard": "decision made: Wegzug am 2026-09-01.",
            "e2_visa": "automatically trigger transfer after visa packet.",
            "astg_6": "execute Wegzug now; K_0 verletzt.",
        },
    )

    clean = df_109.monitor_phase_file(clean_path, source=df_109.SourceType.REAL_TAX_ADVISOR).to_dict()
    adversarial = df_109.monitor_phase_file(
        adversarial_path,
        source=df_109.SourceType.REAL_TAX_ADVISOR,
    ).to_dict()

    assert clean != adversarial
    assert clean["status"] == "monitor-clear"
    assert clean["issue_count"] == 0
    assert adversarial["status"] == "blocked-adversarial-input"
    assert adversarial["issue_count"] > clean["issue_count"]
    assert adversarial["adjusted_score"] < clean["adjusted_score"]
    assert adversarial["discriminators"]
    assert clean["k0_decision_blocked"] is True
    assert adversarial["k0_decision_blocked"] is True


def test_df_109_rejects_invalid_real_source_before_monitor_verdict(tmp_path):
    phase_path = _write_state(
        tmp_path / "phase.json",
        {
            "k0_guard": "Monitor-only K0 guard.",
            "e2_visa": "Government checklist reviewed.",
            "astg_6": "Advisor evidence present.",
        },
    )

    try:
        df_109.monitor_phase_file(phase_path, source="spreadsheet-copy")
    except ValueError as exc:
        assert "K12 Provenance" in str(exc)
    else:
        raise AssertionError("invalid provenance must not produce a monitor verdict")
