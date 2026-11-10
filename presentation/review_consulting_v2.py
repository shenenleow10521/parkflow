"""Validate the separate V2 HTML deck without producing or changing any PDF."""
import hashlib
import json
import math
import re
from decimal import Decimal
from pathlib import Path
from urllib.parse import unquote, urlsplit

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs/deck-design-analysis/renders/consulting-v2'


def main():
    protected = [ROOT / p for p in ['site-consulting/index.html', 'site-consulting/deck.css',
                 'site-consulting/premium.css', 'site-consulting/deck.js', 'site-vnext/index.html']]
    protected += list((ROOT / 'submission').glob('*.pdf'))
    before = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in protected}
    deck = ROOT / 'site-consulting/index-v2.html'
    html = BeautifulSoup(deck.read_text(encoding='utf-8'), 'html.parser')
    for element in html.select('[href],[src]'):
        link = urlsplit(element.get('href') or element.get('src'))
        if not link.scheme and not link.netloc and link.path:
            assert (deck.parent / unquote(link.path)).resolve().exists(), link.path
        if not link.path and link.fragment:
            assert html.find(id=unquote(link.fragment)), link.fragment
    # Independently reconcile cash, capital and scenario metrics, including the
    # two NEW zone cameras and tax on gateway fees (not on booking principal).
    import consulting_v2_finance as finance
    capital = Decimal(2)*Decimal(3226)+Decimal(2033)+Decimal(4000)+Decimal(7500)+Decimal(60000)
    annual_running = Decimal(10500)
    assert capital == 79985 and capital + annual_running == 90485
    assert finance.LPR_COUNT == 2 and finance.LPR == 6452
    cases = html.select('#recovery tbody tr')
    for case, peak, weekday in zip(cases, [20,30,40,50], ['5','7.5','10','12.5'], strict=True):
        gross = Decimal(104)*peak*5 + Decimal(261)*Decimal(weekday)*4
        contribution = gross*(1-Decimal('.20')-Decimal('.018')*Decimal('1.08'))-annual_running
        values = [e.get_text(strip=True) for e in case.select('td')]
        assert values[-3:] == [f'RM{contribution:,.0f}',f'{capital/contribution:.1f} years',f'{contribution/capital:.1%}'], values
        actual=finance.economics(peak,float(weekday))
        assert math.isclose(actual['contribution'],float(contribution),abs_tol=1e-8)
        assert math.isclose(actual['net']-float(annual_running),actual['contribution'],abs_tol=1e-8)
    cash=finance.economics()
    assert math.isclose(cash['processing'],455.4792,abs_tol=1e-8)
    assert math.isclose(cash['contribution'],7788.5208,abs_tol=1e-8)
    assert math.isclose(finance.recovery_gap(5),8208.4792,abs_tol=1e-8)
    # Independent cost/channel stress checks catch falsely attractive returns.
    assert math.isclose(finance.economics(extra_annual=12000)['contribution'],cash['contribution']-12000,abs_tol=1e-8)
    assert finance.economics(extra_annual=12000)['payback'] is None
    assert math.isclose(finance.economics(route='billplz_fpx')['processing'],6854.625,abs_tol=1e-8)
    assert finance.required_bookings(3) > finance.required_bookings(5) > finance.required_bookings()
    assert finance.required_bookings(5,extra_annual=12000) > finance.required_bookings(5)
    assert finance.required_bookings(5,upfront=finance.UPFRONT+10000) > finance.required_bookings(5)
    for selector in ['#executive .ex-kpi','#capex-opex .co-pill','#decision .decision-budget']:
        assert 'RM90' in html.select_one(selector).get_text(), selector
    financial_ids=['executive','investment','booking-return','decision','a-cost','a-finance','recovery']
    for name in financial_ids:
        slide=html.find(id=name)
        assert slide['data-financial-model']=='v2-2026-11-09'
        text=slide.get_text(' ',strip=True)
        assert not any(stale in text for stale in ['RM92k','RM81,500','RM8,524','RM19,391','2% processing','Processing 2%'])
    assert 'RM6,452' in html.find(id='a-cost').get_text()
    assert '30/60/90' in html.find(id='scorecard').get_text()
    assert '100%' in html.find(id='member-value').get_text()
    # No unsupported visit/capture conversion. Published comparable GROSS lease
    # rates support a separate main chart, without adding rental cash to returns.
    assert not html.find(id='a-retention')
    assert not hasattr(finance,'weekly_visits') and not hasattr(finance,'CAPTURE_ILLUSTRATION')
    assert finance.MARGINAL_VISIT_VALUE is None and finance.VISIT_LIFT_PER_MEMBER_MONTH is None
    all_text=html.get_text(' ',strip=True)
    assert not re.search(r'RM13(?![\d,.])|13\s+(?:extra|additional|visits)|\b[2358]%\s+(?:capture|net capture|effective capture)|extra visits / week',all_text,re.I)
    assert len(html.select('#member-value .v2-proof-ladder>article'))==3
    assert html.select_one('#member-value a[href="https://doi.org/10.1086/500480"]')
    assert html.select_one('#member-value a[href="https://doi.org/10.1016/j.jretai.2021.08.001"]')
    assert 'No retention cash is assumed' in html.find(id='member-value').get_text()
    assert not html.find(id='retention')
    assert finance.LEASE_RATE_LOW==.05 and finance.LEASE_RATE_HIGH==.15
    assert 'not a cost or demand average across SDP malls' in html.find(id='executive').get_text()
    # Independent lease cases: no top-up below floor; partial rent at crossing;
    # full marginal rate once above floor; reversal cannot undercut base rent.
    lease=finance.monthly_turnover_rent_change
    assert lease(base_and_service=10000,sales_before=90000,extra_sales=5000,rate=.10)==0
    assert lease(base_and_service=10000,sales_before=90000,extra_sales=20000,rate=.10)==1000
    assert lease(base_and_service=10000,sales_before=120000,extra_sales=5000,rate=.10)==500
    assert lease(base_and_service=10000,sales_before=120000,extra_sales=-30000,rate=.10)==-2000
    assert lease(base_and_service=0,sales_before=0,extra_sales=100000,rate=.05)==5000
    assert lease(base_and_service=0,sales_before=0,extra_sales=100000,rate=.15)==15000
    assert not html.select('.takeaway,.controls'), 'Topic-led V2 must not retain the old takeaway band or floating controls'
    assert html.select_one('#pilot-design svg') and html.select_one('#horizons svg')
    assert html.select_one('script[src="v2.js"]')
    OUT.mkdir(parents=True, exist_ok=True)
    errors, rows = [], []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={'width': 1600, 'height': 900}, reduced_motion='reduce')
        page.on('pageerror', lambda e: errors.append(str(e)))
        url = deck.as_uri()
        page.goto(url)
        page.wait_for_function('window.__consultingReady === true')
        ids = page.locator('section.slide').evaluate_all('ss => ss.map(s => s.id)')
        assert len(ids) == 34 and len(set(ids)) == 34 and ids[1] == 'team', ids
        assert ids.index('thanks')==22, '23 main slides including standalone Thank You'
        assert ids[10:13]==['ml-stack','forecast','simulation'], 'Architecture precedes prediction and operating results'
        assert ids[14:18]==['must-be-true','capex-opex','booking-return','investment'], 'Value, cost, income and break-even order'
        assert ids[19:22]==['roadmap','horizons','decision'], 'Six-month plan precedes three-horizon plan and decision'
        assert ids[ids.index('thanks')+1]=='risk' and html.find(id='risk')['data-appendix']=='true'
        assert 'member-value' in ids[:ids.index('thanks')], 'Retain the former slide 13'
        assert not set(ids)&{'context','booking-sensitivity','retention'}
        assert ids.index('recovery')>ids.index('thanks') and ids.index('scorecard')>ids.index('thanks')
        assert not set(ids)&{'commercial','sanity-checks','a-partners','a-historical-policy','a-evidence','a-audit'}
        dom_ids=page.locator('[id]').evaluate_all('es=>es.map(e=>e.id)')
        assert len(dom_ids)==len(set(dom_ids)), 'Duplicate inline SVG or section IDs'
        assert ids[ids.index('thanks') + 2] == 'a-cost'
        assert page.evaluate('Array.from(document.images).every(i => i.complete && i.naturalWidth > 0)')
        crossings=page.locator('#horizons .hz-chart svg').evaluate('''svg=>{
          const paths=[...svg.querySelectorAll('path')].filter(p=>p.getAttribute('stroke-width')==='4.5');
          const labels=[...svg.querySelectorAll('text')].filter(t=>{const r=t.getBBox();return r.y>130&&r.y+r.height<440;});
          return labels.filter(t=>{const r=t.getBBox();return paths.some(p=>{
            const n=p.getTotalLength();for(let i=0;i<=500;i++){const v=p.getPointAtLength(n*i/500);
              if(v.x>r.x-2&&v.x<r.x+r.width+2&&v.y>r.y-2&&v.y<r.y+r.height+2)return true;}return false;
          });}).map(t=>t.textContent);
        }''')
        assert not crossings, ('Horizon curves cross their labels',crossings)
        for i, slide_id in enumerate(ids, 1):
            slide = page.locator('#' + slide_id)
            slide.evaluate("s => s.scrollIntoView({behavior:'instant', block:'start'})")
            page.wait_for_timeout(40)
            data = slide.evaluate('''s => {
              const c = s.querySelector('.content'), cr = c.getBoundingClientRect();
              const overflow = [...c.querySelectorAll('p,li,h1,h2,h3,table,img,.decision-strip,.equation,.sources-list,article')].filter(e => {
                const r = e.getBoundingClientRect();
                return r.width && r.height && (r.bottom > cr.bottom + 2 || r.right > cr.right + 2 || r.left < cr.left - 2);
              }).map(e => ({tag:e.tagName, text:e.textContent.slice(0,90), bottom:Math.round(e.getBoundingClientRect().bottom-cr.bottom)}));
              const source = s.querySelector('.source');
              const title = s.querySelector('.slide-title');
              return {id:s.id, overflow, sourceOverflow:source.scrollHeight > source.clientHeight + 1,
                titleOverflow:title ? title.scrollHeight > title.clientHeight + 1 || title.getBoundingClientRect().bottom > cr.top - 8 : false,
                titleMetrics:title ? {scrollHeight:title.scrollHeight,clientHeight:title.clientHeight,bottom:Math.round(title.getBoundingClientRect().bottom),contentTop:Math.round(cr.top)} : null};
            }''')
            rows.append(data)
            if slide_id in ['cover','executive','ml-stack','admission','simulation','forecast','must-be-true','capex-opex','booking-return','investment','pilot-design','horizons','scorecard','a-decision-study']:
                page.screenshot(path=str(OUT / f'{i:02d}-{slide_id}.png'), style='.controls{visibility:hidden}')
        page.goto(url + '#thanks')
        page.wait_for_function('window.__consultingReady === true')
        page.keyboard.press('ArrowRight')
        assert page.url.endswith('#risk'), page.url
        for width, height in [(1280,720), (1366,768), (1920,1080)]:
            page.set_viewport_size({'width':width, 'height':height})
            page.wait_for_timeout(70)
            box = page.locator('#a-cost .frame').bounding_box()
            assert box['width'] <= width+1 and box['height'] <= height+1, box
        page.set_viewport_size({'width':390, 'height':844})
        page.keyboard.press('r')
        assert page.locator('body').evaluate("b => b.classList.contains('read-mode')")
        horizontal_overflow=page.locator('body *').evaluate_all('''els=>els.filter(e=>{
          const r=e.getBoundingClientRect();return r.width&&r.right>innerWidth+1;
        }).map(e=>({slide:e.closest('section')?.id||'',tag:e.tagName,id:e.id,cls:e.className?.baseVal||e.className||'',right:Math.round(e.getBoundingClientRect().right),width:Math.round(e.getBoundingClientRect().width)})).slice(0,20)''')
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), ('Reading mode horizontal overflow',horizontal_overflow)
        for slide_id in ['a-forecast-results','a-stress-results']:
            columns=page.locator('#'+slide_id+' .cols').evaluate("e => getComputedStyle(e).gridTemplateColumns.split(' ').length")
            assert columns==1, (slide_id, 'Phone reading mode must stack exhibit columns')
        page.goto(url)
        page.wait_for_function('window.__consultingReady === true')
        assert page.locator('body').evaluate("b => b.classList.contains('read-mode')"), 'Phone defaults to readable mode'
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        assert not errors, errors
        browser.close()
    assert all(hashlib.sha256(p.read_bytes()).hexdigest() == h for p, h in before.items())
    findings = [r for r in rows if r['overflow'] or r['sourceOverflow'] or r['titleOverflow']]
    result = {'slides':len(ids), 'main':ids.index('thanks')+1, 'appendix':len(ids)-ids.index('thanks')-1,
              'browser_errors':errors, 'local_references_valid':True, 'financial_cases_verified':True,
              'protected_files_unchanged':True, 'layout_findings':findings}
    (OUT / 'review.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result, indent=2))
    if findings:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
