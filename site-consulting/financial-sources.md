# V2 financial evidence and commercial value

Checked 9 November 2026. Applies only to `index-v2.html`. The original deck and its model remain unchanged. The business case is a **single-zone reference for a proposed SDP member service**, with KLGCC Mall as the proposed candidate pilot. Published equipment/payment benchmarks and comparable mall leases are labelled separately; these are not cost, demand or capture averages across SDP's portfolio. This is not an installed quotation or a forecast of customer behaviour.

## New-zone scope

The zone requires **two additional LPR cameras**, one entry and one exit, as confirmed by the project owner. [KLGCC Mall's official page](https://www.simedarbyproperty.com/malls/klgcc-mall/) lists about 1,000 bays on LG and B1–B3 with Touch 'n Go card payment; it does not publish mall-wide LPR. Any incumbent LPR found in the site audit sets integration requirements, not a camera-purchase saving.

| Item | Source observation | Treatment in V2 |
| --- | --- | --- |
| Two new LPR cameras | [Viskou DS-TCG406-E](https://viskou.my/products/4mpintelligententranceanprcamerads-tcg406-e): RM3,226 each, excluding taxes. Zero stock shown at all listed branches. Relay/barrier control supported; regional plate support, interfaces and commissioning need confirmation. | 2 × RM3,226 = RM6,452, equipment-only price benchmark. Not an orderable installed quote. |
| Compact zone LED | [Viskou DS-TVL224-4-5Y, two rows](https://viskou.my/products/outdoorledguidancedisplayds-tvl224-4-5y2rows): RM2,033 excluding taxes; zero stock at listed branches. RJ45/RS485; small 304 × 152 mm display. | Replaces the RM4,000 equipment allowance with RM2,033 as a benchmark. Visibility, mounting, integration and availability remain procurement checks. |
| Cheaper display lead | [CarPark Counter LED Display](https://buildingmaterials.com.my/products/details/carpark-counter-led-display-5097): RM1,000 listing, shown in stock; purchase requires a seller quote. Exact specification/interface and installed scope are absent. | Not substituted into the financial model: equivalence has not been established. |
| Coverage cameras | No site camera count or installed quote. | Retain RM4,000 allowance; not a sourced cost. Separate LPR from bay-occupancy coverage. |
| Power, network and installation | No surveyed cable distances, PoE/UPS specification or installation quote. | Retain RM7,500 works allowance; require an itemised package and avoid double counting a switch/UPS already included in that package. |
| Production integration | No signed implementation quotation. | Retain RM60,000 allowance for identity, booking, payment, controller integration, commissioning and acceptance. A public developer salary or cheap generic app package cannot validate this scope. |
| Annual running | No actual usage/SLA or support quote. | Retain RM10,500 allowance rather than disguise free-tier cloud pricing as the full operating cost. Reconcile hosting, messaging, upkeep and central support before investment approval. |
| Other zone equipment | Gate motors/arms, safe boundary, loops/radar, intercom, edge controller, licenses, recorder/storage and backups need design decisions. | **Unpriced additions**, not zero-cost items. Confirm whether included in installation/integration packages. |

Priced hardware and works: RM6,452 + RM2,033 + RM4,000 + RM7,500 = **RM19,985**. Integration brings the upfront subtotal to **RM79,985**. Adding Year 1 running gives **RM90,485 + unpriced scope**. The former same-boundary RM92,000 subtotal falls by RM1,515 (1.65%); that is not an all-in saving or a claim that new-zone deployment is cheap. Extra zone equipment, project taxes, support and contingency can outweigh it. No tax percentage is applied to equipment without a supplier tax invoice.

## Small-ticket payment economics

[Billplz public pricing](https://main.billplz.com/pricing) lists Basic-plan MYR card payments at 1.8%, wallets at 1.5%, and consumer FPX at RM1.25/payment. Basic has no annual membership charge. [Billplz's pricing guide](https://support.billplz.com/guide/pricing) applies 8% SST to gateway fees, rather than to the payment principal. Merchant approval, supported channels, refunds, disbursements, chargebacks and any activation fees must be confirmed against the [merchant agreement](https://main.billplz.com/terms).

The V2 reference calculation uses **the MYR-card route at 1.8% × 1.08 = 1.944% of gross booking fees**. This is a comparable public route, not a claim that all users will pay by card or that the mall has contracted Billplz. Transaction-level fee rounding is not specified; the model aggregates the published rate and must be reconciled with actual settlement. The old 2% processing allowance is removed from final V2 financial slides.

At RM5, a Basic MYR-card payment costs RM0.0972 before transaction rounding, versus RM1.35 for Basic consumer FPX including fee SST. At the reference 5,077.5 payments/year, that same-provider comparison is RM455.48/year versus RM6,854.63/year. This is a payment-channel choice, not a saving against an existing signed payment contract. Do not select the 1.5% wallet rate while claiming to support an unrestricted mix at that price.

[ToyyibPay's own rate card](https://www.toyyibpay.com/pricing-plans/) also offers consumer FPX at RM1 and local cards at 1.5%, with RM100 card onboarding and RM100/year from the subsequent year. It is a procurement alternative, not the selected model. Its ambiguous QR description and unconfirmed minimums/tax/acceptance requirements are not converted into a lower headline cost. A paid gateway plan only helps when transaction savings exceed subscription and applicable tax.

## What is still an input rather than a sourced fact

- RM4 weekday / RM5 peak are **price-test inputs**, additional to ordinary parking. [KL East's official page](https://www.simedarbyproperty.com/malls/kleast-mall/) currently lists RM2 for the first two hours and RM2 for each subsequent hour, excluding 8% service tax. Its valet starts at RM18 Monday–Thursday and RM23 Friday–Sunday/public holidays for four hours. Valet is a different service, so these prices establish a local comparison, not willingness to pay for ParkFlow. For the KLGCC pilot, [KLGCC Mall's official page](https://www.simedarbyproperty.com/malls/klgcc-mall/) lists RM3 flat on weekdays and, on weekends, RM3 for the first three hours then RM2 per hour capped at RM10, excluding 6% SST, with charges taking effect from 1 September 2026. Booking-service output tax must be confirmed; it is not silently included or assumed exempt.
- The proposed operator allocation remains 20% of gross booking fees; no agreed contract was supplied. This is not a published industry commission.
- 104 peak and 261 weekday days are a fixed 365-day illustration. They are not the 2026 calendar and do not price public holidays separately.
- Reference volume is 30 peak / 7.5 weekday paid bookings per day. Lower, higher and growth scenarios are comparisons, not demand estimates from an external mall.
- At that reference volume, gross fees are RM23,430; proposed operator allocation RM4,686; processing RM455.4792; running RM10,500; annual contribution **RM7,788.5208 before excluded costs**. Capital recovery uses RM79,985 rather than the Year 1 subtotal, avoiding double-counting annual running.
- Unpriced support, refunds, incentives, displaced parking revenue and project taxes reduce the economic result. Ordinary parking receipts already earned from existing visitors are not counted as new ParkFlow income.

## Derive the hurdle instead of inventing demand

At the disclosed fee/day mix, net cash before fixed running is **RM3.601875 per paid booking** after the proposed operator allocation and public MYR-card fee. Required paid bookings = (annual running + extra annual costs + upfront capital / recovery years) / net per booking.

On priced lines only, annual operating break-even is about 2,916 bookings (8.0/day); five-year simple recovery needs 7,357 bookings/year (20.2/day); three years needs 10,318/year (28.3/day). Daily numbers are annual averages at the fixed fee mix, not a requirement to book the same number on weekdays and peaks. No occupancy-capacity constraint or local conversion has been validated by this calculation. Discounted returns would require a higher cash hurdle.

The 50 peak / 12.5 weekday growth scenario yields RM19,980.87 annual contribution, approximately 4.0-year simple payback and 25.0% annual operating cash yield on priced upfront capital. **Cash yield is not net ROI or IRR**, and the scenario is not an observed forecast. Complete quotes and measured paid uptake must support any investment recommendation.

## Retention, benchmarks and the wider business case

1. **Relevant customer segment.** [Vase.ai's 2026 national survey](https://www.vase.ai/resources/insights-report/malaysia-shopping-mall-report-2026) reports RM195 recalled spend among 1–2-visits/month shoppers versus RM327 among 5+-visits/month shoppers: a derived 67.7% difference. The approximate overall mean is RM260, reported directly, not calculated as a midpoint. The survey has 500 adults; recalled-trip spending is reported among 451 visitors. Frequency and spending are associated; this does not establish that parking improvements cause either to increase. Do not multiply both frequency and basket uplift into the base return.
2. **Real loyalty-parking precedent.** [1 Utama's official ONECARD FAQ](https://www.onecard.com.my/Home/FAQ) documents member-only preferred-parking zones, member rates, plate registration and wallet settlement. This shows the category exists. Membership prices or loyalty rewards are not measured ParkFlow willingness to pay, and the source supplies no causal retention percentage to import.
3. **Fit with the property owner's income model.** [SDP's FY2025 annual report](https://www.simedarbyproperty.com/sites/default/files/2026-04/SDP%20IAR2025%20%28Website%29.pdf), printed p. 28, reports 100% committed occupancy at KL East and Elmina Lakeside at end-2025. Printed pp. 151/154 discuss positive KL East rental reversions. This supports a tenant-trading and recurring-income argument. It does not justify assigning a rent uplift to ParkFlow or estimating landlord capture from portfolio revenue/PBT. Committed occupancy is not physical occupancy or carpark utilisation.
4. **SDP revenue mechanism and remaining boundary.** [SDP's 17 May 2024 written reply to MSWG](https://www.simedarbyproperty.com/sites/default/files/2024-05/Reply%20Letter%20to%20MSWG%20%2817052024%29.pdf), Q4(a), p. 4, attributes KL East's FY2023 outperformance partly to higher gross turnover rent and marketing revenue alongside cost savings. Its [2024 AGM minutes](https://www.simedarbyproperty.com/sites/default/files/2024-07/Minutes-of-the-51st-AGM.pdf), section 3.6.1(ii), p. 14, also connect visitor growth and turnover rent. They do not disclose a marginal lease rate or ParkFlow-caused retention effect. NPI yield is not a share of shopper spend. No net mall-capture rate or visit-to-cash conversion is used. The five-year booking-only annual cash gap remains RM8,208.48; it is not converted into a visit count.
5. **Measure retention itself.** Compare 30/60/90-day member return rates and visits/member against an eligible control and pre-pilot baseline. A booking or an already-planned repeat trip is not an incremental visit. Separate retained members from increased visit frequency; do not count the same trip twice. Longer follow-up may extend beyond the eight-week implementation pilot.
6. **Operational value.** Observe incident handling, staff minutes, queues and bay utilisation before/after with a suitable comparison. Count only a realised expense reduction or evidenced avoided future expense as cash; freed staff time is a service benefit until actually redeployed or costed. Deduct any displaced walk-in revenue and extra incident costs.
7. **ML value.** The existing offline studies compare operating policies on synthetic demand and occupancy forecasts on UK data. The event-driven learned controller does not clearly outperform the adaptive forecast baseline on the declared preference score. That score is not RM. Do not monetize its weights or add a separate “AI uplift” to booking and retention cash. The live test must compare the same controller with ML and the strongest practical simple forecast.

The financial identity is booking contribution + attributable marginal mall cash + realised operating savings − additional central/support/incentive/displacement cost. Tenant sales, member convenience, service quality and future rental resilience are valuable accompanying measures; only evidenced cash effects enter payback. Generic retention/profit multipliers do not establish KL East's lease-linked economics and are not used.

## Sourced growth strategies, without an assumed uplift

The main retention slide now explains three proposed mechanisms. They are future offer tests, not existing ParkFlow features or agreed supplier/tenant programmes.

- **Spend-linked parking credit.** [1 Utama's official service rates](https://www.1utama.com.my/services/) list first-hour-free ONECARD Express Parking for qualifying RM30 Jaya Grocer spend, with registration/payment conditions and subsequent-hour charges. This is a local operational precedent, not proof of extra visits. A ParkFlow tenant-backed credit requires an actual funding agreement, offer rules and measured incremental demand.
- **Repeat-visit milestones.** [Nunes and Dreze, Journal of Consumer Research (2006)](https://doi.org/10.1086/500480), [author-hosted paper](https://msbfile03.usc.edu/digitalmeasures/jnunes/intellcont/Endowed%20Progress%20Effect-1.pdf), report a reward-progress experiment in which an explained head start increased completion and shortened completion time. The original task required eight purchases in either condition. That finding supports testing milestone design, not importing the experiment's completion rate as KL East visit uplift.
- **Targeted return offers.** [Gabel and Guhl, Journal of Retailing (2022)](https://doi.org/10.1016/j.jretai.2021.08.001) model rewards, targeted coupons, trip incidence and expenditure using a German grocery programme. Its retailer-specific results support a strategy test; they are not a randomised ParkFlow treatment effect. A return offer should be evaluated against eligible members not offered it, including non-adopters in the offered group.

Record campaign cost, any contracted tenant funding, waived fee contribution, support and displaced income. Do not count a funded credit twice as both a subsidy saving and new revenue. The proposed mechanisms remain beside the shopper benchmark; no external uplift percentage is imported.

## Restored contour: comparable gross turnover-rent terms

The broader source search found a numerical Malaysian comparator. **Tropicana Corporation's 3 December 2024 disposal circular**, [Appendix II(A), printed p. 23 (PDF page 32)](https://www.insage.com.my/BursaNews/Attachment/202412/20241203/TROP-AN20241203A3-1.pdf#page=32), contains CBRE WTW's valuation certificate. It reports around 5% for specified trades and 5–15% for other categories, with a top-up when percentage rent exceeds base rent plus service charge. These are historical gross lease clauses, not an SDP average or net profit margin.

[Paradigm REIT's 2025 prospectus, PDF page 105](https://ir2.chartnexus.com/paradigm/docs/Paradigm%20REIT%20-%20Prospectus.pdf#page=105) separately describes higher-of and percentage-only tenancy structures for its malls. This corroborates the need to model the actual clause and floor; it is not used as another numeric rate observation. The prospectus also discusses tenant sales thresholds and monthly reporting. Neither document supplies a verified net capture rate across SDP malls.

The main chart keeps the earlier contour presentation but changes its meaning:

- X: gross turnover-rent clause from the disclosed comparable range. Intermediate points are scenario interpolation, not observed portfolio averages.
- Y: additional eligible tenant sales, RM50,000–RM250,000/year, a sensitivity axis rather than a demand forecast. These sales must already generate additional turnover rent after each tenant/month's fixed floor. They are not all shopper spending or the national per-visit basket.
- Contours: additional **gross rent**, calculated as eligible incremental sales × clause rate. RM100,000 of eligible sales yields RM5,000 at 5% or RM15,000 at 15%, before campaign/support/operating costs.
- Dashed line: the RM8,208.48 booking-only five-year cash gap on the current reference scope. It is a comparison before further incremental costs, not proof of total project recovery.

For a higher-of lease, calculate the change tenant by tenant and month by month:

`extra gross rent = max(base + service charge, rate × (existing sales + extra sales)) − max(base + service charge, rate × existing sales)`

Extra sales can produce **zero** additional rent below the floor. A period crossing the floor yields only a partial top-up. A percentage-only clause or an already-active percentage rent yields the full marginal rate. Do not apply a floor once to annual pooled sales from different tenants or months. Campaigns, fees waived, support, displacement and collection risk still need deductions before claiming net cash.

The previous 13-visits claim and basket/capture appendix remain removed. Booking-only returns are unchanged; no conditional rental uplift is added to those returns. The chart can be used across proposed malls as a sourced **comparable lease sensitivity**, with each site's agreements and eligible sales required before an investment forecast.

## Reproduction and boundaries

[`consulting_v2_finance.py`](../presentation/consulting_v2_finance.py) is the V2 financial authority. [`consulting_v2_financial_slides.py`](../presentation/consulting_v2_financial_slides.py) applies it to every V2 financial exhibit after the older content pass. Build and review:

```powershell
python -B presentation/build_consulting_v2.py
python -B presentation/review_consulting_v2.py
```

No field retention estimate, installed supplier quotation, willingness-to-pay result or landlord-approved capture was found in these public sources. The model exposes those gaps instead of filling them with selected favourable percentages.
