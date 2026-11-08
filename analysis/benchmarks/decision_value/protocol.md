# Event-driven forecast decision-value study

Specified 8 November 2026, before the new test outcomes. This extends, and does not replace, the completed V2 benchmark. Its purpose is to test whether forecasts change decisions when requests and walk-ins interleave. A favourable result is not guaranteed.

## Scope and shared assumptions

All new requests, trips and predictive demand signals are synthetic. None is observed KL East behaviour. The public Birmingham occupancy benchmark remains separate. In particular, the association between an initial walk-in wave and a later booking-request wave is an **experimental assumption** to test the mechanism; it is not sourced evidence of how shoppers behave.

- Opening lasts 780 minutes. Events occur at minute resolution with a fixed random within-minute ordering of walk-ins and new requests. Actual departures and already accepted arrivals are reconciled first. Controls update every 15 minutes and plan twelve 15-minute buckets (180 minutes). Future counts/outcomes are never supplied to an ordinary policy.
- Booking lead time varies from 15 to 180 minutes. Requests stop 180 minutes before closing so all due windows fit within opening. Grace is 20 minutes, with late arrivals and no-shows reported separately from capacity failures. Drain pending arrivals after closing.
- Each accepted booking reserves one **currently free** physical bay immediately. Walk-ins cannot consume existing promises or two common spare safety bays. Predicted departures never authorize a real promise. All policies use this exact guard, without a separate booking quota.
- Walk-in base rates and lognormal stays follow the earlier simulator's scenario parameters. Mean baseline member requests are 45/day plus occasional synthetic pulses. Pulse timing varies between days; sizes range from 60 to 110 requests. Some pulses have an earlier walk-in wave, some have no advance cue. These are not demand estimates or willingness-to-pay measurements.
- Training: seeds 41000–41159 (160 synthetic days); calibration: 51000–51039 (40 days); evaluation: 61000 onward. No test day is used to select a model, fixed buffer, weight or scenario. Every policy receives the same immutable external events.

## Isolation and baselines

The LP and occupancy/survival models are identical for every forecast variant. Only the **new booking-request forecast** changes. All use the same forecast of future walk-in demand. The common survival model is fitted to completed training trips and knows only an active car's observed age, member status and requested duration, never its actual future departure.

Policies: guard only; fixed additional buffers 5 and 10; a fixed buffer chosen on calibration days from 0/5/10/15/20/30/40; reactive next-window adaptive forecast; the same LP with slot/weekday averages, adaptive averages, linear ridge forecasts, or LightGBM forecasts; and a future-request-count oracle reference. The oracle retains the same fitted survival and future walk-in inputs and is not a global upper bound.

All ordinary predictors have access to the same as-of time and past 5/15/30/60-minute request and walk-in counts. Both ridge and LightGBM use those features. Historical/adaptive baselines receive the same histories; no calendar/surge label or latent intensity is given exclusively to ML. Adaptive averages scale the historical profile using recent request and walk-in intensity.

The LP plans member acceptances and walk-ins. It can protect space **before future requests arrive**, including the upcoming first bucket. Only its immediate discretionary protection target is executed. When a new request is accepted, discretionary protection is converted into a real claim rather than counted twice. Future allocations remain advisory. LP infeasibility falls back to zero new walk-ins and is reported.

## Objectives and settings

Primary operating score: 5 × valid accepted member arrivals served + walk-ins admitted. The weight is a declared service preference, not RM, landlord value or a commercial return. The LP uses the common 90% show-up prior for hypothetical requests. Booking and walk-in counts are always reported separately so a weighted gain cannot conceal a service trade-off. Idle protected bay-hours are integrated at minute resolution only when a walk-in is denied.

Evaluate all ten policies in:

1. Mixed demand waves, 100 bays: 60 paired days (includes days with no pulse and pulses without an advance cue).
2. Quiet/no-pulse demand: 30 paired days, an expected low-value setting.
3. Unannounced pulses: 30 paired days; the preceding walk-in cue is absent.
4. Shifted cue timing: 30 paired days; the relationship changes out of distribution.
5. 50 bays, same demand: 30 days.
6. 150 bays, same demand: 30 days.
7. Longer lead times (90–180 minutes): 30 days.
8. Weights 1 and 10: 30 days each on the main mixed generator; choose the fixed buffer on calibration separately for each weight.

There is no post-test search for a favourable seed or a best-looking subset. Report all settings. The earlier V2 null result remains valid for its earlier setup.

## Decision criteria and reporting

- Primary comparisons: learned-forecast LP minus adaptive-forecast LP, linear-forecast LP and calibration-selected fixed buffer. Also show guard-only and historical-mean results.
- Resample paired days 2,000 times to report 95% intervals for fulfilled member arrivals, walk-ins and weighted operating score. Intervals reflect Monte Carlo uncertainty conditional on this generator, not real-world validity. Comparisons are exploratory; no multiple-comparison-adjusted general superiority claim.
- Report request forecast MAE/WAPE across all twelve horizons and 30/60/120/180-minute cumulative horizons, and how often ordinary first-action protection differs between forecast variants.
- Report request acceptance/rejection, no-show/late outcomes, physical and promise invariant violations, solver failures, idle bay-hours, and the trade-off by weight and capacity.
- The experiment supports only a conditional mechanism claim if learned forecasts improve actual decisions against strong baselines. Prediction-error improvements alone do not establish operating value. No gain means no gain under this setup; do not rewrite or suppress that result.
- No local shopper-demand, retention, installed-cost or financial-return conclusion follows from this study.

Code: `analysis/benchmark_decision_value.py`. Structured results, full setting tables, paired intervals and the final report live alongside this protocol; raw per-day results remain in ignored `analysis/benchmark_data/`.
