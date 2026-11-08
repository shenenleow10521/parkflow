# ParkFlow presentation: measured design guidance

## Current direction: property, product and investment

The user's latest approved direction supersedes the red consulting treatment below. Continue working only in `site-consulting/`; preserve `site-vnext/` and its existing exports.

- **Identity:** deep navy `#102A43`, ParkFlow blue `#245BD8`, white and cool neutral surfaces. Red is not the presentation's primary colour. Retain the authentic colours of third-party organisation marks.
- **Typography:** self-hosted Public Sans, a font identified in the supplied BDR reference, with medium/semibold sentence-case headlines and clear body hierarchy. Original font licence is included with the asset.
- **Composition:** design the exhibit around the argument. Use property photography, large product views, spatial service illustrations, operational accounting, linked diagnostic boxes, paired charts, financial waterfalls, a timeline and a decision map.
- **Brand assets:** official SDP, 1 Utama, ONECARD and Sunway Pyramid marks identify the recipient or comparator. They do not imply partnership or endorsement. Official KL East photography anchors the proposal to a real property.
- **ParkFlow identity:** a restrained original wordmark, with a two-direction flow motif. Do not borrow an unrelated premium brand's mark to imply ParkFlow's identity.
- **Main-story tables:** retain only meaningful numerical matrices and the pilot scorecard. Detailed cost, method and evidence tables belong in the appendix.
- **Lighter opening, denser business:** preserve the user's preferred density ramp; neither a wall of text nor a recurring heading/band/table template satisfies it.

### Composition contracts from the user's latest examples

**Capability analysis:** a roughly 2:1 split. The large panel links site/integration questions to operating impacts, with arrows and a specific concluding action. The smaller panel combines a real property image, a short asset-reuse argument and the items to verify. Distinguish unverified capability questions from documented shortcomings.

**Feasibility and sanity checks:** one common model statement above three aligned panels. Each panel contains a question, a small quantitative chart, an interpretation and a decision boundary. The new slide links paid demand, zone contribution, the capital-recovery hurdle and incremental visits using the same model. Do not manufacture market sizes or invent measured demand to populate the charts.

**Product and place:** show the actual app and operator prototype at useful scale. Use the official property photograph on the cover/location/close; label the proposed zone illustration as a concept rather than a real surveyed floor plan.

Implementation is in `premium.css` and `presentation/consulting_art_direction.py`. `deck.css` retains the base layout primitives. Source provenance, URLs and asset hashes are in `site-consulting/assets/public-assets.json`.

### Current-edition verification

**V2 graphical revision, 8 November 2026:** start each slide with a short topic heading; remove the separate takeaway band and put interpretations beside their exhibit. Use the ML forecasting architecture, scatterplot, forecast lines, commercial value map, cost map, break-even curve, visit contour and task-level Gantt. Horizon curves overlap and reach different scope levels with shared junction nodes; heights are not financial projections. The final trimmed V2 has 24 main slides and 11 continuous appendix slides, with Team second and standalone Thank You before the appendix. Keep member visits/spending; move pilot measures to the appendix. Floating controls are removed. These choices supersede the V1 composition counts below for V2 only.

The current build has 34 slides: 26 main (Team Hexa second, standalone Thank You last) followed continuously by 8 appendix slides. The main story uses tables only for booking-volume sensitivity, retention sensitivity and the pilot scorecard. Ten slides include real property imagery, official marks or product/concept visuals.

The capability analysis combines linked question/impact boxes, a property image, asset-reuse notes and a conclusion. The financial sanity-check exhibit combines three quantitative charts, interpretations and validation boundaries. Its operating break-even calculation holds the fee mix fixed; the extra-visit scenario uses the same recovery gap as the rest of the model.

The final review found zero content/source overflow or browser errors. It checked 1600 × 900, 1280 × 720, 1366 × 768, 1920 × 1080, and a 390px reading mode. Contrast ratios are 14.64:1 navy/white, 6.05:1 muted ink/white, 5.89:1 blue/white, and 5.53:1 muted ink/pale surface. The PDF has 34 selectable-text landscape pages.

Business/implementation OCR word median is 148, with a 10.49% word-box footprint; product median is 129 with an 8.15% footprint. These are descriptive results, not targets to inflate. The revised composition intentionally distributes information through photography, diagrams and charts rather than maximizing text or edge counts.

## Archived first-edition brief and measurements

The remaining red/Arial specifications and first-edition output numbers are a historical record of the initial reference reproduction. They are superseded visually by the direction above. Original PDF measurements, metric definitions, evidence boundaries and the preservation requirement still apply.

## Scope and reference precedence

Build a **separate deck** in `site-consulting/`. Do not change `site-vnext/`, its assets, its existing PDFs, or the earlier deck generators. The user's consulting photographs are the principal visual reference; the two supplied BDR PDFs provide measurable supporting examples of composition and density. The opening should remain easier to absorb than the financial and implementation sections.

For this new deck, this document supersedes the cinematic/signage styling in `DESIGN.md`. It does not change the application or original presentation design system. Keep Team Hexa on slide 2, one standalone Thank You slide, and the appendix in the same continuous sequence.

## Measurement provenance

Measured sources:

| Source | Scope | Method and limits |
|---|---|---|
| `C:\Downloads\FINAL_BDR_PITCHDECK.pdf` | All 15 pages; main content pages 2–12 | 960 × 540 PDF points, flattened images. Rendered at 1600 × 900 and measured with Tesseract. Original fonts and point sizes cannot be recovered reliably. |
| `C:\Downloads\BDR_17_AC2026.pdf` | All 30 pages; main content pages 2–15 | 1440 × 810 PDF points. Native text/font/position extraction plus the same rendered OCR method. Appendix spreadsheet screenshots require OCR to count their contents. |
| `site-vnext/index.html` | All 32 visible slides | Chromium at 1600 × 900; DOM text ranges, computed font styles, rendered screenshots, and the same OCR method. |
| Three consulting photographs in the conversation | Market-share exhibit, value waterfall, strategy/customer journey | Visually inspected. Original image files were not exposed on disk, so no machine-sampled colours, exact fonts or pixel measurements are claimed for these photographs. Perspective, screen tint and camera moiré affect their appearance. |

Reproduce with `python presentation/measure_deck_design.py`, then `python presentation/measure_deck_design.py --enrich-ocr`. Raw measurements and contact sheets are in `docs/deck-design-analysis/`.

All pixel dimensions below refer to a **1600 × 900 design canvas**. PDF points and CSS pixels are not interchangeable: normalize by `1600 / source_page_width` first.

Documented methods: [PyMuPDF text and position extraction](https://pymupdf.readthedocs.io/en/latest/recipes-text.html), [Tesseract command-line/OCR output](https://tesseract-ocr.github.io/tessdoc/Command-Line-Usage.html), [OpenCV Canny edge detection](https://docs.opencv.org/4.x/da/d22/tutorial_py_canny.html), and [W3C minimum contrast](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html). The active-grid metric is a project-specific descriptive proxy built on Canny, not an established consulting quality score.

### Comparable measurements

The following are medians. Both references and ParkFlow use the same 1600-pixel OCR method in the two OCR columns.

| Group | Pages | OCR words | OCR word-box footprint | Active detail grid |
|---|---:|---:|---:|---:|
| FINAL BDR main content | 2–12 | 183 | 12.27% | 86.11% |
| BDR 17 main content | 2–15 | 194 | 15.25% | 90.97% |
| ParkFlow product/problem opening | 3–12 | 102 | 6.27% | 45.48% |
| ParkFlow business case | 13–22 | 116 | 8.66% | 47.57% |

Definitions:

- **OCR words:** Tesseract `--psm 11`, minimum confidence 40. Includes labels and readable text inside pictures. It is a proxy, not a fact count or writing quota.
- **OCR word-box footprint:** union of recognized word bounding rectangles divided by full slide area. It measures glyph-region occupancy, not total chart/panel area.
- **Active detail grid:** divide the image into 16 × 9 cells of 100 × 100 pixels. A cell is active if over 1.5% of its pixels are Canny edges (thresholds 70/160). This describes distribution of detail. Rules, decoration and photographs can increase it without adding meaning.
- **Light-neutral area:** saturation below 20/255 and value above 225/255. This includes white panels and pale backgrounds; it must not be called empty space.
- **Native/DOM text footprint:** font boxes have different padding from OCR glyph boxes. Do not compare the native 25.77% BDR footprint directly with the OCR 12.27% FINAL footprint.

### Typography and geometry actually observed

| Detail | Measurement | Design consequence |
|---|---|---|
| BDR 17 main titles | Lora Bold, approximately 36 native points = 40px on common canvas | The editable reference uses much smaller titles than current ParkFlow. The serif is specific to that reference, not a required consulting convention. |
| BDR 17 body | Mostly Public Sans; frequent normalized sizes 17.8, 18.9, 20 and 24.4px | Useful analysis fits through a measured hierarchy and concise labels. |
| ParkFlow business headings | Typically 76px | Approximately 1.9× the height of the reference's nominal 40px title. Reduce the heading before reducing body readability. |
| BDR 17 recurring title origin | x ≈ 64.6px, y ≈ 24.3px | The header has a stable anchor across slides. |
| ParkFlow recurring content origin | x = 120px | Current horizontal padding consumes 7.5% on either side; a 64px inset recovers 112px of usable width. |
| ParkFlow business title top | Investment ≈102px; revenue ≈114px; GTM ≈190px | Vertical centering creates inconsistent top anchors and unused space. |
| FINAL BDR main text left edge | Approximately 27–32px on sampled slides | Its tighter margins are measurable, but a 64px safe inset is preferable for this deck's projection/readability. |

Selected page comparisons:

| Exhibit | OCR words | OCR footprint | Active grid |
|---|---:|---:|---:|
| FINAL BDR p8, business model | 206 | 12.27% | 82.64% |
| FINAL BDR p9, financial dashboard | 174 | 7.99% | 77.08% |
| FINAL BDR p10, phased delivery | 280 | 12.37% | 99.31% |
| BDR 17 p4, competitor matrix | 246 | 17.50% | 90.97% |
| BDR 17 p14, cost forecast + methodology | 150 | 12.00% | 75.69% |
| BDR 17 p15, revenue + impact | 143 | 12.87% | 79.17% |
| ParkFlow pilot investment | 130 | 9.45% | 52.78% |
| ParkFlow go-to-market | 104 | 7.96% | 45.83% |
| ParkFlow horizons | 120 | 7.25% | 40.97% |

BDR 17 p13 contains visible overlapping roadmap labels; OCR recognizes 190 words versus 360 native tokens. This is a concrete warning against treating a higher word count as a better slide.

## Visual contract for the separate deck

Scene: mall management, finance and operations review the case on a meeting-room screen and inspect the PDF afterward. The visual language should resemble the supplied white/red consulting exhibits: restrained, aligned, comparative and easy to scrutinize.

Use the photographs' hierarchy and exhibit logic. Do not combine the orange Palm2Palm identity, blue PosShop identity, and red consulting identity into a multicolour theme. Use the red consulting lane consistently; retain navy for the ParkFlow series/comparison, with grey peers.

### Canvas and grid

| Token | Specification |
|---|---|
| Design canvas | 1600 × 900, 16:9 |
| Safe left/right | 64px each; 1472px usable width |
| Header | Fixed top anchor; 40–52px topic title; no vertical centering |
| Context/takeaway band | Below header, neutral grey fill, approximately 42–54px high |
| Exhibit area | Starts around y = 160px; ends before y = 790px |
| Sources | Dedicated strip near bottom; 13–15px, dark enough to read |
| Footer | Fine grey rule, section labels, page number; no floating dashboard HUD |
| Column gutter | 24–32px |
| Chart + interpretation | Approximately 60:40 or 65:35 |
| Analysis matrix | Full-width, 3–5 meaningful columns |
| Section-to-section gap | 24–32px |
| Related-label gap | 8–12px |
| Table cell padding | 10–14px; tighter only in appendix |

Anchor all slide bodies to the same top grid. Permit generous whitespace on cover, team and Thank You; analytical whitespace should separate arguments rather than surround an undersized exhibit.

### Typography

The photographs' exact family is unverified. Use **Arial** as an explicit implementation choice to reproduce their neutral sans-serif tone, with real regular/bold weights. Use one family for headings, charts, tables and footnotes. This is a reference-reproduction task, so neutral typography takes precedence over a distinctive brand-font search.

| Role | At 1600 × 900 | Rules |
|---|---:|---|
| Cover | 64–76px | Maximum two lines; no condensed signage treatment |
| Main topic title | 40–44px | Bold, red; short topic, no oversized display word wrapping |
| Takeaway band | 23–25px | Sentence case; states the question answered or implication |
| Exhibit/module title | 23–27px | Bold; names the measure and unit |
| Main body | 20–23px | 1.25–1.4 line height; 45–70 characters per line |
| Opening explanation | 24–27px | More air, fewer simultaneous concepts |
| Table/chart labels | 18–21px | Unit, denominator and scenario visible |
| Sources/notes | 13–15px | Secondary, readable, never the sole location of a critical limitation |

Keep display headings separate from the takeaway. The photographs use descriptive topic headers; not every title needs to become a long conclusion sentence. Use the takeaway band to express the argument precisely.

### Palette and pairing

The following are **chosen reproduction tokens**, not claimed colour samples from the photographed screen:

| Role | Hex | Use |
|---|---|---|
| Canvas | `#FFFFFF` | Continuous white base |
| Main ink | `#1A1A1A` | Body and data labels |
| Muted/source ink | `#595959` | Notes and supporting labels |
| Consulting red | `#C00024` | Main titles, focal bars and one critical implication |
| Navy | `#17365D` | ParkFlow comparison series and structural headings |
| Grey series | `#9299A3` | Comparator data |
| Pale grey panel | `#F0F1F3` | Context bands and selected table rows |
| Rule | `#CDD0D5` | Dividers and light chart gridlines |

Programmatically check contrast against the actual background. Use red/navy/dark ink on white and white on red/navy. Grey chart fills are acceptable as shapes; text over them still needs a suitable contrast pair. Preserve a legend and labels so hue is never the only encoding.

Native reference colours actually recovered from BDR 17 include black `#000000`, navy `#002060`, title blue `#5E83D2`, panel blue approximately `#E9F0FF`, and white. FINAL BDR palette values are quantized raster approximations, not editable source colours. Its p8 palette includes a warm dark red around `#9E383D`; its p2 uses orange around `#C87047`.

Avoid glows, gradient text, neon status decoration, fake glass, trading-card team introductions, floating controls inside slide content, and heavy rounded containers. Keep traffic-light colours inside operational examples where they carry meaning.

## Density ramp

The ranges below are design targets informed by measurements, not claims that word count determines quality. Count meaningful narrative separately from microscopic text inside product screenshots.

| Slide class | Narrative-word guide | Detail distribution guide | Composition |
|---|---:|---:|---|
| Cover / Thank You | 15–45 | Deliberately low | Title, promise, identity |
| Team | 50–100 | Moderate | Five clean name/role columns, no badges or faux equipment |
| Opening problem / product | 60–120 | Roughly 45–65% active grid | One physical explanation, 2–3 supporting facts |
| Product evidence | 100–160 | Roughly 55–75% | One chart/table plus evidence boundary |
| Business / implementation | 140–220 | Roughly 65–85% | One main exhibit, 2–4 implications and explicit assumptions |
| Appendix | 160–280, or a readable data table | Content-dependent | Traceable methods, reconciliation and sources |

Do not force more copy into an already complete chart slide. Do not reduce body size to make an arbitrary word target. Some numeric tables communicate far more than their word count suggests.

## Exhibit patterns to reproduce

1. **Segment comparison:** shared scale; grey comparator; highlighted focal series; direct labels; denominator and period; short implication beneath. The mall-spend exhibit must state that the survey is correlational.
2. **Waterfall:** start, individually reconciled additions/deductions, final total; connecting lines; consistent units. Distinguish operating contribution from fully loaded profit.
3. **Two-level strategy slide:** upper operating journey; lower financial/operational workstreams. Align each initiative to owner, deliverable and decision gate.
4. **Competitor matrix:** compare capabilities, not logos alone. 'Not established in reviewed source' is different from 'does not exist'.
5. **Risk/mitigation matrix:** trigger, consequence, response, owner and evidence required. Avoid generic lists of 'privacy/security/scalability'.
6. **Pilot scorecard:** metric, denominator, baseline, decision criterion, data owner and decision date. Proposed targets remain clearly proposed.
7. **Roadmap:** horizon bands above aligned workstreams below; keep dates, gate labels and ownership legible. Do not copy the overlapping reference roadmap.

Every quantitative exhibit requires a title, unit, period, scenario, direct source and a limitation if it changes the decision.

## Content gaps to close in the separate deck

The detailed register is `docs/deck-design-analysis/gaps-and-evidence.md`.

| Gap | Required correction |
|---|---|
| No compact executive recommendation | Add a situation/question/recommendation/decision slide after team. |
| Existing KL East infrastructure omitted | State that the official mall page already advertises LPR. Survey reuse and integration before buying duplicate equipment. |
| Simulation policy and proposed gate differ | Present the full policy comparison. Do not attribute forecast-policy efficiency results to an untested deterministic gate implementation. |
| CV generalization overstated | Say 'held-out cameras at the same outdoor site', not independent new sites or proven indoor performance. |
| Inconsistent retention target | Derive visit thresholds from the same RM81.5k capital and RM7,775.40 annual contribution model. |
| Licensing margin inconsistent with zone OPEX | Use the same RM10.5k annual zone allowance in the partner scenario; show all remaining exclusions. |
| Retail turnover treated like landlord revenue | Apply an explicit effective capture scenario; do not assume the whole shopping basket reaches SDP. |
| Missing baseline and causal test | Define matched/control comparisons, blocked or randomized days, denominator and operating logs. |
| Budget scope is incomplete | Identify barrier/boundary, controller, network, support allocation, tax and contingency as quote/sign-off items. |
| Procurement/ownership unclear | Show who approves, operates, integrates, pays and owns the scale decision. |
| Portfolio overcount | Distinguish three wholly owned malls from JV opportunities. |
| Weak source traceability | Footnote every public claim; separate live-verified prices, older records, model outputs and unsupplied site facts. |

## Acceptance and replication limits

- The current deck's SHA-256 baseline is `62EB8B3AA1CE971016ABECEE50D28017F735CBF88E0E1A0D0D8FA52D3092C740`; verify it at handoff.
- The separate deck must have a fixed header grid, clear white/red/navy/grey hierarchy, aligned exhibits, and the agreed density ramp.
- Replication is of the references' composition and analytical treatment. No claim of pixel-identical reproduction is justified for photographed, perspective-distorted slides with unavailable source fonts/assets.
- PDF output must retain selectable text; native SVG charts should remain vector where possible.
- Check every slide for content overflow, readable captions, missing assets, console errors, arithmetic reconciliation, and meaningful links.
- Verify 1600 × 900 and smaller 16:9/laptop presentations. A fixed-canvas presentation may scale as a whole; expose a reading mode for narrow screens rather than squeezing dense tables into phone-width columns.
- Any still-missing site evidence stays named as a pilot deliverable with an accountable role. Public research cannot manufacture signed quotes, integration access, baseline demand or incremental loyalty impact.

## Built edition and measured result

The separate edition is `site-consulting/index.html`; its 33-page PDF is `submission/ParkFlow-Consulting-Deck.pdf`. There are 25 main slides (including standalone Thank You) and 8 appendix slides. Build with `python presentation/build_consulting_deck.py`; review/export with `python presentation/review_consulting_deck.py`.

| Measure | Original ParkFlow business p13–22 | Consulting business/implementation p13–24 | Reference main-content medians |
|---|---:|---:|---:|
| Typical topic heading | 76px | 42px | BDR 17: 40px |
| Content left anchor | 120px | 64px | BDR 17 recurring title: 64.6px |
| Visible OCR word median | 116 | 172 | FINAL: 183; BDR 17: 194 |
| OCR word-box footprint | 8.66% | 11.39% | FINAL: 12.27%; BDR 17: 15.25% |
| Active detail grid | 47.57% | 72.22% | FINAL: 86.11%; BDR 17: 90.97% |

Opening slides p4–10 have a lower OCR word median of 124 and active grid median of 59.72%. The business section therefore becomes visibly denser while retaining more breathing room than the dense BDR reference. The compared groups are purposeful content subsets, not identical topics, so these are descriptive comparisons rather than controlled experiments.

Measured chosen colour pairs on white: primary ink 17.40:1, source ink 7.00:1, red 6.43:1, navy 12.19:1. White on red/navy gives the same 6.43:1 / 12.19:1 ratios. These pairs exceed the 4.5:1 body-text threshold.

Review recorded no content/source overflow, broken images or browser errors. The canvas was checked at 1600 × 900, 1280 × 720, 1366 × 768 and 1920 × 1080, with a separate narrow-screen reading mode. PDF verification confirmed 33 landscape pages, selectable text and the Thank You → appendix order. Visual inspection supplements the programmatic checks.

Evidence artifacts:

- `docs/deck-design-analysis/summary.json`: reference/current medians and native font evidence.
- `docs/deck-design-analysis/slide-metrics.csv`: per-slide comparable measurements.
- `docs/deck-design-analysis/reference-measurements.json`: source word boxes, font spans and palettes.
- `docs/deck-design-analysis/parkflow-measurements.json`: unchanged original deck measurements.
- `docs/deck-design-analysis/consulting-review.json`: new layout, density, contrast and preservation checks.
- `docs/deck-design-analysis/consulting-contact.jpg`: complete new deck overview.
