# DF-109 Cape-Coral-Relocation-Phase-Monitor [CRUX-MK]

- **Timestamp:** 2026-05-10T10:01:59Z
- **Env-Tag:** `dev`
- **Source-Mode:** `mock`
- **Pareto-Phase:** 1
- **Pending-Phronesis-Count:** 4
- **Diff-Only-Mode:** True (Patch P4)

## D1 K_0-Wegzug-Timing-Guard (NUR Status, KEINE Empfehlung)

- Timing-Status: `review`
- Last-Advisor-Decision: n/a
- Advisor: lexvance
- Decision-Card-Path: `docs/decision-cards/DC-CAPE-CORAL-PENDING.md`
- Health (Binary, Patch P3): data_present=True, coverage=100%
- Source: `mock`

## D2 E-2 Visa Lifecycle

- Current-Phase: `treaty-check` (Index 1/6)
- Treaty-Nationality-Verified: True
- Investment-Substantial: False
- Capital-At-Risk: False
- Marginality-Risk-Assessed: False
- USCIS-Data-Stale (Patch P5): False
- Health (Binary): data_present=True
- Source: `mock`

## D3 § 6 AStG Wegzugssteuer (BMF-Form-Version-Lock: Patch P2)

- Current-Phase: `pre-departure-prep`
- BMF-Form-Version: `2025_v1` (Pflicht-Lock)
- Has-§17-Beteiligung: True
- Stundung-Status: `not-applied`
- Next-Annual-Notification-Due: 2027-07-31
- 7-Jahre-Window-Active: True
- 12-Jahre-Window-Active: False
- Health (Binary): data_present=True
- Source: `mock`

## Action-Items (Patch P6: owner + due_date + escalation)

- `AI-DF109-1` [pending] Lexvance Wegzug-Timing-Decision Review (owner: lexvance, due: 2026-06-30, esc: lexvance -> steuerberater -> us-tax-attorney -> martin)
- `AI-DF109-2` [pending] E-2 Treaty-Investor Petition Vorbereitung (owner: us-immigration-attorney, due: 2026-09-30, esc: us-immigration-attorney -> lexvance -> martin)
- `AI-DF109-3` [pending] § 6 AStG Stundungsantrag Pruefung (owner: steuerberater, due: 2026-07-31, esc: steuerberater -> lexvance -> martin)

## Alerts

- (keine)

## Notes

- DF-109 Pareto-Phase-1: D1+D2+D3 (Wegzug-Guard + E-2 + AStG)
- K_0-Sperr aktiv: NUR Tracking, KEINE Wegzug-Timing-Decisions.
- BMF-Form-Version-Lock: 2025_v1 (Patch P2).

[CRUX-MK]