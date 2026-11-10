# ParkFlow presentation tools

The current property/product presentation is [site-consulting/index.html](../site-consulting/index.html). The preserved original presentation is [site-vnext/index.html](../site-vnext/index.html). Their assets and current PDF exports remain in place.

## Current deck

The separate [V2 HTML deck](../site-consulting/index-v2.html) revises the planning mechanism, validation protocol and commercial tests. It reuses the existing assets and leaves V1 and all PDFs unchanged. Build and check V2 without exporting a PDF:

```powershell
python -B presentation/build_consulting_v2.py
python -B presentation/v2_cost_breakeven_slide.py
python -B presentation/v2_capex_opex_slide.py
python -B presentation/v2_roadmap_slide.py
python -B presentation/v2_redesign_slides.py
python -B presentation/v2_narrative_order.py
python -B presentation/review_consulting_v2.py
```

[V2 revision notes](../site-consulting/v2-notes.md) describe the evidence boundaries.

`v2_graphics.py` generates the data plots and roadmap as inline SVG. Standalone SVG exports and review renders are disposable, ignored build products. Earlier preview pages and draft graphics plans have been removed.

V2 now reads the [completed offline benchmarks](../analysis/benchmarks/v2/report.md) through `consulting_v2_benchmarks.py`. Reproduction commands are in [analysis/README.md](../analysis/README.md). These experiments do not deploy the optimizer into the browser prototype or validate local customer behaviour.

`consulting_v2_layout.py` adds the approved graphical revision and the [event-driven comparison](../analysis/benchmarks/decision_value/report.md): topic headings, ML forecasting architecture adapted from `site-vnext`, scatter/line/contour exhibits, a cost map, a task-level Gantt and connected horizon curves. The final narrative pass keeps 23 main slides followed continuously by 11 appendix slides (34 total). It removes the standalone site-context, booking-sensitivity and turnover-rent slides, retains the six-month implementation plan, and moves exception/fault handling to the appendix. The retained business sequence is commercial model, CAPEX/OPEX, booking economics, then cost and break-even. The member visits/spending slide is retained; pilot measures are in the appendix. `v2.js` provides navigation without floating controls; **R** toggles reading mode.

```powershell
python presentation/build_consulting_deck.py
python presentation/review_consulting_deck.py
```

Output: [ParkFlow-Consulting-Deck.pdf](../submission/ParkFlow-Consulting-Deck.pdf).

`consulting_art_direction.py` composes the individual exhibits. `booking_economics.py` supplies the shared financial model. `prepare_consulting_assets.py` refreshes the recorded official/public assets. `measure_deck_design.py` reproduces the reference measurements; [guidance.md](../guidance.md) documents the design and evidence boundaries.

## Preserved original deck

```powershell
python presentation/audit_web_deck.py
python presentation/export_html_pdf.py --with-appendix
```

Outputs: `ParkFlow-Main-Deck.pdf`, `ParkFlow-Appendix.pdf`, and `ParkFlow-Deck-With-Appendix.pdf` in `submission/`. `generate_web_charts.py` and `draw_ml_pipeline.py` remain available for its chart assets; their generation commands write to the original deck, so run them only when deliberately updating it.

## Historical files

The old PowerPoint generator, its snapshot/rendering directories and superseded exports are in [archive/2026-11-07](../archive/2026-11-07/). The generator retains its historical path assumptions; restore the recorded paths and companion workspace assets before running it. The archive README links to a checksum-verified move journal.

## Narrative decisions

- Accepted bookings are protected by deterministic available-to-promise control using gated entry/exit observations and the reservation ledger.
- Forecasting is advisory and covers the wider car park; it does not override the booking guarantee.
- Priority Zone booking is a member privilege. Non-members receive broad general-parking guidance only.
- The base case is an SDP-sponsored KL East lighthouse. External commercialisation is a gated Horizon 3 option, not assumed pilot revenue.
- Retention and GTO outputs are labelled as illustrative scenarios until measured in the pilot.

