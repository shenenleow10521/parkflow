"""Single source for every cost and net-cash constant in the V3 deck (imported by v3_zone200.py and presentation/v3_assemble.py).
Each line says whether it is SOURCED, DERIVED (arithmetic on sourced inputs) or ASSUMED (last resort, reason given)."""

# ---- tax and fees ----------------------------------------------------------------------------------------------
SST = 0.06            # SOURCED: parking services stayed at 6% when the general service-tax rate rose to 8% on 1 Mar 2024 (Deloitte Malaysia alert; Customs parking-services guide)
                      # TREATMENT: the booking fee is a parking service and is tax-INCLUSIVE (conservative). If it were not taxable, net cash would be ~6% higher.
OPERATOR_SHARE = 0.20  # ASSUMED, unagreed (no published industry commission)
CARD_FEE = 0.018 * 1.08  # SOURCED: Billplz Basic MYR card 1.8% + 8% SST on the gateway fee = 1.944% of the amount collected
NET = (1 - OPERATOR_SHARE) / (1 + SST) - CARD_FEE  # net cash per RM of fee collected: operator share is taken on the ex-SST fee; card fee on the amount collected

# ---- people cost -> day rate -----------------------------------------------------------------------------------
SALARY = 115_701      # SOURCED: Payscale, average Senior Software Developer in Malaysia, annual base, 2026 (Indeed: RM8,876/month for senior Java, Jul 2026, same ballpark)
ONCOST = 0.13         # DERIVED: employer EPF 12% (wage > RM5,000) + SOCSO 1.75% capped at a RM6,000 wage (~1.1% of this salary) + EIS ~0.2% capped
PROD_DAYS = 210       # ASSUMED: ~260 weekdays - ~14 public holidays - ~16 leave/training - ~20 idle/admin
DAY_RATE = SALARY * (1 + ONCOST) / PROD_DAYS   # = ~RM623 per productive person-day, cost basis (no agency margin)

# ---- software build: work breakdown (person-days). ASSUMED effort, itemised so it can be challenged line by line.
# (work package, production days, pilot days). The pilot runs assisted service, so barrier/controller integration and the full console come later.
WBS = [
    ('Member identity and entitlement API (SDP membership)', 10, 10),
    ('Booking service and capacity guard (prototype core exists)', 12, 12),
    ('Deposit, refund, no-show and reconciliation via payment gateway', 10, 10),
    ('LPR count ingest, plate ledger, barrier/controller integration', 15, 7),
    ('Operator console, incident log, audit trail', 10, 5),
    ('Security, deployment, monitoring', 6, 4),
    ('Test, UAT, fault drills, commissioning', 12, 8),
]
PM_UPLIFT = 0.15      # ASSUMED: project management and QA on top of build days
BUILD_DAYS = sum(w[1] for w in WBS) * (1 + PM_UPLIFT)
PILOT_DAYS = sum(w[2] for w in WBS) * (1 + PM_UPLIFT)
INTEGRATION = round(BUILD_DAYS * DAY_RATE, -2)
PILOT_BUILD = round(PILOT_DAYS * DAY_RATE, -2)

# ---- site hardware --------------------------------------------------------------------------------------------
CAM_HW = 750          # SOURCED: Hikvision DS-2CD2046G2-IU/SL 4MP, Lapasar B2B listing (a RM199 TP-Link consumer listing is the floor)
CAM_CABLE = 40 * 10   # DERIVED: RM100 per extra 10 m (Alienvoip installer price list) x ASSUMED 40 m extra run per camera in a multi-level car park
CAM_LABOUR = 350      # ASSUMED: about half a technician-day per camera. Cross-check: Alienvoip's RM2,599 complete 4-camera + NVR bundle is RM650 per camera all-in, so RM1,500 is 2.3x that
CAM = CAM_HW + CAM_CABLE + CAM_LABOUR
WORKS = 7_500         # ASSUMED allowance (PoE switch, UPS, trunking, signage). Camera cabling is now in the camera line, so no overlap. No survey.
DISPLAY = 2_033       # SOURCED: Viskou DS-TVL224-4-5Y 2-row display, tax extra
N_CAM = 4
CAPEX = INTEGRATION + WORKS + N_CAM * CAM + DISPLAY
CAPEX_LO = INTEGRATION + WORKS                       # no CCTV, no display
CAPEX_HI = INTEGRATION + WORKS + 10 * CAM + DISPLAY  # 10 cameras + display
LPR_CAM = 3_226       # SOURCED: Viskou DS-TCG406-E, only if the zone has no LPR

# ---- running cost (per year) ---------------------------------------------------------------------------------
MAINT_RATE = 0.15     # SOURCED as a heuristic: 15-20% of build cost a year (vendor guidance, no authoritative study); low end used
USD_MYR = 4.3         # ASSUMED exchange rate
HOSTING = round(2 * 0.0475 * 730 * 12 * USD_MYR, -2)  # DERIVED: 2 x EC2 t3.medium, AWS Malaysia region, USD0.0475/h on demand, 24x7 (aws-pricing.com)
RUN = round(MAINT_RATE * INTEGRATION + HOSTING, -2)

if __name__ == '__main__':
    print(f'day rate RM{DAY_RATE:.0f}; build {BUILD_DAYS:.1f} d -> RM{INTEGRATION:,.0f}; pilot {PILOT_DAYS:.1f} d -> RM{PILOT_BUILD:,.0f}')
    print(f'camera RM{CAM:,} x{N_CAM}; capex RM{CAPEX:,.0f} (range {CAPEX_LO:,.0f}-{CAPEX_HI:,.0f}); running RM{RUN:,.0f} (hosting {HOSTING:,.0f}); NET {NET:.4f}')
