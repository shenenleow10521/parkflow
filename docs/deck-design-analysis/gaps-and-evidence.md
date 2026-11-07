# Gaps closed in the separate consulting deck

Research checked 7 November 2026. Original presentation files are preserved. Public sources support contextual facts; internal text outputs support prototype results. Neither is a substitute for a live KL East pilot.

| Priority | Missing or misleading element | Finding / correction | Where addressed | Still requires site evidence |
|---|---|---|---|---|
| Critical | Deterministic gate and forecast-policy simulation treated as one validated system | `analysis/simulate_pooling.py` uses expected future capacity for its forecast policy. Its 5 vs 19 idle bay-hours result cannot automatically be transferred to a gate that admits only against current verified free capacity. New deck compares policies and makes the combined system a testable proposition. | Operating control; simulation results; evidence appendix | Replay and field-test the exact deployed admission policy. |
| Critical | Fully installed cost implied by RM92k | The existing budget does not separately price zone barriers/boundaries, controller integration, tax, support allocation or contingency. RM92k is an initial scope subtotal, not a final funding authorization. | Investment; procurement; decision | Site survey, operator scope and binding quotes. |
| High | Existing LPR infrastructure not considered | Official KL East page publishes LPR parking and QR payment. New deck prioritizes a reuse assessment; API access and compatibility are not established. | Context; architecture; sourcing | Read/write access, vendor protocol, physical boundary and contract rights. |
| High | Hardware prices not fully revalidated | The former AAC 2025 PDF returned 404. The current AAC product-search page displays multiple amounts for DS-TCG205-E, requiring supplier clarification. Viskou product exists but the old RM2,033 price was not recoverable in the readable page. | Sourcing appendix | Written itemized quotes including tax, warranty and installation. |
| High | Local demand illustrated with unrelated urban surveys | Broad city/overseas parking percentages do not establish KL East weekend search times or paid demand. New deck uses official infrastructure facts and a clearly named baseline workstream instead of projecting survey percentages onto KL East. | Problem and pilot design | Timestamped entry/search data, member cohort and paid conversion. |
| High | CV result treated as site generalization | Internal test held out cameras 6–9 at the same outdoor Italian site; 99.05% patch accuracy is not indoor Malaysia deployment accuracy. There were 540 occupied patches called free. | Technical evidence; appendix methods | Indoor glare/occlusion/night annotations and error reconciliation. |
| High | Retention sensitivity disconnected from capital model | Base contribution RM7,775.40 and upfront RM81,500 imply RM8,524.60 extra annual net benefit for five-year simple recovery. Required weekly visits are recalculated against that amount, replacing the unrelated RM9,360 target. | Capital recovery; retention | Effective landlord capture and genuinely incremental visits. |
| High | Partner contribution overestimated by switching cost bases | RM45k fee less 1.5 × RM10.5k zone OPEX = RM29,250 before central support/onboarding, versus RM38,250 when only a cloud allowance is deducted. New partner-pace illustration uses RM29,250. | Partner sensitivity appendix | Contracted fees, usage-based OPEX, churn, onboarding and support. |
| High | Portfolio count | FY2025 sources identify three wholly owned malls: KL East, Elmina Lakeside and KLGCC. Avoid automatically adding JV assets at 100% economics. | Horizons and rollout | Property-specific governance and site economics. |
| Medium | Correlation presented as incremental loyalty value | Vase.ai reports self-recalled baskets by visit frequency. It does not establish that parking causes more visits or higher spend. | Member value; retention | Matched/control-cohort uplift and lease-specific capture. |
| Medium | Missing executive decision structure | Add situation, key question, recommendation and approval boundary. | Executive summary | Sponsor agreement. |
| Medium | Reservation treated as absent from competitors | Sunway's official FAQ describes EV bay reservation via ParkEasy. New deck distinguishes specific service capabilities rather than claiming that booking is unique. | Market alternatives | A broader competitive product review if external commercialization proceeds. |
| Medium | No accountable operating model | Add mall sponsor, operator, digital/IT, finance and privacy responsibilities with sign-offs. | GTM and governance | Actual named owners and operator contract. |
| Medium | Pilot metrics lack denominator and test design | Define accepted arrivals, entry failures, held bay-hours while demand is refused, paid conversion and reconciled full cost. Use matched days/control comparisons; report uncertainty. | Scorecard; test plan | Baseline, agreed thresholds and sufficient observation volume. |
| Medium | No exception handling | Plate mismatch, network failure, stale counts, no-shows, overstays, refunds and emergency egress each need a specified response. | Operational risk slide | Operator-approved SOP and drills. |

## Live public source register

| ID | Source | Used for | Boundary |
|---|---|---|---|
| S1 | [SDP official KL East Mall](https://www.simedarbyproperty.com/malls/kleast-mall/) | Existing cashless/LPR parking; published parking tariffs | Does not confirm app API, reserved B1 boundary, spare camera coverage or integration permission. |
| S2 | [1 Utama ONECARD official FAQ](https://www.onecard.com.my/Home/FAQ) | Published member parking and LPR capability | Absence of a specific booking claim on this page does not prove no competing booking product exists. |
| S3 | [Sunway Pyramid official FAQ](https://www.sunwaypyramid.com/faq) | Published preferred parking alternative | No inference about all Sunway sites or unpublished roadmap. |
| S4 | [Vase.ai Malaysia Shopping Mall Report 2026](https://www.vase.ai/resources/insights-report/malaysia-shopping-mall-report-2026) | RM195 vs RM327 recalled basket by visit frequency; n=500 total survey | Correlational, self-recalled, not KL East-specific or a causal uplift estimate. |
| S5 | [SDP Q4 FY2025 quarterly report](https://www.simedarbyproperty.com/sites/default/files/2026-02/Quarterly%20Report%20Q4%20FY2025.pdf) | Three wholly owned malls; retail context | Expansion pace still a proposal. |
| S6 | [AAC current ANPR product search](https://store.aacgroup.com.my/?p=list_product&search=anpr) | Product availability and quote discovery | Multiple displayed price labels; not a confirmed installed quote. |
| S7 | [Viskou DS-TVL224 product](https://viskou.my/products/outdoorledguidancedisplayds-tvl224-4-5y2rows) | Compact LED product option | Former price could not be revalidated. |
| S8 | [Malaysia PDP Act and official guidelines index](https://www.pdp.gov.my/en/akta709/) | Privacy notice, controller/processor, retention and breach-response workstream | SDP legal/privacy must determine obligations for the actual deployment. |
| S9 | [CNR research institute dataset record](https://openportal.isti.cnr.it/doc?id=people______%3A%3A82a7de1e67ac2d1a64791ab662b78bfb) | Dataset geography, camera coverage and benchmark context | ParkFlow scores are internal experiments, not scores endorsed by the dataset authors. |
| S10 | [UCI Parking Birmingham](https://archive.ics.uci.edu/dataset/482/parking%2Bbirmingham) | Forecast dataset provenance | UK occupancy history does not establish KL East accuracy. |
| S11 | [WCAG contrast criterion](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html) | Programmatic colour-pair checks | A contrast check alone does not prove full accessibility. |

## Internal experiment and model provenance

- `analysis/backtest_ensemble_results.txt`: 48,112 forecasts across 30 car parks, six-week test; 60-minute ensemble MAE 2.07% vs last-week 5.34%.
- `analysis/cv_benchmark_results.txt`: 78,270 held-out-camera patches; 99.05% patch accuracy; indoor transfer remains untested.
- `analysis/simulate_pooling_results.txt` and `analysis/simulate_pooling.py`: comparative policy simulation; retain the exact denominators for held-back bay-hours.
- `presentation/booking_economics.py`: shared fee model. New deck recalculates from constants; it does not run this file's chart-writing entry point or alter original assets.
- `analysis/business_case_results.txt`: older hardware and four-SDP-mall scenarios are superseded for this separate deck. Do not combine their payback/NPV with the newer RM92k pilot model.

## Remaining evidence cannot be filled by desk research

Actual KL East search time, paid conversion, tenant rent capture, plate/camera drift, API integration effort, outage behavior, signed hardware installation cost, additional staffing, refunds, legal allocation and approval authority remain unknown. The new deck converts them into named baseline, quotation or pilot deliverables. It does not invent measured values to increase information density.
