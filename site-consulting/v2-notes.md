# ParkFlow V2 · graphical revision

Open [index-v2.html](index-v2.html). This is an HTML-only revision of the existing consulting deck, based on the user's supplied revision brief. V1 (`index.html`), its shared CSS/JS/assets, the original `site-vnext` deck and every existing PDF are preserved.

## Presentation changes

- The service mechanism now explains proposed three-hour forecasts, rolling optimization, hard current-capacity/commitment checks and repeated replanning.
- Historical occupancy and camera results retain their original task, horizon and site limitations.
- Short topic headings replace the separate takeaway band on every standard slide. Interpretations appear next to the graphic they explain.
- Main exhibits include a capacity timeline, policy trade-off scatterplot, forecast-error lines, a connected commercial model, an annotated cost map, a booking break-even curve and sourced retention-strategy graphics.
- The business section adds conservative/base/higher-demand cases calculated from the same existing model, with explicit support and installed-cost boundaries.
- The eight-week plan is a ten-task Gantt chart with proposed owners and decision milestones.
- The three-horizon roadmap has progressively higher, overlapping curves and shared capability junctions. Heights indicate schematic expansion of scope, not revenue, adoption or measured performance.
- ML forecasting architecture is restored at slide 11 using the `site-vnext` two-model pipeline as its reference, with updated horizons and a separate booking-request path. The original deck and its diagram are unchanged.
- The member visits/spending slide (formerly slide 13) is retained. Ownership, repeated threshold calculations, external partner scenarios, the old policy simulation, the evidence summary and design-record slides are removed from V2.
- Pilot measures are moved to the appendix. The visit/capture sensitivity appendix is removed entirely. The final sequence is 24 main slides including standalone Thank You, then 10 continuous appendix slides (34 total).
- Floating controls are removed. Arrow keys, Space, Page Up/Down and Home/End navigate. **R** toggles reading mode. Phones initially open in reading mode; presentation mode also supports horizontal swipes.
- The appendix retains forecast/optimizer ablation, 50/100/150-bay sizing, stress results, full policy results and benchmark scope.

## Evidence boundaries

The [event-driven study](../analysis/benchmarks/decision_value/report.md) contains 3,000 synthetic policy-day runs and is now the main policy comparison. Only request forecasts vary between its LP variants. It improves the declared preference score versus linear forecasts, but not clearly versus adaptive forecasts; the calibrated fixed buffer has a higher score with a different member/walk-in trade-off. The synthetic relationship between an earlier walk-in wave and a later request surge is an experimental assumption, not a sourced local fact.

The new offline 180-minute rolling LP was implemented and tested in **3,500 synthetic policy-day runs**. The public occupancy test produced **18,074 held-out forecasts across 28 UK car parks**, including 120/180-minute horizons. Booking-demand and turnover tests use separate synthetic training, calibration and test days. See the [completed benchmark report](../analysis/benchmarks/v2/report.md) and [protocol](../analysis/benchmarks/v2/protocol.md).

This is a research harness, not the deployed app or a KL East field trial. Guard-only, averages, learned forecasts and oracle-reference policies have identical main-case operating outcomes. The undetected-count negative control breaks the capacity invariant; a crafted test also demonstrates that an incorrect ledger can break a promise. No local shopper interviews, willingness-to-pay measurements, controlled retention results, supplier quotations or approved landlord-capture rates were supplied.

The historical 2.07% versus 5.34% forecast comparison is not substituted for the new test: stricter availability-time preprocessing changes the sample. The new 180-minute occupancy ensemble MAE is 4.42% of capacity versus 6.02% last week and 4.56% adjusted last week. The national approximate RM260 recalled-spend mean remains a sourced shopper benchmark; no basket-to-landlord-capture conversion is used.

## Financial evidence revision · 9 November 2026

The new zone includes **two additional LPR cameras**, not reuse of the mall entrance cameras. The V2-only [financial model](../presentation/consulting_v2_finance.py) uses published camera/display benchmarks and a MYR-card payment reference including SST on gateway fees. The priced-line subtotal is **RM90,485 + unpriced scope**, including RM79,985 upfront and RM10,500 Year 1 running. Development, works, coverage cameras and running remain unquoted allowances; equipment list prices show zero stock and exclude project taxes. Full [source observations and boundaries](financial-sources.md) accompany the HTML.

Booking, recovery, cost details and executive/decision figures all reconcile to that model. The reference annual contribution is RM7,788.52 before exclusions; five-year booking-only gap RM8,208.48. All paid-volume cases remain scenarios. The spending benchmark uses a dumbbell graphic, while the business context adds SDP's FY2025 committed occupancy. Pilot measures cover member return rates, attributable visits, tenant/mall cash and realised operational savings. No benchmark score or causal retention percentage is converted into money.

After a further source search, SDP's own 2024 MSWG reply was found to confirm KL East turnover-rent income. It does not disclose a marginal capture rate or ParkFlow-induced visit effect. The former visit-to-cash curve, assumed 5% capture and 13-visits example are therefore removed completely, including the appendix sensitivity. The main retention slide instead shows spend-linked credits, visit milestones and targeted offers with primary sources beside each. Retention cash remains unquantified and excluded from reference returns; the deck does not substitute a new unsupported rate.

## Build

```powershell
python -B presentation/build_consulting_v2.py
python -B presentation/review_consulting_v2.py
```

The builder reads the existing HTML and writes `index-v2.html` and generated SVG charts. `consulting_v2_layout.py` applies headings and compositions after the content/benchmark passes; `consulting_v2_financial_slides.py` then applies the V2 financial model and sourced commercial exhibits. `v2.css` and `v2.js` are isolated to this edition. Shared assets are reused; no PDF is generated.

## HTML verification

The browser review checks all 34 slides (24 main, 10 appendix), slide/source fit, image loading, local references, unique SVG IDs, financial scenario values, keyboard navigation from Thank You into the appendix, three desktop viewport sizes and phone reading mode. It also verifies removal of the visit sensitivity and default capture calculator, source links for the proposed growth mechanisms, architecture placement, retention of member visits/spending, the agreed cuts and removal of floating controls. Existing deck/PDF hashes are preserved; renders and the machine-readable review stay in the ignored `docs/deck-design-analysis/renders/consulting-v2/` folder. Both benchmark suites retain their independent control tests and checksum-bound results.
