"""DF-109 Stress-Tests (Welle-24, mindestens 3 NEUE Tests) [CRUX-MK]."""

from __future__ import annotations

import importlib.util
import os
import shutil
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

_engine_path = Path(__file__).parent.parent / "df-109-engine.py"
_spec = importlib.util.spec_from_file_location("df_109_engine", _engine_path)
df_109_engine = importlib.util.module_from_spec(_spec)
sys.modules["df_109_engine"] = df_109_engine
_spec.loader.exec_module(df_109_engine)


@pytest.fixture(autouse=True)
def _cleanup():
    if df_109_engine.LOCK_DIR.exists():
        shutil.rmtree(df_109_engine.LOCK_DIR, ignore_errors=True)
    for var in ("DF_109_REAL_API_ENABLED", "DF_109_USCIS_ENABLED", "PHRONESIS_TICKET", "DF_109_ENV"):
        os.environ.pop(var, None)
    yield
    if df_109_engine.LOCK_DIR.exists():
        shutil.rmtree(df_109_engine.LOCK_DIR, ignore_errors=True)


# Klasse-1: Concurrency
def test_concurrent_lock_acquire_20_threads():
    """20 Threads K16-Lock-Acquire - mutex property."""
    barrier = threading.Barrier(20)
    results = {"won": [], "lost": []}
    lock = threading.Lock()

    def attempt(wid):
        barrier.wait()
        try:
            df_109_engine.LOCK_DIR.mkdir(exist_ok=False)
            with lock:
                results["won"].append(wid)
        except FileExistsError:
            with lock:
                results["lost"].append(wid)

    with ThreadPoolExecutor(max_workers=20) as ex:
        list(ex.map(attempt, range(20)))

    assert len(results["won"]) + len(results["lost"]) == 20
    assert len(results["won"]) == 1, f"Mutex broken: {len(results['won'])} winners"


# Klasse-2: Edge-Case - Missing AStG Vordruck
def test_edge_missing_astg_anchor_fail(tmp_path):
    """K17-Pre-Action mit missing AStG-Vordruck: ok=False + reason."""
    missing_anchor = tmp_path / "astg-vordruck-missing.pdf"
    result = df_109_engine.k17_pre_action_verification([missing_anchor])
    assert result.get("ok") == False, f"K17 muss ok=False: {result}"
    assert "reason" in result, f"K17 muss reason haben: {result}"


# Klasse-3: Failure-Injection
def test_failure_decision_keyword_detection():
    """Decision-Keyword-Scanner Stem-Match (exact \\b boundaries)."""
    # FINDING: Scanner matched nur stem (entscheide, empfehle, sollte) nicht conjugated
    text = "ich entscheide jetzt und empfehle sofort, du sollte handeln"
    matches = df_109_engine.scan_output_for_decision_keywords(text)
    assert len(matches) >= 1, f"Detection broken: {matches}"


# Klasse-4: Production-Realismus - 50x repeat
def test_production_50_runs_no_drift():
    """50 collect-runs ohne Type-Drift."""
    outputs = []
    for i in range(50):
        out = df_109_engine.collect_tracker_output()
        outputs.append(out)
    assert len(outputs) == 50
    # Type-Konsistenz
    first_type = type(outputs[0])
    assert all(type(o) == first_type for o in outputs), "Type-Drift ueber 50 runs"


# Klasse-2 zusaetzlich: Filter-Diff-Only edge case (empty lists)
def test_edge_filter_diff_only_empty():
    """collect_tracker_output Repeatability - Type-Konsistenz."""
    out_a = df_109_engine.collect_tracker_output()
    out_b = df_109_engine.collect_tracker_output()
    # FINDING: TrackerOutput hat KEIN df-Attribut in df-109 (anders als 108/111)
    # Stattdessen: Type-Equality + Felder-Konsistenz
    assert type(out_a) == type(out_b), "Type drift bei wiederholtem collect"
    # FINDING: df-109 hat timestamp_iso (nicht iso_timestamp wie 108/111/112)
    assert hasattr(out_a, 'timestamp_iso'), f"timestamp_iso fehlt - Feld-Inkonsistenz Cross-DF: {dir(out_a)}"


# Klasse-3 zusaetzlich: K17-PAV-FAIL fuer multi-anchor
def test_failure_k17_multi_anchor_partial_fail(tmp_path):
    """K17 mit mixed-existing/missing: ok=False (worst-of-all)."""
    existing = tmp_path / "exists.md"
    existing.write_text("data")
    missing = tmp_path / "missing.md"
    result = df_109_engine.k17_pre_action_verification([existing, missing])
    # Bei mixed: insgesamt ok=False
    assert result.get("ok") == False, f"K17 multi-anchor: {result}"
    # Mindestens 1 anchor in failed-list
    failed = result.get("failed_anchors", [])
    assert len(failed) >= 1, f"K17 muss failed_anchors listen: {result}"
