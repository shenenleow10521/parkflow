# ParkFlow V2 · graphical revision

Open [index-v2.html](index-v2.html). This is an HTML-only revision of the existing consulting deck, based on the user's supplied revision brief. V1 (`index.html`), its shared CSS/JS/assets, the original `site-vnext` deck and every existing PDF are preserved.

## Presentation changes

- The service mechanism now explains proposed three-hour forecasts, rolling optimization, hard current-capacity/commitment checks and repeated replanning.
- Historical occupancy and camera results retain their original task, horizon and site limitations.
- Short topic headings replace the separate takeaway band on every standard slide. Interpretations appear next to the graphic they explain.
- Main exhibits include a capacity timeline, policy trade-off scatterplot, forecast-error lines, a connected commercial model, an annotated cost map, a booking break-even curve and a visit/capture contour map.
- The business section adds conservative/base/higher-demand cases calculated from the same existing model, with explicit support and installed-cost boundaries.
- The eight-week plan is a ten-task Gantt chart with proposed owners and decision milestones.
- The three-horizon roadmap has progressively higher, overlapping curves and shared capability junctions. Heights indicate schematic expansion of scope, not revenue, adoption or measured performance.
- ML forecasting architecture is restored at slide 11 using the `site-vnext` two-model pipeline as its reference, with updated horizons and a separate booking-request path. The original deck and its diagram are unchanged.
- The member visits/spending slide (formerly slide 13) is retained. Ownership, repeated threshold calculations, external partner scenarios, the old policy simulation, the evidence summary and design-record slides are removed from V2.
- Pilot measures are moved to the appendix. The final sequence is 24 main slides including standalone Thank You, then 11 continuous appendix slides (35 total).
- Floating controls are removed. Arrow keys, Space, Page Up/Down and Home/End navigate. **R** toggles reading mode. Phones initially open in reading mode; presentation mode also supports horizontal swipes.
- The appendix retains forecast/optimizer ablation, 50/100/150-bay sizing, stress results, full policy results and benchmark scope.

## Evidence boundaries

The [event-driven study](../analysis/benchmarks/decision_value/report.md) contains 3,000 synthetic policy-day runs and is now the main policy comparison. Only request forecasts vary between its LP variants. It improves the declared preference score versus linear forecasts, but not clearly versus adaptive forecasts; the calibrated fixed buffer has a higher score with a different member/walk-in trade-off. The synthetic relationship between an earlier walk-in wave and a later request surge is an experimental assumption, not a sourced local fact.

The new offline 180-minute rolling LP was implemented and tested in **3,500 synthetic policy-day runs**. The public occupancy test produced **18,074 held-out forecasts across 28 UK car parks**, including 120/180-minute horizons. Booking-demand and turnover tests use separate synthetic training, calibration and test days. See the [completed benchmark report](../analysis/benchmarks/v2/report.md) and [protocol](../analysis/benchmarks/v2/protocol.md).

This is a research harness, not the deployed app or a KL East field trial. Guard-only, averages, learned forecasts and oracle-reference policies have identical main-case operating outcomes. The undetected-count negative control breaks the capacity invariant; a crafted test also demonstrates that an incorrect ledger can break a promise. No local shopper interviews, willingness-to-pay measurements, controlled retention results, supplier quotations or approved landlord-capture rates were supplied.

The historical 2.07% versus 5.34% forecast comparison is not substituted for the new test: stricter availability-time preprocessing changes the sample. The new 180-minute occupancy ensemble MAE is 4.42% of capacity versus 6.02% last week and 4.56% adjusted last week. The 13-extra-weekly-visits example still uses illustrative RM260 spend and 5% effective capture; it is not an observed result or a count of retained shoppers.

## Build

```powershell
python -B presentation/build_consulting_v2.py
python -B presentation/review_consulting_v2.py
```

The builder reads the existing HTML and writes `index-v2.html` and generated SVG charts. `consulting_v2_layout.py` applies the final headings and compositions after the content/benchmark passes. `v2.css` and `v2.js` are isolated to this edition. Shared assets are reused; no PDF is generated.

## HTML verification

The browser review checks all 35 slides (24 main, 11 appendix), slide/source fit, image loading, local references, unique SVG IDs, financial scenario values, keyboard navigation from Thank You into the appendix, three desktop viewport sizes and phone reading mode. It also checks architecture placement, retention of member visits/spending, the agreed cuts and removal of floating controls. Existing deck/PDF hashes are preserved; renders and the machine-readable review stay in the ignored `docs/deck-design-analysis/renders/consulting-v2/` folder. Both benchmark suites retain their independent control tests and checksum-bound results.
