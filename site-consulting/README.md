# ParkFlow consulting edition

Open `index.html` for the separate 34-slide presentation. Arrow keys, Page Up/Down and the lower-right controls navigate slides. The `Aa` control enables a reflowing reading mode for narrow screens. Team Hexa is slide 2; slide 26 is a standalone Thank You; slide 27 begins the appendix without switching modes.

This edition now uses ParkFlow's navy/blue identity, Public Sans, official property imagery, authenticated organisation marks and exhibits composed for each argument. The capability and three-part financial sanity-check slides follow the user's composite reference layouts. The main story retains three table-based slides; detailed matrices remain in the appendix.

The existing `site-vnext` deck is not modified by this edition.

Build and export from the repository root:

```powershell
python presentation/build_consulting_deck.py
python presentation/review_consulting_deck.py
```

The PDF is `submission/ParkFlow-Consulting-Deck.pdf`. The builder reads the existing booking model and copies existing prototype/concept assets into this edition's own asset directory. It never calls the old chart-writing entry points. All financial exhibits share one calculation base. Layout-specific content is in `presentation/consulting_art_direction.py`; `premium.css` overrides the archived first-edition treatment.

Public assets can be refreshed with `python presentation/prepare_consulting_assets.py`. This downloads only the explicitly recorded official-site photographs/logos and open-licensed font. Provenance is in `assets/public-assets.json`; the Public Sans licence is in `assets/public-sans-OFL.txt`. Organisation marks identify the proposal recipient or published comparators, not endorsing partners.

Design measurements and rules are in `../guidance.md`. Research corrections, source boundaries and remaining pilot deliverables are in `../docs/deck-design-analysis/gaps-and-evidence.md`. Reproducible visual/layout evidence is in `../docs/deck-design-analysis/consulting-review.json`.

The PDF has selectable text and vector SVG charts; prototype screenshots remain raster. Internal source hyperlinks point to repository analysis files, while public citations point directly to their sources.
