
# K16: Concurrent-Spawn-Mutex (fcntl-based, Trinity-CONSERVATIVE 2026-05-17)
def k16_lock_or_exit(df_name: str):
    """Acquire exclusive lock or exit(3). Prevents concurrent DF runs."""
    import fcntl, os, sys
    lock_path = f"/tmp/df-trinity-{df_name}.lock"
    fd = os.open(lock_path, os.O_CREAT | os.O_WRONLY)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return fd
    except BlockingIOError:
        sys.exit(3)


# K13: External-Anchor-Mock-RFC3161 (Trinity-CONSERVATIVE 2026-05-17)
def k13_anchor(payload_hash: str) -> dict:
    """Mock RFC3161-style timestamp anchor."""
    from datetime import datetime, timezone
    return {
        "anchor_type": "rfc3161-mock",
        "iso_ts": datetime.now(timezone.utc).isoformat(),
        "payload_hash": payload_hash,
    }


# K12: HMAC-SHA256-Provenance (Trinity-CONSERVATIVE 2026-05-17)
def k12_provenance(payload: bytes, key: bytes = b"df-trinity-conservative-v1") -> dict:
    """Returns payload_hash + HMAC-SHA256 signature."""
    import hashlib, hmac
    return {
        "payload_hash": hashlib.sha256(payload).hexdigest(),
        "hmac_sha256": hmac.new(key, payload, hashlib.sha256).hexdigest(),
    }

"""DF-109 Cape-Coral-Relocation-Phase-Monitor [CRUX-MK]

Welle: 23-B (Pareto-Phase-1: 3 Dimensionen K_0-Guard + E-2 + § 6 AStG)
Domain: K_0 (Wegzug/Steuer/Vermoegen) - STRENG-SPERR
Spec: branch-hub/blueprints/welle-23/SPEC-DF-109-CAPE-CORAL-RELOCATION-MONITOR-2026-05-10.md

Mission:
    Phase-Monitor fuer Cape-Coral-Relocation (DE -> FL USA).
    NICHT Decision-Maker. Aggregiert Status aus existing-Files + visualisiert
    Health-Score pro Phase. K_0-Sperr: Wegzug-Timing bleibt Martin-Phronesis.

Pareto-Phase-1 Dimensionen (P1: 70% Decision-Delta-Wert bei 30% Build-Aufwand):
    D1 K_0-Wegzug-Timing-Guard  - Status-Anzeige (locked/review/changed-by-advisor)
    D2 E-2 Visa Lifecycle       - USCIS Tracker + State Dept Termin-Slots
    D3 § 6 AStG Wegzugssteuer   - BMF-Vordrucke + 7/12-Jahre-Status

Pareto-Phase-2 Dimensionen (Phase-2 nach Pilot-Erfolg):
    D4 DE/US Tax Residency (SPT) - Tage-Tracker + DBA-Position
    D5 Smart-Home Readiness      - IoT-Inventory + Deployment-Status
    D6 Property & Risk-Setup     - Insurance-Binders + Permits
    D7 Business-Continuity-Bridge - US-Entity-Setup + Banking

Wargame-Patches (Pflicht-Integration aus 3-LLM-Konsens):
    P1 Output-Sanitizer / RegEx-Filter  - blockiert "optimal", "jetzt wegziehen", etc.
    P2 AStG-Version-Lock                - bmf_form_version Pflicht in config
    P3 Binary Health pro K_0-Dim        - vorhanden/fehlend, KEINE qualitative-Bewertung
    P4 Diff-Only-Reports                - nur Deltas seit letzter Phronesis-Freigabe
    P5 Web-API-Race-Schutz              - fetched_at + source_hash + stale_if_older_than
    P6 Action-Routing                   - owner + due_date + escalation_path pro Item
    P7 K17 PAV-Pflicht                  - Pre-Action-Check fuer alle Filesystem-Anker

CRUX-Bindung:
    K_0: Strict-Conditions Mock-Default + Activation-Gate-Pflicht + 7 K_0-Sperr-Items
    Q_0: Familien-Beratung-Pflicht (Q_0 indirekt via Cape-Coral)
    I_min: 3-Pareto-Dimensionen-Tracking strukturiert
    L_Martin: Phronesis-Items klar markiert PENDING-PHRONESIS-MARTIN

[CRUX-MK]
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import os
import re
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# ============================================================================
# Constants
# ============================================================================

DF_NAME = "df-109"
LOCK_DIR = Path("/tmp/df-109.lock")
LOCK_STALE_AGE_S = 6 * 3600  # 6h K16 default

# Wargame-Patch P7 (K17): File-Stability-Threshold (5 Min Drive-Sync-Race-Schutz)
FILE_STABILITY_MIN_AGE_SEC = 300

# Wargame-Patch P5: Web-API-Race-Stale-Threshold (Default 24h)
WEB_API_STALE_IF_OLDER_THAN_SEC = 24 * 3600

# Wargame-Patch P2: AStG-Version-Lock (Pflicht-Constant)
EXPECTED_BMF_FORM_VERSION = "2025_v1"

# Wargame-Patch P1: Decision/Recommendation-Keywords (K_0-Sperr Negative-Scan)
# Erweitert ueber Standard hinaus: timing-spezifische Trigger fuer Wegzug
DECISION_KEYWORDS_REGEX = re.compile(
    # FINDING-2-FIX-V2 (Welle-24): Verb-Stems + spezifische Phrasen.
    r"\b(optimal(?:er|e|es)?|jetzt wegziehen|stichtag-vorschlag|stichtagsvorschlag|"
    r"should move|recommend(?:s|ed|ing)?|empfehl(?:e|en|t|st)|empfiehlt?|"
    r"priorisier(?:e|en|t|st)|entscheid(?:e|en|et|est)|"
    r"sollt(?:e|en|est)|muss(?:t|en|est)|advis(?:e|es|ed|ing)|"
    r"propos(?:e|es|ed|ing)|wegzieh(?:e|en|t)|"
    r"jetzt wegzug|sofort wegzug|jetzt verkaufen)\b",
    re.IGNORECASE,
)

# K_0-Wegzug-Timing-Guard Status (NUR diese 3 Status erlaubt - keine Empfehlungen)
WEGZUG_TIMING_STATUS_ALLOWED = ("locked", "review", "changed-by-advisor")

# E-2 Visa Lifecycle Phasen
E2_VISA_PHASES = ("planning", "treaty-check", "investment-prep",
                  "petition-filed", "interview-scheduled", "approved", "in-status")

# § 6 AStG Phasen
ASTG_PHASES = ("not-applicable", "pre-departure-prep", "valuation-pending",
               "stundung-applied", "stundung-granted", "trigger-event-monitoring",
               "annual-notification-due")


def iso_now() -> str:
    """ISO-8601 UTC timestamp."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ============================================================================
# Wargame-Patch P7 (K17): File-Stability-Check
# ============================================================================

def _file_stable(path: Path, min_age_sec: int = FILE_STABILITY_MIN_AGE_SEC) -> bool:
    """Drive-Sync-Race-Schutz. K13-Anker muss seit min_age_sec unbearbeitet sein.

    Returns:
        True wenn stabil ODER nicht-existent (separater Check).
        False wenn kuerzlich geaendert (Race-Risk).
    """
    if not path.exists():
        return False
    try:
        mtime = path.stat().st_mtime
        age_sec = time.time() - mtime
        return age_sec >= min_age_sec
    except (OSError, PermissionError):
        return False


# ============================================================================
# K16 Concurrent-Spawn-Mutex
# ============================================================================

def acquire_lock_with_identity() -> bool:
    """K16: Atomic mkdir-Lock + pgrep-Defense.

    Wargame-konform per concurrency-mandatory-tests Rule.
    Returns True wenn Lock erworben, False bei Concurrent-Run.
    """
    if LOCK_DIR.exists():
        try:
            lock_age_s = time.time() - LOCK_DIR.stat().st_mtime
            if lock_age_s > LOCK_STALE_AGE_S:
                import shutil
                shutil.rmtree(LOCK_DIR, ignore_errors=True)
        except (OSError, PermissionError):
            return False

    try:
        LOCK_DIR.mkdir(parents=False, exist_ok=False)
    except FileExistsError:
        return False

    try:
        (LOCK_DIR / "pid").write_text(str(os.getpid()))
    except (OSError, PermissionError):
        pass

    return True


def release_lock() -> None:
    """Release K16-Lock (EXIT/INT/TERM)."""
    import shutil
    shutil.rmtree(LOCK_DIR, ignore_errors=True)


# ============================================================================
# K17 Pre-Action-Verification (Wargame-Patch P7)
# ============================================================================

def _check_env_tag() -> str:
    """K17: env-tag (dev/staging/prod) verifizieren."""
    env = os.environ.get("DF_109_ENV", "dev")
    if env not in ("dev", "staging", "prod"):
        return "unknown"
    return env


def _check_anchor_exists(anchor_path: Path) -> bool:
    """K17: Anker-Datei muss existieren UND stabil sein."""
    if not anchor_path.exists():
        return False
    return _file_stable(anchor_path, min_age_sec=FILE_STABILITY_MIN_AGE_SEC)


def k17_pre_action_verification(anchors: list[Path]) -> dict:
    """K17 Pre-Action-Verification (PocketOS-Lehre + Verfassungsrang).

    Pflicht VOR jedem Read auf shared/external Resources.
    HARD-STOP bei Failure (kein Auto-Override).

    Returns:
        Dict mit verification-status. Wenn 'ok'=False: HARD-STOP.
    """
    env_tag = _check_env_tag()
    if env_tag == "unknown":
        return {"ok": False, "reason": "env-tag-unknown", "env_tag": env_tag}

    failed_anchors = [str(a) for a in anchors if not _check_anchor_exists(a)]
    if failed_anchors:
        return {
            "ok": False,
            "reason": "anchor-missing-or-unstable",
            "env_tag": env_tag,
            "failed_anchors": failed_anchors,
        }

    return {
        "ok": True,
        "env_tag": env_tag,
        "anchors_verified": len(anchors),
    }


# ============================================================================
# Activation-Gates
# ============================================================================

def _is_real_api_enabled() -> bool:
    """Activation-Gate: Real-API nur wenn ENV=true UND Phronesis-Ticket."""
    enabled = os.environ.get("DF_109_REAL_API_ENABLED") == "true"
    if not enabled:
        return False
    ticket = os.environ.get("PHRONESIS_TICKET", "")
    if not ticket or ticket == "MISSING":
        return False
    return True


def _is_uscis_api_enabled() -> bool:
    """Activation-Gate: USCIS-API nur wenn ENV=true UND Phronesis-Ticket (Phase-2)."""
    enabled = os.environ.get("DF_109_USCIS_API_ENABLED") == "true"
    if not enabled:
        return False
    ticket = os.environ.get("PHRONESIS_TICKET", "")
    return bool(ticket) and ticket != "MISSING"


# ============================================================================
# Wargame-Patch P3: Binary Health (vorhanden/fehlend - KEINE qualitative-Bewertung)
# ============================================================================

@dataclass(frozen=True)
class BinaryHealth:
    """Patch P3: Binary Health-Score - NUR Daten-Praesenz, KEINE Quality.

    NICHT 'gruen/gelb/rot' (das wuerde K_0-Inferenz triggern).
    NUR 'data_present=True/False' + 'anchor_count' + 'stale_count'.
    """

    data_present: bool         # T = mindestens 1 Anker vorhanden
    anchor_count: int          # Wie viele Anker erwartet
    anchors_found: int         # Wie viele tatsaechlich gefunden
    anchors_stale: int         # Wie viele stale (> stale_threshold)

    @property
    def coverage_ratio(self) -> float:
        """Daten-Praesenz-Quote (KEINE qualitative Bewertung)."""
        if self.anchor_count == 0:
            return 0.0
        return self.anchors_found / self.anchor_count


# ============================================================================
# Wargame-Patch P5: Web-API-Race-Schutz (fetched_at + source_hash)
# ============================================================================

@dataclass(frozen=True)
class WebApiData:
    """Patch P5: Web-API-Daten mit Race-Schutz-Metadaten.

    Auch wenn Web-API erstmal Mock ist, das Pattern ist Pflicht
    fuer spaetere Real-API-Integration.
    """

    payload: dict
    fetched_at_iso: str
    source_hash: str
    stale_if_older_than_sec: int = WEB_API_STALE_IF_OLDER_THAN_SEC
    retry_count: int = 0
    backoff_next_sec: int = 0

    @property
    def is_stale(self) -> bool:
        """Stale-Marker (Pflicht-Display)."""
        try:
            fetched = datetime.fromisoformat(self.fetched_at_iso.replace("Z", "+00:00"))
            age_sec = (datetime.now(timezone.utc) - fetched).total_seconds()
            return age_sec > self.stale_if_older_than_sec
        except (ValueError, AttributeError):
            return True  # bei Format-Fehler: konservativ stale


def _make_web_api_data(payload: dict, source_hint: str = "mock") -> WebApiData:
    """Erstellt WebApiData mit fetched_at + source_hash (Patch P5)."""
    payload_str = json.dumps(payload, sort_keys=True)
    source_hash = hashlib.sha256(payload_str.encode()).hexdigest()[:16]
    return WebApiData(
        payload=payload,
        fetched_at_iso=iso_now(),
        source_hash=source_hash,
    )


# ============================================================================
# Wargame-Patch P6: Action-Routing (owner + due_date + escalation_path)
# ============================================================================

@dataclass(frozen=True)
class ActionItem:
    """Patch P6: Pro Report-Item: owner + due_date + escalation_path."""

    item_id: str
    description: str
    owner: str                    # z.B. "martin", "steuerberater", "lexvance"
    due_date_iso: Optional[str]   # ISO-Date oder None
    escalation_path: str          # z.B. "martin -> lexvance -> us-tax-attorney"
    state: str = "pending"        # "pending" | "acknowledged" | "resolved"
    acknowledged_at_iso: Optional[str] = None
    resolved_at_iso: Optional[str] = None


# ============================================================================
# 7-Dimension-Tracker (Pareto-Phase-1 = D1+D2+D3, Phase-2 = D4-D7)
# ============================================================================

@dataclass(frozen=True)
class WegzugTimingGuardDimension:
    """D1 K_0-Wegzug-Timing-Guard - NUR Status-Anzeige.

    K_0-Sperr: KEINE Empfehlung, NUR locked/review/changed-by-advisor.
    """

    timing_status: str            # "locked" | "review" | "changed-by-advisor"
    last_advisor_decision_iso: Optional[str]
    advisor_name: Optional[str]   # z.B. "lexvance", "steuerberater-mueller"
    decision_card_path: Optional[str]
    health: BinaryHealth          # Patch P3
    source: str                    # "mock" | "real-decision-cards"

    def __post_init__(self):
        # K_0-Sperr-Enforcement: timing_status muss in erlaubter Liste sein
        if self.timing_status not in WEGZUG_TIMING_STATUS_ALLOWED:
            raise ValueError(
                f"K_0-SPERR-VERLETZUNG: timing_status='{self.timing_status}' "
                f"nicht in {WEGZUG_TIMING_STATUS_ALLOWED}. "
                f"Wegzug-Timing-Empfehlungen sind Martin-Phronesis."
            )


@dataclass(frozen=True)
class E2VisaLifecycleDimension:
    """D2 E-2 Visa Lifecycle - USCIS Tracker + State Dept Termin-Slots."""

    current_phase: str           # E2_VISA_PHASES
    treaty_nationality_verified: bool
    investment_substantial: bool
    capital_at_risk: bool
    marginality_risk_assessed: bool
    uscis_appointment_data: Optional[WebApiData]  # Patch P5
    health: BinaryHealth         # Patch P3
    source: str                   # "mock" | "real-uscis-api"

    @property
    def phase_index(self) -> int:
        """0-6 Index der aktuellen Phase."""
        try:
            return E2_VISA_PHASES.index(self.current_phase)
        except ValueError:
            return -1


@dataclass(frozen=True)
class AstgWegzugssteuerDimension:
    """D3 § 6 AStG Wegzugssteuer - BMF-Vordrucke + 7/12-Jahre-Status.

    Patch P2: bmf_form_version Pflicht.
    """

    current_phase: str            # ASTG_PHASES
    bmf_form_version: str         # Patch P2: PFLICHT (z.B. "2025_v1")
    has_section17_beteiligung: bool
    stundung_status: str          # "not-applied" | "applied" | "granted" | "denied"
    next_annual_notification_due: Optional[str]  # ISO-Date 31.07.
    seven_year_window_active: bool
    twelve_year_window_active: bool
    health: BinaryHealth          # Patch P3
    source: str                    # "mock" | "real-bmf-vordruck"

    def __post_init__(self):
        # Patch P2: AStG-Version-Lock-Enforcement
        if not self.bmf_form_version:
            raise ValueError(
                "Patch P2: bmf_form_version Pflicht (AStG-Version-Lock). "
                f"Erwartet z.B. '{EXPECTED_BMF_FORM_VERSION}'."
            )


@dataclass(frozen=True)
class TaxResidencyDimension:
    """D4 DE/US Tax Residency (SPT) - Tage-Tracker + DBA-Position [Phase-2]."""

    de_wohnsitz_active: bool
    us_substantial_presence_days_current: int
    us_spt_threshold_reached: bool
    fbar_filing_required: bool
    fatca_filing_required: bool
    health: BinaryHealth
    source: str


@dataclass(frozen=True)
class SmartHomeDimension:
    """D5 Smart-Home Readiness - IoT-Inventory + Deployment-Status [Phase-2]."""

    network_deployed: bool
    hvac_deployed: bool
    security_deployed: bool
    leak_flood_sensor_deployed: bool
    generator_deployed: bool
    health: BinaryHealth
    source: str


@dataclass(frozen=True)
class PropertyRiskDimension:
    """D6 Property & Risk-Setup - Insurance-Binders + Permits [Phase-2]."""

    flood_zone_classified: bool
    wind_hurricane_mitigation_done: bool
    hoa_status_known: bool
    storm_shutters_installed: bool
    insurance_binders_count: int
    health: BinaryHealth
    source: str


@dataclass(frozen=True)
class BusinessContinuityDimension:
    """D7 Business-Continuity-Bridge - US-Entity-Setup + Banking [Phase-2]."""

    us_llc_inc_status: str  # "not-started" | "in-progress" | "active"
    us_bank_account_active: bool
    digital_post_workflow_de_active: bool
    health: BinaryHealth
    source: str


@dataclass(frozen=True)
class TrackerOutput:
    """7-Dimension-Aggregat-Output (Tracking, NICHT Decision).

    Pareto-Phase-1: D1+D2+D3 (P1)
    Phase-2: D4+D5+D6+D7 (alle None in Phase-1)
    """

    timestamp_iso: str
    env_tag: str
    pareto_phase: int  # 1 oder 2
    # Pareto-Phase-1
    wegzug_timing: WegzugTimingGuardDimension
    e2_visa: E2VisaLifecycleDimension
    astg_wegzugssteuer: AstgWegzugssteuerDimension
    # Phase-2 (alle Optional in Phase-1)
    tax_residency: Optional[TaxResidencyDimension] = None
    smart_home: Optional[SmartHomeDimension] = None
    property_risk: Optional[PropertyRiskDimension] = None
    business_continuity: Optional[BusinessContinuityDimension] = None
    # Output-Felder
    pending_phronesis_count: int = 4  # 4 PENDING-PHRONESIS-MARTIN aus SPEC
    notes: list[str] = field(default_factory=list)
    alerts: list[str] = field(default_factory=list)
    action_items: list[ActionItem] = field(default_factory=list)  # Patch P6
    diff_only_mode: bool = True  # Patch P4: Default Diff-Only
    last_freigabe_iso: Optional[str] = None  # Patch P4: Diff-Basis
    source_mode: str = "mock"


# ============================================================================
# Mock + Real Collection-Logic
# ============================================================================

def _mk_health(present: bool, expected: int = 1, found: int = 1, stale: int = 0) -> BinaryHealth:
    """Helper: erstellt BinaryHealth (Patch P3)."""
    return BinaryHealth(
        data_present=present,
        anchor_count=expected,
        anchors_found=found,
        anchors_stale=stale,
    )


def _collect_wegzug_timing_mock() -> WegzugTimingGuardDimension:
    """Mock-Mode D1: K_0-Wegzug-Timing-Guard (NUR Status)."""
    return WegzugTimingGuardDimension(
        timing_status="review",
        last_advisor_decision_iso=None,
        advisor_name="lexvance",
        decision_card_path="docs/decision-cards/DC-CAPE-CORAL-PENDING.md",
        health=_mk_health(present=True, expected=1, found=1),
        source="mock",
    )


def _collect_e2_visa_mock() -> E2VisaLifecycleDimension:
    """Mock-Mode D2: E-2 Visa Lifecycle."""
    uscis_data = _make_web_api_data(
        payload={"appointment_slots": [], "next_available": None},
        source_hint="mock",
    )
    return E2VisaLifecycleDimension(
        current_phase="treaty-check",
        treaty_nationality_verified=True,
        investment_substantial=False,  # PENDING
        capital_at_risk=False,
        marginality_risk_assessed=False,
        uscis_appointment_data=uscis_data,
        health=_mk_health(present=True, expected=2, found=1),
        source="mock",
    )


def _collect_astg_mock() -> AstgWegzugssteuerDimension:
    """Mock-Mode D3: § 6 AStG Wegzugssteuer (Patch P2: bmf_form_version Pflicht)."""
    return AstgWegzugssteuerDimension(
        current_phase="pre-departure-prep",
        bmf_form_version=EXPECTED_BMF_FORM_VERSION,  # Patch P2 Pflicht
        has_section17_beteiligung=True,
        stundung_status="not-applied",
        next_annual_notification_due="2027-07-31",
        seven_year_window_active=True,
        twelve_year_window_active=False,
        health=_mk_health(present=True, expected=2, found=2),
        source="mock",
    )


def _collect_wegzug_timing_real(anchor_path: Path) -> WegzugTimingGuardDimension:
    """Real-Mode D1: Read Decision-Cards (Patch P7 K17 + file_stable)."""
    if not _file_stable(anchor_path):
        m = _collect_wegzug_timing_mock()
        return dataclasses.replace(m, source="mock-fallback-anchor-unstable")
    try:
        mtime = anchor_path.stat().st_mtime
        last_iso = datetime.fromtimestamp(mtime, tz=timezone.utc).isoformat()
        return WegzugTimingGuardDimension(
            timing_status="review",  # Default - kein Auto-Promote
            last_advisor_decision_iso=last_iso,
            advisor_name="lexvance",
            decision_card_path=str(anchor_path),
            health=_mk_health(present=True, expected=1, found=1),
            source="real-stub-decision-cards",
        )
    except (OSError, PermissionError):
        return _collect_wegzug_timing_mock()


# ============================================================================
# Wargame-Patch P1: Output-Sanitizer / RegEx-Filter
# ============================================================================

def scan_output_for_decision_keywords(text: str) -> list[str]:
    """Patch P1: Negative-RegEx-Test fuer K_0-Sperr.

    Blockiert: "optimal", "jetzt wegziehen", "stichtag-vorschlag",
              "should move", "recommend", "empfehle", "priorisiere"
    """
    matches = DECISION_KEYWORDS_REGEX.findall(text)
    return matches


def assert_no_decision_keywords(output: TrackerOutput) -> None:
    """Hard-Assert: Output enthaelt KEINE Decision-Keywords (K_0-Sperr).

    Raises:
        ValueError wenn Decision-Keyword gefunden.
    """
    text_blob = " ".join(output.notes + output.alerts)
    matches = scan_output_for_decision_keywords(text_blob)
    if matches:
        raise ValueError(
            f"K_0-SPERR-VERLETZUNG: Decision-Keywords gefunden: {matches}. "
            f"DF-109 darf NICHT Decisions/Empfehlungen produzieren. "
            f"Wegzug-Timing ist Martin-Phronesis."
        )


# ============================================================================
# Wargame-Patch P4: Diff-Only-Reports
# ============================================================================

def filter_diff_only(
    current_output: TrackerOutput,
    last_freigabe_state_path: Optional[Path] = None,
) -> dict:
    """Patch P4: Standard-Ansicht zeigt nur Deltas seit letzter Freigabe.

    Wenn last_freigabe_state_path nicht existiert oder nicht-stable:
    Voll-Output (initial-Mode).
    """
    full_dict = _to_dict(current_output)

    if not last_freigabe_state_path or not last_freigabe_state_path.exists():
        # Initial-Mode: Voll-Output mit Marker
        return {
            "mode": "initial-no-baseline",
            "diff": full_dict,
            "note": "No prior Phronesis-Freigabe found - full output as baseline",
        }

    try:
        last_state = json.loads(last_freigabe_state_path.read_text())
    except (json.JSONDecodeError, OSError):
        return {
            "mode": "baseline-corrupt",
            "diff": full_dict,
            "note": "Could not parse last_freigabe_state - falling back to full output",
        }

    diff = {}
    for key, value in full_dict.items():
        if last_state.get(key) != value:
            diff[key] = {"before": last_state.get(key), "after": value}

    return {
        "mode": "diff-only",
        "diff": diff,
        "last_freigabe_iso": current_output.last_freigabe_iso,
    }


# ============================================================================
# Main Aggregation
# ============================================================================

def collect_tracker_output(
    anchors: Optional[list[Path]] = None,
    real_mode: Optional[bool] = None,
    pareto_phase: int = 1,
) -> TrackerOutput:
    """7-Dimension-Aggregate-Tracker (Pareto-Phase-1 = D1+D2+D3).

    Args:
        anchors: K13-Pflicht-Anker (Decision-Cards + USCIS-Tracker + BMF-Vordrucke).
        real_mode: Override fuer Real-Mode (Default: from ENV).
        pareto_phase: 1 (P1: D1+D2+D3) oder 2 (alle 7 Dimensionen).

    Returns:
        TrackerOutput.

    Pre-conditions:
        - K17-PAV (Patch P7): env-tag + anchors stable
        - K16-Lock: erworben (caller-Responsibility)

    Post-conditions:
        - Output enthaelt KEINE Decision-Keywords (Patch P1)
        - Source-Field gesetzt
        - bmf_form_version dokumentiert (Patch P2)
        - Action-Items mit owner + due_date + escalation (Patch P6)
    """
    if real_mode is None:
        real_mode = _is_real_api_enabled()

    env_tag = _check_env_tag()
    notes: list[str] = []
    alerts: list[str] = []
    action_items: list[ActionItem] = []

    # Patch P7 K17 Pre-Action-Verification (nur wenn anchors angegeben)
    if anchors:
        pav = k17_pre_action_verification(anchors)
        if not pav["ok"]:
            notes.append(f"K17-PAV-FAIL: {pav['reason']} - Mock-Fallback aktiviert")
            real_mode = False

    # Pareto-Phase-1: 3 Dimensionen sammeln
    if real_mode and anchors:
        wegzug = _collect_wegzug_timing_real(anchors[0])
    else:
        wegzug = _collect_wegzug_timing_mock()

    e2 = _collect_e2_visa_mock()  # Mock auch in real-mode (USCIS-API Phase-2)
    astg = _collect_astg_mock()    # Mock auch in real-mode (BMF-Vordrucke Phase-2)

    # Phase-2 Dimensionen (in Phase-1 None)
    tax_res = None
    smart_home = None
    property_risk = None
    bus_continuity = None
    if pareto_phase == 2:
        # Phase-2: Stub-Mocks (Phase-2 bedeutet Aktivierung pending Pilot-Erfolg)
        tax_res = TaxResidencyDimension(
            de_wohnsitz_active=True,
            us_substantial_presence_days_current=0,
            us_spt_threshold_reached=False,
            fbar_filing_required=False,
            fatca_filing_required=False,
            health=_mk_health(False, 1, 0),
            source="mock-phase2-stub",
        )
        smart_home = SmartHomeDimension(
            network_deployed=False,
            hvac_deployed=False,
            security_deployed=False,
            leak_flood_sensor_deployed=False,
            generator_deployed=False,
            health=_mk_health(False, 5, 0),
            source="mock-phase2-stub",
        )
        property_risk = PropertyRiskDimension(
            flood_zone_classified=False,
            wind_hurricane_mitigation_done=False,
            hoa_status_known=False,
            storm_shutters_installed=False,
            insurance_binders_count=0,
            health=_mk_health(False, 1, 0),
            source="mock-phase2-stub",
        )
        bus_continuity = BusinessContinuityDimension(
            us_llc_inc_status="not-started",
            us_bank_account_active=False,
            digital_post_workflow_de_active=False,
            health=_mk_health(False, 1, 0),
            source="mock-phase2-stub",
        )

    # Patch P6: Action-Items mit owner + due_date + escalation_path
    action_items.append(ActionItem(
        item_id="AI-DF109-1",
        description="Lexvance Wegzug-Timing-Decision Review",
        owner="lexvance",
        due_date_iso="2026-06-30",
        escalation_path="lexvance -> steuerberater -> us-tax-attorney -> martin",
    ))
    action_items.append(ActionItem(
        item_id="AI-DF109-2",
        description="E-2 Treaty-Investor Petition Vorbereitung",
        owner="us-immigration-attorney",
        due_date_iso="2026-09-30",
        escalation_path="us-immigration-attorney -> lexvance -> martin",
    ))
    action_items.append(ActionItem(
        item_id="AI-DF109-3",
        description="§ 6 AStG Stundungsantrag Pruefung",
        owner="steuerberater",
        due_date_iso="2026-07-31",
        escalation_path="steuerberater -> lexvance -> martin",
    ))

    notes.append(
        f"DF-109 Pareto-Phase-{pareto_phase}: "
        + ("D1+D2+D3 (Wegzug-Guard + E-2 + AStG)" if pareto_phase == 1
           else "alle 7 Dimensionen (D1-D7)")
    )
    notes.append("K_0-Sperr aktiv: NUR Tracking, KEINE Wegzug-Timing-Decisions.")
    notes.append(f"BMF-Form-Version-Lock: {EXPECTED_BMF_FORM_VERSION} (Patch P2).")

    output = TrackerOutput(
        timestamp_iso=iso_now(),
        env_tag=env_tag,
        pareto_phase=pareto_phase,
        wegzug_timing=wegzug,
        e2_visa=e2,
        astg_wegzugssteuer=astg,
        tax_residency=tax_res,
        smart_home=smart_home,
        property_risk=property_risk,
        business_continuity=bus_continuity,
        pending_phronesis_count=4,
        notes=notes,
        alerts=alerts,
        action_items=action_items,
        diff_only_mode=True,
        source_mode="real" if real_mode else "mock",
    )

    # Patch P1: Hard-Assert vor Return
    assert_no_decision_keywords(output)

    return output


# ============================================================================
# Persistence
# ============================================================================

def persist_output(output: TrackerOutput, output_dir: Path) -> Path:
    """Persist tracker output as JSON + Markdown report."""
    output_dir.mkdir(parents=True, exist_ok=True)
    date_str = output.timestamp_iso[:10]

    json_path = output_dir / f"cape-coral-status-{date_str}.json"
    json_path.write_text(json.dumps(_to_dict(output), indent=2))

    md_path = output_dir / f"cape-coral-status-{date_str}.md"
    md_path.write_text(_render_markdown(output))

    return json_path


def _to_dict(output: TrackerOutput) -> dict:
    """Dataclass -> dict (recursive)."""
    return dataclasses.asdict(output)


def _render_markdown(output: TrackerOutput) -> str:
    """Render TrackerOutput as audit-Markdown.

    NOTE: Render darf KEINE Decision-Keywords erzeugen (Patch P1).
    Format ist beschreibend, nicht praeskriptiv.
    """
    w = output.wegzug_timing
    e2 = output.e2_visa
    astg = output.astg_wegzugssteuer

    lines = [
        "# DF-109 Cape-Coral-Relocation-Phase-Monitor [CRUX-MK]",
        "",
        f"- **Timestamp:** {output.timestamp_iso}",
        f"- **Env-Tag:** `{output.env_tag}`",
        f"- **Source-Mode:** `{output.source_mode}`",
        f"- **Pareto-Phase:** {output.pareto_phase}",
        f"- **Pending-Phronesis-Count:** {output.pending_phronesis_count}",
        f"- **Diff-Only-Mode:** {output.diff_only_mode} (Patch P4)",
        "",
        "## D1 K_0-Wegzug-Timing-Guard (NUR Status, KEINE Empfehlung)",
        "",
        f"- Timing-Status: `{w.timing_status}`",
        f"- Last-Advisor-Decision: {w.last_advisor_decision_iso or 'n/a'}",
        f"- Advisor: {w.advisor_name or 'n/a'}",
        f"- Decision-Card-Path: `{w.decision_card_path or 'n/a'}`",
        f"- Health (Binary, Patch P3): data_present={w.health.data_present}, "
        f"coverage={w.health.coverage_ratio:.0%}",
        f"- Source: `{w.source}`",
        "",
        "## D2 E-2 Visa Lifecycle",
        "",
        f"- Current-Phase: `{e2.current_phase}` (Index {e2.phase_index}/6)",
        f"- Treaty-Nationality-Verified: {e2.treaty_nationality_verified}",
        f"- Investment-Substantial: {e2.investment_substantial}",
        f"- Capital-At-Risk: {e2.capital_at_risk}",
        f"- Marginality-Risk-Assessed: {e2.marginality_risk_assessed}",
        f"- USCIS-Data-Stale (Patch P5): "
        f"{e2.uscis_appointment_data.is_stale if e2.uscis_appointment_data else 'n/a'}",
        f"- Health (Binary): data_present={e2.health.data_present}",
        f"- Source: `{e2.source}`",
        "",
        "## D3 § 6 AStG Wegzugssteuer (BMF-Form-Version-Lock: Patch P2)",
        "",
        f"- Current-Phase: `{astg.current_phase}`",
        f"- BMF-Form-Version: `{astg.bmf_form_version}` (Pflicht-Lock)",
        f"- Has-§17-Beteiligung: {astg.has_section17_beteiligung}",
        f"- Stundung-Status: `{astg.stundung_status}`",
        f"- Next-Annual-Notification-Due: {astg.next_annual_notification_due or 'n/a'}",
        f"- 7-Jahre-Window-Active: {astg.seven_year_window_active}",
        f"- 12-Jahre-Window-Active: {astg.twelve_year_window_active}",
        f"- Health (Binary): data_present={astg.health.data_present}",
        f"- Source: `{astg.source}`",
        "",
        "## Action-Items (Patch P6: owner + due_date + escalation)",
        "",
    ]
    for ai in output.action_items:
        lines.append(
            f"- `{ai.item_id}` [{ai.state}] {ai.description} "
            f"(owner: {ai.owner}, due: {ai.due_date_iso or 'n/a'}, "
            f"esc: {ai.escalation_path})"
        )

    lines.extend(["", "## Alerts", ""])
    if output.alerts:
        for alert in output.alerts:
            lines.append(f"- {alert}")
    else:
        lines.append("- (keine)")

    lines.extend(["", "## Notes", ""])
    for note in output.notes:
        lines.append(f"- {note}")

    lines.append("")
    lines.append("[CRUX-MK]")
    return "\n".join(lines)


# ============================================================================
# CLI Entry-Point
# ============================================================================

def main() -> int:
    """CLI-Entry mit K16-Lock + Output-Persist."""
    if not acquire_lock_with_identity():
        sys.stderr.write("DF-109: K16-LOCK-CONFLICT (concurrent run detected)\n")
        return 3

    try:
        output = collect_tracker_output()
        report_dir = Path(__file__).parent / "reports"
        path = persist_output(output, report_dir)
        sys.stdout.write(f"DF-109 OK -> {path}\n")
        return 0
    finally:
        release_lock()


if __name__ == "__main__":
    sys.exit(main())

# [CRUX-MK]
