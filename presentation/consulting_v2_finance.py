"""V2-only single-zone reference model, not an SDP portfolio-average forecast.

Source observations and unresolved inputs: ../site-consulting/financial-sources.md.
Keep the original deck's booking_economics.py unchanged. No local demand, operator
contract, development quotation or landlord capture rate has been supplied.
"""

CHECKED = '2026-11-09'
SOURCES = {
    'site': ('KL East: existing LPR and payment', 'https://www.simedarbyproperty.com/malls/kleast-mall/'),
    'lpr': ('Viskou: DS-TCG406-E ANPR camera', 'https://viskou.my/products/4mpintelligententranceanprcamerads-tcg406-e'),
    'landlord': ('SDP FY2025 annual report', 'https://www.simedarbyproperty.com/sites/default/files/2026-04/SDP%20IAR2025%20%28Website%29.pdf'),
    'led': ('Viskou: DS-TVL224 display', 'https://viskou.my/products/outdoorledguidancedisplayds-tvl224-4-5y2rows'),
    'payments': ('Billplz public rates', 'https://main.billplz.com/pricing'),
    'fee_tax': ('Billplz fee tax and plan terms', 'https://support.billplz.com/guide/pricing'),
    'terms': ('Billplz merchant agreement', 'https://main.billplz.com/terms'),
    'fpx': ('ToyyibPay public rates', 'https://www.toyyibpay.com/pricing-plans/'),
    'spend': ('Vase.ai: national shopping survey', 'https://www.vase.ai/resources/insights-report/malaysia-shopping-mall-report-2026'),
    'spend_parking': ('1 Utama: spend-linked Express Parking', 'https://www.1utama.com.my/services/'),
    'progress': ('Nunes & Dreze: reward-progress experiment', 'https://doi.org/10.1086/500480'),
    'targeting': ('Gabel & Guhl: rewards and targeted coupons', 'https://doi.org/10.1016/j.jretai.2021.08.001'),
    'turnover': ('SDP: KL East turnover-rent contribution', 'https://www.simedarbyproperty.com/sites/default/files/2024-05/Reply%20Letter%20to%20MSWG%20%2817052024%29.pdf'),
    'lease_benchmark': ('Tropicana Gardens: disclosed lease rates', 'https://www.insage.com.my/BursaNews/Attachment/202412/20241203/TROP-AN20241203A3-1.pdf#page=32'),
    'lease_structure': ('Paradigm REIT: lease structures', 'https://ir2.chartnexus.com/paradigm/docs/Paradigm%20REIT%20-%20Prospectus.pdf#page=105'),
}

# Published: display-only, excluding tax; zero stock at listed branches on check.
LED = 2_033
# User-confirmed new zone: one NEW entry and one NEW exit LPR camera.
LPR_COUNT = 2
LPR_UNIT_PRICE = 3_226
LPR = LPR_COUNT * LPR_UNIT_PRICE
# Retained, unquoted inputs: no web page validates this project's installed cost.
CAMERA_ALLOWANCE = 4_000
CABLING_ALLOWANCE = 7_500
INTEGRATION_ALLOWANCE = 60_000
ANNUAL_RUNNING = 10_500
HARDWARE = LPR + LED + CAMERA_ALLOWANCE + CABLING_ALLOWANCE
UPFRONT = HARDWARE + INTEGRATION_ALLOWANCE
FIRST_YEAR = UPFRONT + ANNUAL_RUNNING
PREVIOUS_FIRST_YEAR = 92_000

# MYR-card Basic-plan reference, not a signed provider or assumed payment mix.
CARD_RATE = .018
FEE_TAX = .08
PROCESSING_SHARE = CARD_RATE * (1 + FEE_TAX)
# Unagreed commercial terms and price-test inputs, retained visibly as such.
OPERATOR_SHARE = .20
WEEKDAY_FEE, PEAK_FEE = 4, 5
PEAK_DAYS, WEEKDAY_DAYS = 104, 261  # fixed 365-day illustration, not a 2026 calendar
SCENARIOS = [('Lower volume', 20, 5), ('Reference', 30, 7.5),
             ('Higher volume', 40, 10), ('Growth target', 50, 12.5)]
# Published comparable GROSS lease terms, not a net capture rate or SDP average.
# Tropicana's 3 Dec 2024 circular, printed p.23, discloses around 5% for specified
# trades and 5–15% for other categories. Top-up applies above base + service charge.
LEASE_RATE_LOW, LEASE_RATE_HIGH = .05, .15
# No national-basket-to-landlord-capture conversion or causal visit uplift is used.
# The conditional sales/rent sensitivity is separate from booking-only returns.
MARGINAL_VISIT_VALUE = None
VISIT_LIFT_PER_MEMBER_MONTH = None


def economics(peak_per_day=30, weekday_per_day=7.5, *, upfront=UPFRONT,
              extra_annual=0, operator_share=OPERATOR_SHARE, route='card'):
    bookings = PEAK_DAYS * peak_per_day + WEEKDAY_DAYS * weekday_per_day
    gross = PEAK_DAYS * peak_per_day * PEAK_FEE + WEEKDAY_DAYS * weekday_per_day * WEEKDAY_FEE
    if route == 'card':
        processing = gross * PROCESSING_SHARE
    elif route == 'billplz_fpx':
        processing = bookings * 1.25 * (1 + FEE_TAX)
    else:
        raise ValueError(route)
    operator = gross * operator_share
    net = gross - operator - processing
    contribution = net - ANNUAL_RUNNING - extra_annual
    return dict(bookings=bookings, gross=gross, operator=operator,
                processing=processing, net=net, contribution=contribution,
                payback=upfront/contribution if contribution > 0 else None,
                cash_yield=contribution/upfront)


def recovery_gap(years=5, result=None, *, upfront=UPFRONT):
    return max(0, upfront / years - (result or economics())['contribution'])


def monthly_turnover_rent_change(*, base_and_service, sales_before, extra_sales, rate):
    """Higher-of lease: marginal gross rent, NOT net profit or total rent/sales.

    All amounts share one tenant/month. No annual pooling across tenants or months
    is valid because the fixed floor applies separately to each tenancy period.
    """
    from math import isfinite
    if not all(isfinite(v) for v in [base_and_service,sales_before,extra_sales,rate]):
        raise ValueError('Lease inputs must be finite')
    if base_and_service < 0 or sales_before < 0 or sales_before+extra_sales < 0 or not 0 <= rate <= 1:
        raise ValueError('Invalid sales, floor or rate')
    return max(base_and_service,rate*(sales_before+extra_sales))-max(base_and_service,rate*sales_before)


def required_bookings(years=None, *, upfront=UPFRONT, extra_annual=0,
                      operator_share=OPERATOR_SHARE, route='card'):
    """Algebraic threshold at the disclosed fee/day mix, never a demand forecast."""
    unit = economics(operator_share=operator_share, route=route)
    margin = unit['net'] / unit['bookings']
    target = ANNUAL_RUNNING + extra_annual + (upfront / years if years else 0)
    return target / margin
