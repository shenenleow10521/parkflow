# ParkFlow presentation tools

The current property/product presentation is [site-consulting/index.html](../site-consulting/index.html). The preserved original presentation is [site-vnext/index.html](../site-vnext/index.html). Their assets and current PDF exports remain in place.

## Current deck

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

