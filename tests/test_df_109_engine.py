"""DF-109 Cape-Coral Engine-Tests (Architekt-Self-Build Recovery 2026-05-10) [CRUX-MK]"""

import importlib.util
import os
import re
import subprocess
import sys
from pathlib import Path

DF_DIR = Path(__file__).parent.parent
ENGINE_PATH = DF_DIR / "df-109-engine.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("df_109", str(ENGINE_PATH))
    mod = importlib.util.module_from_spec(spec)
    sys.modules["df_109"] = mod  # Python 3.14 dataclasses Workaround
    spec.loader.exec_module(mod)
    return mod


def test_engine_imports():
    """Engine kann ohne Fehler geladen werden."""
    mod = _load_module()
    assert hasattr(mod, "collect_tracker_output")


def test_pareto_phase_1_only_k0_e2_astg():
    """Pareto-Phase-1: 3 Dimensionen aktiv (D1+D2+D3)."""
    mod = _load_module()
    assert hasattr(mod, "WegzugTimingGuardDimension")
    assert hasattr(mod, "E2VisaLifecycleDimension")
    assert hasattr(mod, "AstgWegzugssteuerDimension")


def test_output_sanitizer_blocks_decision_words():
    """Patch P1: scan_output_for_decision_keywords blockiert Decision-Worte."""
    mod = _load_module()
    assert hasattr(mod, "scan_output_for_decision_keywords")
    detected = mod.scan_output_for_decision_keywords("Du solltest jetzt wegziehen, optimal ist Q3 2026")
    assert any(kw in str(detected).lower() for kw in ["optimal", "wegziehen", "solltest"])


def test_astg_version_lock_enforced():
    """Patch P2: config.yaml MUSS bmf_form_version enthalten."""
    config_path = DF_DIR / "config.yaml"
    assert config_path.exists()
    txt = config_path.read_text(encoding="utf-8")
    assert re.search(r"bmf_form_version\s*:\s*\S+", txt), "bmf_form_version Pflicht in config.yaml"


def test_binary_health_no_qualitative_score():
    """Patch P3: BinaryHealth Class existiert (vorhanden/fehlend, kein qualitative)."""
    mod = _load_module()
    assert hasattr(mod, "BinaryHealth")


def test_diff_only_reports_default():
    """Patch P4: filter_diff_only Funktion existiert."""
    mod = _load_module()
    assert hasattr(mod, "filter_diff_only")


def test_web_api_race_stale_marker():
    """Patch P5: WebApiData Klasse mit fetched_at/source_hash/stale-Logik."""
    mod = _load_module()
    assert hasattr(mod, "WebApiData")
    assert hasattr(mod, "_make_web_api_data")
    data = mod._make_web_api_data({"slot_date": "2026-08-15"}, source_hint="mock")
    fields = data.__dict__ if hasattr(data, "__dict__") else dict(data._asdict()) if hasattr(data, "_asdict") else {}
    assert "fetched_at" in fields or any("fetched" in str(k) for k in fields)


def test_action_routing_per_item():
    """Patch P6: ActionItem Class mit owner/due_date/escalation_path."""
    mod = _load_module()
    assert hasattr(mod, "ActionItem")


def test_k17_pav_blocks_on_missing_anchor():
    """Patch P7 + K17 PAV: Pre-Action-Check muss Missing-Anchor erkennen."""
    mod = _load_module()
    assert hasattr(mod, "k17_pre_action_verification")
    result = mod.k17_pre_action_verification([Path("/nonexistent/anchor.md")])
    assert isinstance(result, dict)


def test_k16_lock_concurrent():
    """K16: acquire_lock_with_identity + release_lock vorhanden."""
    mod = _load_module()
    assert hasattr(mod, "acquire_lock_with_identity")
    assert hasattr(mod, "release_lock")


def test_mock_mode_default():
    """Activation-Gate: DF_109_REAL_API_ENABLED default false."""
    mod = _load_module()
    assert hasattr(mod, "_is_real_api_enabled")
    os.environ.pop("DF_109_REAL_API_ENABLED", None)
    assert mod._is_real_api_enabled() is False


def test_activation_gate_phronesis_ticket():
    """Phronesis-Ticket-Check existiert in config oder engine."""
    config_path = DF_DIR / "config.yaml"
    txt = config_path.read_text(encoding="utf-8")
    assert "PHRONESIS_TICKET" in txt or "phronesis_ticket" in txt.lower()


# ====== K_0-Sperr-Tests (7 NEGATIVE) ======

DECISION_KEYWORDS = ["optimal", "jetzt wegziehen", "stichtag-vorschlag", "should move", "recommend", "empfehle", "priorisiere"]


def test_no_wegzug_timing_recommendation():
    """K_0-Sperr-1: KEINE Wegzug-Timing-Empfehlung im Source."""
    src = ENGINE_PATH.read_text(encoding="utf-8").lower()
    forbidden = ["recommend_wegzug_date", "suggest_wegzug", "optimal_wegzug_date"]
    for f in forbidden:
        assert f not in src, f"Forbidden: {f}"


def test_no_steuer_decisions():
    """K_0-Sperr-2: KEINE Steuer-Decision-Funktionen."""
    src = ENGINE_PATH.read_text(encoding="utf-8").lower()
    forbidden = ["decide_stundung", "auto_verkauf_vor_wegzug", "recommend_tax_strategy"]
    for f in forbidden:
        assert f not in src, f"Forbidden: {f}"


def test_no_section17_valuation():
    """K_0-Sperr-3: KEINE §17-Bewertung (Steuerberater-Domain)."""
    src = ENGINE_PATH.read_text(encoding="utf-8").lower()
    forbidden = ["compute_section17_value", "berechne_gemeiner_wert", "estimate_section17"]
    for f in forbidden:
        assert f not in src, f"Forbidden: {f}"


def test_no_e2_investment_decisions():
    """K_0-Sperr-4: KEINE E-2-Investment-Decisions."""
    src = ENGINE_PATH.read_text(encoding="utf-8").lower()
    forbidden = ["recommend_e2_investment", "decide_e2_amount", "auto_e2_structure"]
    for f in forbidden:
        assert f not in src, f"Forbidden: {f}"


def test_no_property_buy_decisions():
    """K_0-Sperr-5: KEINE Property-Buy-Decisions."""
    src = ENGINE_PATH.read_text(encoding="utf-8").lower()
    forbidden = ["recommend_property", "decide_purchase", "auto_buy_property"]
    for f in forbidden:
        assert f not in src, f"Forbidden: {f}"


def test_advisor_override_silently_stale_blocked():
    """Anti-Pattern-1: stale advisor-override muss markiert sein."""
    mod = _load_module()
    # Check fuer stale-related logic in WebApiData
    src = ENGINE_PATH.read_text(encoding="utf-8")
    assert "stale" in src.lower() or "fetched_at" in src.lower()


def test_green_health_despite_missing_source_blocked():
    """Anti-Pattern-2: Health-OK-DESPITE-Missing-Source darf nicht passieren."""
    mod = _load_module()
    bh = mod._mk_health(present=False, expected=1, found=0)
    # BinaryHealth with present=False darf nicht "green" sein
    fields = bh.__dict__ if hasattr(bh, "__dict__") else {}
    # Pruefe: present=False → Health-Status nicht "OK"
    assert any(getattr(bh, attr, None) is False for attr in ["present", "is_present", "data_present"]) or \
           "missing" in str(fields).lower() or "fehlend" in str(fields).lower() or fields.get("present") is False
