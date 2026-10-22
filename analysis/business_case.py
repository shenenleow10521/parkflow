"""ParkFlow business case: market size, cost sheet, per-mall P&L and 5-year break-even.

Every input is labelled: [S] sourced, [D] deck/simulation, [A] our assumption to confirm in the
mentoring sprint (vendor quotes, SDP digital team, operator contract).
Usage: python business_case.py   (writes business_case_results.txt)
"""

RM_PER_USD = 4.7                                   # [A] exchange rate used for USD list prices

# ---------------- Market (number of malls) ----------------
MALLS_MY = 490          # [S] PPK Malaysia: shopping malls in Malaysia, end-2024 (The Star)
MALLS_KV = 173          # [S] NAPIC via The Rakyat Post: enclosed malls in Selangor (95) + Kuala Lumpur (78), mid-2025
SDP_MALLS = 4           # [D] KL East, KLGCC, Elmina Lakeside, Melawati

# ---------------- Pricing and demand per mall ----------------
FEE = 4.0                       # [D] RM4 guarantee fee per paid booking
PAID_BUSY = (20, 30, 40)        # [D] paid bookings per busy (weekend) day: low / base / high
PAID_OTHER = (5, 7.5, 10)       # [D] paid bookings per other day
BUSY_DAYS, OTHER_DAYS = 104, 261
OPERATOR_SHARE = 0.20           # [A] share of booking fees paid to the car-park operator
CARD_FEE = 0.02                 # [A] payment processing
SPONSOR_FEE = 2.0               # [A] RM per booking a tenant sponsors ("film or dinner + guaranteed bay")
SPONSORED_BUSY = (5, 15, 25)    # [A] tenant-sponsored bookings per busy day, to test in the pilot
SPONSORED_OTHER = (2, 4, 6)
LICENCE = 2500 * 12             # [A] partner-mall licence, RM per zone per year (RM2,500 a month)

# ---------------- Cost sheet ----------------
HW = {  # one-off per mall, RM: (low, base, high)
    "Zone plate cameras, both directions (installed)": (8000, 12000, 20000),        # [A] no public price; to quote
    "LED zone sign": (12000, 16300, 16300),                                           # [S] USD 3,475 list (Tapconet), local quote may be lower
    "2 AI boxes (NVIDIA Jetson Orin Nano Super)": (2340, 2340, 2340),                 # [S] USD 249 each
    "4-6 extra cameras at blind spots": (3000, 5000, 9000),                            # [A] RM750-1,500 each
    "Installation and cabling": (5000, 7500, 10000),                                  # [A]
}
PLATFORM_BUILD = (100000, 150000, 200000)  # [A] one-off: booking tab, rule engine, dashboard (3 devs x 4-6 months)
RUN_PER_MALL = {  # yearly per live mall, RM: (low, base, high)
    "Cloud hosting": (3600, 4800, 7200),                                              # [A] RM300-600 a month
    "WhatsApp confirmations": (900, 1400, 2000),                                      # [S] Meta utility template ~USD 0.014; ~2 per booking
    "Hardware upkeep (10% of hardware a year)": (3400, 4300, 5700),                   # [A]
}
TEAM = (100000, 120000, 150000)  # [A] central engineer (with on-costs) per year; a second one beyond 12 live malls
SALES = 30000                    # [A] partner onboarding and support per year, from the first partner
ROLLOUT = [  # (year, new SDP malls, new partner malls)  [A]
    (1, 1, 0),   # KL East pilot, then live
    (2, 3, 0),   # KLGCC, Elmina Lakeside, Melawati
    (3, 0, 6),
    (4, 0, 6),
    (5, 0, 6),
    (6, 0, 6),
    (7, 0, 6),
]
TEAM_Y1 = 0.5                    # [A] our team runs the 8-week pilot; the central engineer joins at go-live


def pick(t, case):
    return t[{"low": 0, "base": 1, "high": 2}[case]]


def mall_revenue(case):
    """Net revenue for an SDP-run mall per year (booking fees after operator share and card fees, plus sponsorship)."""
    paid = pick(PAID_BUSY, case) * BUSY_DAYS + pick(PAID_OTHER, case) * OTHER_DAYS
    fees = paid * FEE * (1 - OPERATOR_SHARE - CARD_FEE)
    spons = (pick(SPONSORED_BUSY, case) * BUSY_DAYS + pick(SPONSORED_OTHER, case) * OTHER_DAYS) * SPONSOR_FEE
    return fees, spons, paid


def hw_cost(case):
    # Low revenue goes with high cost and vice versa, so "low" and "high" are true worst and best cases.
    c = {"low": "high", "base": "base", "high": "low"}[case]
    return sum(pick(v, c) for v in HW.values())


def run_cost(case):
    c = {"low": "high", "base": "base", "high": "low"}[case]
    return sum(pick(v, c) for v in RUN_PER_MALL.values())


def five_year(case):
    c = {"low": "high", "base": "base", "high": "low"}[case]
    fees, spons, _ = mall_revenue(case)
    sdp = partners = 0
    cum = 0.0
    rows = []
    for yr, new_sdp, new_p in ROLLOUT:
        sdp += new_sdp
        partners += new_p
        rev = sdp * (fees + spons) + partners * LICENCE
        cost = new_sdp * hw_cost(case) + (sdp + partners) * run_cost(case)
        cost += pick(TEAM, c) * (1 if sdp + partners <= 12 else 2) * (TEAM_Y1 if yr == 1 else 1)
        cost += SALES if partners else 0
        if yr == 1:
            cost += pick(PLATFORM_BUILD, c)
        net = rev - cost
        cum += net
        rows.append((yr, sdp, partners, rev, cost, net, cum))
    return rows


def main():
    L = []
    L.append("MARKET SIZE (annual licence value, RM2,500 a month per mall)")
    L.append(f"  TAM  all malls in Malaysia           {MALLS_MY:>4} malls  RM{MALLS_MY * LICENCE / 1e6:5.1f}m a year")
    L.append(f"  SAM  Klang Valley (Selangor + KL)     {MALLS_KV:>4} malls  RM{MALLS_KV * LICENCE / 1e6:5.1f}m a year")
    som = SDP_MALLS + sum(p for _, _, p in ROLLOUT[:3])
    L.append(f"  SOM  4 SDP malls + 6 partners, year 3 {som:>3} malls  RM{som * LICENCE / 1e6:5.2f}m a year ({som / MALLS_KV:.0%} of SAM)")

    L.append("\nCOST SHEET, per mall (one-off hardware), RM: low / base / high")
    for k, v in HW.items():
        L.append(f"  {k:<52}{v[0]:>8,} {v[1]:>8,} {v[2]:>8,}")
    L.append(f"  {'Hardware total':<52}{hw_cost('high'):>8,.0f} {hw_cost('base'):>8,.0f} {hw_cost('low'):>8,.0f}")
    L.append(f"  {'Platform build (once, all malls)':<52}{PLATFORM_BUILD[0]:>8,} {PLATFORM_BUILD[1]:>8,} {PLATFORM_BUILD[2]:>8,}")
    L.append("Running, per live mall per year, RM")
    for k, v in RUN_PER_MALL.items():
        L.append(f"  {k:<52}{v[0]:>8,} {v[1]:>8,} {v[2]:>8,}")
    L.append(f"  {'Running total':<52}{run_cost('high'):>8,.0f} {run_cost('base'):>8,.0f} {run_cost('low'):>8,.0f}")
    L.append(f"  {'Central engineer (portfolio)':<52}{TEAM[0]:>8,} {TEAM[1]:>8,} {TEAM[2]:>8,}")

    L.append("\nREVENUE PER SDP MALL PER YEAR, RM (low / base / high)")
    for case in ("low", "base", "high"):
        fees, spons, paid = mall_revenue(case)
        L.append(f"  {case:<5} paid bookings {paid:>6,.0f}  fees net {fees:>8,.0f}  tenant-sponsored {spons:>7,.0f}  total {fees + spons:>8,.0f}")
    fees, spons, _ = mall_revenue("base")
    contrib = fees + spons - run_cost("base")
    L.append(f"  Base contribution per SDP mall after running costs: RM{contrib:,.0f} a year; "
             f"hardware pays back in {hw_cost('base') / contrib:.1f} years")
    pc = LICENCE - run_cost("base")
    L.append(f"  Partner mall: licence RM{LICENCE:,} - running RM{run_cost('base'):,.0f} = contribution RM{pc:,.0f} a year (partner buys its own hardware)")
    fixed = TEAM[1] + SALES
    n = (fixed - SDP_MALLS * contrib) / pc
    L.append(f"  Fixed central costs RM{fixed:,} a year are covered at {n:.1f} partner malls plus the 4 SDP malls")

    for case in ("base", "low", "high"):
        rows = five_year(case)
        L.append(f"\n7-YEAR ROLLOUT, {case} case, RM thousands")
        L.append(f"  {'Year':<6}{'SDP malls':>10}{'Partners':>10}{'Revenue':>10}{'Cost':>10}{'Net':>10}{'Cumulative':>12}")
        be = None
        for yr, s, p, rev, cost, net, cum in rows:
            L.append(f"  {yr:<6}{s:>10}{p:>10}{rev / 1e3:>10.0f}{cost / 1e3:>10.0f}{net / 1e3:>10.0f}{cum / 1e3:>12.0f}")
            if net > 0 and be is None:
                be = yr
        payback = next((r[0] for r in rows if r[6] > 0), None)
        L.append(f"  First profitable year: {be or 'none within 7 years'}; cumulative payback: {payback or 'after year 7'}")

    # SDP on its own: no partner licences. Treated as a loyalty and footfall programme.
    HOMES = 2000 + 800 + 12800        # [D] SDP homes completed near KL East + Melawati, KLGCC (mid-range), Elmina (A12)
    rev = SDP_MALLS * (fees + spons)
    run = SDP_MALLS * run_cost("base") + TEAM[1]
    capex = PLATFORM_BUILD[1] + SDP_MALLS * hw_cost("base")
    yearly = run - rev + capex / 5
    L.append("\nSDP ON ITS OWN (4 malls, no partners), base case, per year")
    L.append(f"  Revenue RM{rev:,.0f}; running incl. engineer RM{run:,.0f}; one-off RM{capex:,.0f} spread over 5 years RM{capex / 5:,.0f}")
    served = SDP_MALLS * mall_revenue("base")[2] / 0.7          # all bookings, if ~70% are paid (A4)
    L.append(f"  Net cost RM{yearly:,.0f} a year = RM{yearly / HOMES:.0f} per SDP home near the 4 malls ({HOMES:,} homes), "
             f"or RM{yearly / served:.1f} per booking served ({served:,.0f} a year)")
    # Break-even on fees alone: extra paid bookings per busy day per mall needed to cover the net cost.
    need = yearly / (SDP_MALLS * BUSY_DAYS * FEE * (1 - OPERATOR_SHARE - CARD_FEE))
    L.append(f"  Fees alone would need about {pick(PAID_BUSY, 'base') + need:.0f} paid bookings per busy day per mall (base {pick(PAID_BUSY, 'base')}), "
             f"so for SDP it is a loyalty and footfall programme, not a fee business")
    # Partner view: what a partner mall earns vs pays.
    p_cost = LICENCE + run_cost("base") + hw_cost("base") / 5
    L.append(f"  A partner mall pays RM{p_cost:,.0f} a year (licence, running, hardware over 5 years) against RM{fees + spons:,.0f} of fees: "
             f"it buys ParkFlow for footfall and loyalty, as SDP does; so partner licences are upside, not the base case.")

    L.append("\nNot counted (upside for SDP): PRIME value for home sales, spend data, turnover rent from higher tenant sales, "
             "premium-rate income from non-bookers, search time saved (simulate_carpark.py).")
    L.append("[S] sources: PPK Malaysia via The Star (490 malls, 2024); NAPIC via The Rakyat Post (Selangor 95, KL 78, mid-2025); "
             "NVIDIA list price; Tapconet list price; Meta WhatsApp rate card (via Sleekflow, Jul 2025).")
    out = "\n".join(L)
    print(out)
    with open("business_case_results.txt", "w", encoding="utf-8") as f:
        f.write(out.strip() + "\n")


if __name__ == "__main__":
    main()

