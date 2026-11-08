"""Validate the separate V2 HTML deck without producing or changing any PDF."""
import hashlib
import json
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
    # Independently checked annual fee flows and five-year recovery scenarios.
    cases = html.select('#recovery tbody tr')
    for case, contribution, gap, visits in zip(cases, ['RM1,684','RM7,775','RM13,867'],
                                             ['RM14,616','RM8,525','RM2,433'], ['22','13','4'], strict=True):
        values = [e.get_text(strip=True) for e in case.select('td')]
        assert values[-3:] == [contribution, gap, visits], values
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
        assert len(ids) == 35 and len(set(ids)) == 35 and ids[1] == 'team', ids
        assert ids.index('thanks')==23, '24 main slides including standalone Thank You'
        assert ids[10:13]==['ml-stack','forecast','simulation'], 'Architecture precedes prediction and operating results'
        assert 'member-value' in ids[:ids.index('thanks')], 'Retain the former slide 13'
        assert ids.index('recovery')>ids.index('thanks') and ids.index('scorecard')>ids.index('thanks')
        assert not set(ids)&{'commercial','sanity-checks','a-partners','a-historical-policy','a-evidence','a-audit'}
        dom_ids=page.locator('[id]').evaluate_all('es=>es.map(e=>e.id)')
        assert len(dom_ids)==len(set(dom_ids)), 'Duplicate inline SVG or section IDs'
        assert ids[ids.index('thanks') + 1] == 'a-cost'
        assert page.evaluate('Array.from(document.images).every(i => i.complete && i.naturalWidth > 0)')
        crossings=page.locator('#horizons .content svg').evaluate('''svg=>{
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
                titleOverflow:title ? title.scrollHeight > title.clientHeight + 1 || title.getBoundingClientRect().bottom > cr.top - 8 : false};
            }''')
            rows.append(data)
            if slide_id in ['cover','executive','ml-stack','admission','simulation','forecast','must-be-true','investment','booking-sensitivity','retention','pilot-design','horizons','scorecard','a-decision-study']:
                page.screenshot(path=str(OUT / f'{i:02d}-{slide_id}.png'), style='.controls{visibility:hidden}')
        page.goto(url + '#thanks')
        page.wait_for_function('window.__consultingReady === true')
        page.keyboard.press('ArrowRight')
        assert page.url.endswith('#a-cost'), page.url
        for width, height in [(1280,720), (1366,768), (1920,1080)]:
            page.set_viewport_size({'width':width, 'height':height})
            page.wait_for_timeout(70)
            box = page.locator('#a-cost .frame').bounding_box()
            assert box['width'] <= width+1 and box['height'] <= height+1, box
        page.set_viewport_size({'width':390, 'height':844})
        page.keyboard.press('r')
        assert page.locator('body').evaluate("b => b.classList.contains('read-mode')")
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), 'Reading mode horizontal overflow'
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
