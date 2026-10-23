"""ParkFlow business case: market size, cost sheet, per-mall P&L, 7-year rollout and payback scenarios.

Every input is labelled: [S] sourced, [D] deck/simulation, [A] our assumption to confirm in the
mentoring sprint (vendor quotes, SDP digital team, operator contract).
The base case counts only booking fees, tenant sponsorship and partner licences. Two extra revenue
streams (a card sponsor and a Priority Pass) are shown as pilot targets, not built into the base case.
The premium rate paid by non-bookers in a held zone goes to the parking operator (deck A8), so it is
not SDP revenue here.
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
LICENCE = 2500 * 12             # [A] partner licence, RM per zone per year (RM2,500 a month)
ZONES_PER_PARTNER = 1.5         # [A] zones per partner mall on average: partners are larger malls, and a zone is
                                #     6-10% of a car park (simulate_zone_size.py), so a 3,000-bay mall runs 2-3 zones

# ---------------- Pilot targets: extra revenue per SDP mall, not in the base case ----------------
CARD_SPONSOR = 24000            # [A] a card issuer sponsors the zone ("Priority Zone by <bank>"), RM2,000 a month per mall
PASS_SUBS = 150                 # [A] Priority Pass subscribers per mall
PASS_PRICE = 20                 # [A] RM a month for unlimited Priority Zone bookings (Sunway season parking: from RM140 a month)
PASS_SWAP = 2                   # [A] paid RM4 bookings a month each subscriber would otherwise have made (lost fees)

# ---------------- Cost sheet ----------------
HW = {  # one-off per mall, RM: (low, base, high)
    "Zone plate cameras, both directions (installed)": (8000, 12000, 20000),        # [A] no public price; to quote
    "LED zone sign": (12000, 16300, 16300),                                           # [S] USD 3,475 list (Tapconet), local quote may be lower
    "2 AI boxes (NVIDIA Jetson Orin Nano Super)": (2340, 2340, 2340),                 # [S] USD 249 each
    "4-6 extra cameras at blind spots": (3000, 5000, 9000),                            # [A] RM750-1,500 each
    "Installation and cabling": (5000, 7500, 10000),                                  # [A]
}
PLATFORM_BUILD = (45000, 60000, 100000)    # [A] one-off: production booking tab, rule engine and dashboard built on our
                                           #     working prototype (about a 3-month sprint), not from scratch
RUN_PER_MALL = {  # yearly per live mall, RM: (low, base, high)
    "Cloud hosting": (3600, 4800, 7200),                                              # [A] RM300-600 a month
    "WhatsApp confirmations": (900, 1400, 2000),                                      # [S] Meta utility template ~USD 0.014; ~2 per booking
    "Hardware upkeep (10% of hardware a year)": (3400, 4300, 5700),                   # [A]
}
TEAM = (36000, 48000, 72000)     # [A] engineering support per year: 0.3-0.6 of an engineer (RM120k with on-costs)
                                 #     for 4 zones; doubles beyond 12 live malls
SALES = 30000                    # [A] partner onboarding and support per year, from the first partner
ROLLOUT = [  # (year, new SDP malls, new partner malls)  [A]
    (1, 1, 0),   # KL East pilot, then live
    (2, 3, 6),   # KLGCC, Elmina Lakeside, Melawati; partners from year 2, sold to mall groups (one deal, several malls)
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


def extra_streams(streams):
    """Pilot-target revenue per SDP mall per year: card sponsor and/or Priority Pass.
    The pass is counted net of card fees and of the paid bookings it replaces."""
    rev = 0.0
    if "sponsor" in streams:
        rev += CARD_SPONSOR
    if "pass" in streams:
        rev += PASS_SUBS * PASS_PRICE * 12 * (1 - CARD_FEE)
        rev -= PASS_SUBS * PASS_SWAP * 12 * FEE * (1 - OPERATOR_SHARE - CARD_FEE)
    return rev


def rollout(per_year=6, start=2):
    """SDP malls as in ROLLOUT; partner malls signed per year from the start year (0 = SDP alone)."""
    return [(yr, s, per_year if yr >= start else 0) for yr, s, _ in ROLLOUT]


def five_year(case, streams=(), plan=None):
    c = {"low": "high", "base": "base", "high": "low"}[case]
    fees, spons, _ = mall_revenue(case)
    extra = extra_streams(streams)
    sdp = partners = 0
    cum = 0.0
    rows = []
    for yr, new_sdp, new_p in plan or ROLLOUT:
        sdp += new_sdp
        partners += new_p
        rev = sdp * (fees + spons + extra) + partners * ZONES_PER_PARTNER * LICENCE
        cost = new_sdp * hw_cost(case) + (sdp + partners * ZONES_PER_PARTNER) * run_cost(case)   # running cost per zone
        cost += pick(TEAM, c) * (1 if sdp + partners <= 12 else 2) * (TEAM_Y1 if yr == 1 else 1)
        cost += SALES if partners else 0
        if yr == 1:
            cost += pick(PLATFORM_BUILD, c)
        net = rev - cost
        cum += net
        rows.append((yr, sdp, partners, rev, cost, net, cum))
    return rows


def payback_years(rows):
    """Years until cumulative cash turns positive, assuming each year's cash arrives evenly through the year."""
    prev = 0.0
    for yr, *_, net, cum in rows:
        if cum > 0:
            return yr - 1 + (-prev / net if prev < 0 else 0)
        prev = cum
    return None


def main():
    L = []
    L.append("MARKET SIZE (annual licence value, RM2,500 a month per zone; TAM and SAM count one zone per mall)")
    L.append(f"  TAM  all malls in Malaysia           {MALLS_MY:>4} malls  RM{MALLS_MY * LICENCE / 1e6:5.1f}m a year")
    L.append(f"  SAM  Klang Valley (Selangor + KL)     {MALLS_KV:>4} malls  RM{MALLS_KV * LICENCE / 1e6:5.1f}m a year")
    partners3 = sum(p for _, _, p in ROLLOUT[:3])
    som = SDP_MALLS + partners3
    som_rm = (SDP_MALLS + partners3 * ZONES_PER_PARTNER) * LICENCE
    L.append(f"  SOM  4 SDP malls + {partners3} partners, year 3 {som:>3} malls  RM{som_rm / 1e6:5.2f}m a year "
             f"({som / MALLS_KV:.0%} of SAM malls; partners at {ZONES_PER_PARTNER} zones each)")

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
    pc = (LICENCE - run_cost("base")) * ZONES_PER_PARTNER
    L.append(f"  Partner mall ({ZONES_PER_PARTNER} zones): licence RM{LICENCE * ZONES_PER_PARTNER:,.0f} - running "
             f"RM{run_cost('base') * ZONES_PER_PARTNER:,.0f} = contribution RM{pc:,.0f} a year (partner buys its own hardware)")
    fixed = TEAM[1] + SALES
    n = (fixed - SDP_MALLS * contrib) / pc
    L.append(f"  Fixed central costs RM{fixed:,} a year are covered at {n:.1f} partner malls plus the 4 SDP malls")

    L.append("\nPAYBACK SCENARIOS, base bookings and costs (cumulative cash, RM thousands)")
    L.append(f"  {'Scenario':<52}{'Extra/mall':>11}{'Y1':>7}{'Y2':>7}{'Y3':>7}{'Y4':>7}   Payback")
    scenarios = [("Base: fees, tenant sponsors, partner licences", ()),
                 ("Base + card sponsor (pilot target)", ("sponsor",)),
                 ("Base + Priority Pass (pilot target)", ("pass",)),
                 ("Base + card sponsor + Priority Pass (pilot target)", ("sponsor", "pass"))]
    for name, streams in scenarios:
        rows = five_year("base", streams)
        cum = "".join(f"{r[6] / 1e3:>7.0f}" for r in rows[:4])
        pay = payback_years(rows)
        L.append(f"  {name:<52}{extra_streams(streams) / 1e3:>10.0f}k{cum}   {f'{pay:.1f} years' if pay else 'after year 7'}")
    L.append(f"  Card sponsor RM{CARD_SPONSOR:,} a year; Priority Pass {PASS_SUBS} x RM{PASS_PRICE} a month, "
             f"less {PASS_SWAP} paid bookings a month each it replaces = RM{extra_streams(('pass',)):,.0f} net a year")

    L.append(f"\nSOM AND PARTNER PACE, base bookings and costs (SOM = zones live x RM30,000; partners at {ZONES_PER_PARTNER} zones)")
    L.append(f"  {'Scenario':<52}{'Malls Y3':>9}{'SOM Y3':>9}{'Malls Y7':>9}{'Cash Y7':>10}   Payback")
    saved = globals()["ZONES_PER_PARTNER"]
    for name, streams, plan, zones in [
            ("Base: mall groups, 6 partners a year from year 2", (), rollout(6, 2), saved),
            ("Same, one zone per partner (no per-zone pricing)", (), rollout(6, 2), 1.0),
            ("Previous base: 6 a year from year 3, one zone each", (), rollout(6, 3), 1.0),
            ("12 partners a year from year 2", (), rollout(12, 2), saved),
            ("Base + card sponsor + Priority Pass", ("sponsor", "pass"), rollout(6, 2), saved),
            ("SDP's 4 malls alone, no partners", (), rollout(0, 2), saved),
            ("SDP's 4 malls alone + card sponsor + Priority Pass", ("sponsor", "pass"), rollout(0, 2), saved)]:
        globals()["ZONES_PER_PARTNER"] = zones
        rows = five_year("base", streams, plan)
        y3 = rows[2][1] + rows[2][2]
        y7 = rows[-1][1] + rows[-1][2]
        som_y3 = (rows[2][1] + rows[2][2] * zones) * LICENCE
        pay = payback_years(rows)
        L.append(f"  {name:<52}{y3:>9}{f'RM{som_y3 / 1e6:.2f}m':>9}{y7:>9}{f'RM{rows[-1][6] / 1e6:.2f}m':>10}   "
                 f"{f'{pay:.1f} years' if pay else 'never within 7 years'}")
    globals()["ZONES_PER_PARTNER"] = saved
    L.append("  Partner support stays at RM30,000 a year in every case, which understates the cost of signing 12 malls a year.")

    for case, streams in (("base", ()), ("low", ()), ("high", ()), ("base", ("sponsor", "pass"))):
        rows = five_year(case, streams)
        label = case + (" + card sponsor + Priority Pass" if streams else "")
        L.append(f"\n7-YEAR ROLLOUT, {label} case, RM thousands")
        L.append(f"  {'Year':<6}{'SDP malls':>10}{'Partners':>10}{'Revenue':>10}{'Cost':>10}{'Net':>10}{'Cumulative':>12}")
        be = None
        for yr, s, p, rev, cost, net, cum in rows:
            L.append(f"  {yr:<6}{s:>10}{p:>10}{rev / 1e3:>10.0f}{cost / 1e3:>10.0f}{net / 1e3:>10.0f}{cum / 1e3:>12.0f}")
            if net > 0 and be is None:
                be = yr
        payback = payback_years(rows)
        L.append(f"  First profitable year: {be or 'none within 7 years'}; payback: {f'{payback:.1f} years' if payback else 'after year 7'}")

    # SDP on its own: no partner licences. Treated as a loyalty and footfall programme.
    rev = SDP_MALLS * (fees + spons)
    run = SDP_MALLS * run_cost("base") + TEAM[1]
    capex = PLATFORM_BUILD[1] + SDP_MALLS * hw_cost("base")
    yearly = run - rev + capex / 5
    L.append("\nSDP ON ITS OWN (4 malls, no partners), base case, per year")
    L.append(f"  Revenue RM{rev:,.0f}; running incl. engineering RM{run:,.0f}; one-off RM{capex:,.0f} spread over 5 years RM{capex / 5:,.0f}")
    served = SDP_MALLS * mall_revenue("base")[2] / 0.7          # all bookings, if ~70% are paid (A4)
    L.append(f"  Net cost RM{yearly:,.0f} a year = RM{yearly / SDP_MALLS:,.0f} per mall, "
             f"or RM{yearly / served:.2f} per booking served ({served:,.0f} a year)")
    target = SDP_MALLS * extra_streams(("sponsor", "pass"))
    L.append(f"  With a card sponsor and Priority Pass (pilot targets): net RM{target - yearly:+,.0f} a year")
    # Break-even on fees alone: extra paid bookings per busy day per mall needed to cover the net cost.
    need = yearly / (SDP_MALLS * BUSY_DAYS * FEE * (1 - OPERATOR_SHARE - CARD_FEE))
    L.append(f"  Fees alone would need about {pick(PAID_BUSY, 'base') + need:.0f} paid bookings per busy day per mall (base {pick(PAID_BUSY, 'base')}), "
             f"so for SDP it is a loyalty and footfall programme, not a fee business")
    # Partner view: what a partner mall earns vs pays.
    p_cost = (LICENCE + run_cost("base") + hw_cost("base") / 5) * ZONES_PER_PARTNER
    L.append(f"  A partner mall ({ZONES_PER_PARTNER} zones) pays RM{p_cost:,.0f} a year (licence, running, hardware over 5 years) "
             f"against RM{(fees + spons) * ZONES_PER_PARTNER:,.0f} of fees: "
             f"it buys ParkFlow for footfall and loyalty, as SDP does; so partner licences are upside, not the base case.")

    L.append("\nNot counted (upside for SDP): rewards sign-ups and voucher-led visits, spend data, turnover rent from higher tenant sales, "
             "search time saved (simulate_carpark.py). The premium rate from non-bookers goes to the parking operator (A8).")
    L.append("[S] sources: PPK Malaysia via The Star (490 malls, 2024); NAPIC via The Rakyat Post (Selangor 95, KL 78, mid-2025); "
             "NVIDIA list price; Tapconet list price; Meta WhatsApp rate card (via Sleekflow, Jul 2025).")
    out = "\n".join(L)
    print(out)
    with open("business_case_results.txt", "w", encoding="utf-8") as f:
        f.write(out.strip() + "\n")


if __name__ == "__main__":
    main()

