# ParkFlow — Predictive Parking Command Centre

Hackathon prototype for the Sime Darby Property University Hackathon.
KL East Mall pilot concept · illustrative layout · simulated data.

![Operator command centre](docs/screenshots/operator-overview.png)

| Driver app: home | Guidance | My car |
|---|---|---|
| ![Driver home](docs/screenshots/driver-home.png) | ![Guidance](docs/screenshots/driver-guidance.png) | ![My car](docs/screenshots/driver-my-car.png) |

## Live demo

With GitHub Pages serving the `docs/` folder (Settings → Pages → Deploy from branch → `main` / `docs`):

- Operator command centre: `https://<user>.github.io/<repo>/`
- Driver app (open on a phone): `https://<user>.github.io/<repo>/driver.html`

Or open `docs/index.html` and `docs/driver.html` straight from a clone.

## Run it

Two pages, one simulation engine:

- `docs/index.html` is the operator command centre (3D model, allocation, forecasts, impact).
- `docs/driver.html` is the driver app for shoppers: level board, "I'm on my way" guidance with a
  live floor map, special-bay booking, parked confirmation, find-my-car and simulated pay-and-leave.
- `dist/parkflow.html` and `dist/parkflow-driver.html` are the same pages as body fragments, for hosts that
  add their own HTML skeleton.

Open either in any modern browser. No server, credentials or internet needed
(the Barlow fonts load from Google Fonts when online and fall back to system fonts offline).

## Rebuild

Requires Node 18+ and TypeScript (`npm i -g typescript`).

```
node tools/build.mjs        # tsc -> bundles -> docs/ (standalone site) and dist/ (fragments + local test pages)
python3 tools/functional.py # optional: Playwright acceptance checks for the operator view (25 checks)
python3 tools/driver_flow.py /tmp/drv  # optional: driver app flow test and screenshots (15 checks)
node tools/bundle.mjs /tmp/core.js --core --test tools/core-test.js && node /tmp/core.js   # simulation checks
```

## Code map

| Folder | What it does |
|---|---|
| `src/core/layout.ts` | Three-level schematic car park, one-way lane graph, 180 bays and their types |
| `src/core/scenarios.ts` | Five scenarios, seeded demand generation (arrivals, durations, eligibility, initial occupancy) |
| `src/core/sim.ts` | 1-second discrete-time simulation: movement, parking, departures, reservations, events |
| `src/core/allocation.ts` | Hard constraints + weighted, normalised zone score with plain-language explanation |
| `src/core/forecast.ts` | History-only and history + intent forecasts with editable assumptions |
| `src/core/metrics.ts` | Matched comparison runs (unguided baseline vs ParkFlow) |
| `src/render/gl3d.ts` | WebGL2 renderer: procedural car park and cars, per-floor shadow maps, HDR bloom, bay indicator lights, ceiling lights, camera coverage, guidance route, picking |
| `src/render/scene3d.ts` | Canvas fallback renderer for devices without WebGL2 |
| `src/ui/*` | Level board, KPI strip, inspector, pages, charts, driver app preview, presentation mode |
| `src/mobile/app.ts` | Driver app: screens, guidance wording, booking, pay and leave |
| `src/mobile/map.ts` | Live SVG floor map with a camera that frames the car, its target zone or the walk to the lift |
| `src/mobile/motion.ts` | Motion (motion.dev) adapter with a Web Animations fallback and reduced-motion support |
| `src/styles.css` | Design tokens (top of file) and layout |

## Design notes

- Dark operations-room theme so the lit 3D model and indicator colours read on a projector.
- Parking-sign blue is the only interface accent. Status colours match the bay lights in the model
  (green free, red taken, blinking amber leaving soon, purple held, blue accessible, cyan EV) and the
  zone colours match the painted pillar bands (A blue, B yellow, C orange).
- The level board is drawn like the dot-matrix availability sign at a mall entrance; clicking a
  level isolates that floor in the model.
- Barlow (a typeface modelled on road signage) for text, Barlow Semi Condensed for numbers.
- Layers menu in the 3D view: bay lights, guidance route, camera coverage, slow orbit.

## Driver app notes

- Uses the Motion library (`motion@11.11.13` from jsDelivr) for screen pushes, spring sheets, the rolling
  level counts, instruction changes and the route draw-on. Without it (offline), the same animations run on
  the Web Animations API; the about panel on desktop shows which engine is active.
- "I'm on my way" adds the driver's car to the simulation as an intent signal, so it shapes the forecast and
  is guided by the same allocation engine as every other car. "I'm at the entrance" skips the drive there.
- Light and dark themes follow the phone setting. Payments are simulated; no card details are collected.
