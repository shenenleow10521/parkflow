"""Inspect, measure and export only the separate consulting edition."""
from concurrent.futures import ThreadPoolExecutor
import argparse
import hashlib
import io
import json
from pathlib import Path

import fitz
from PIL import Image
from playwright.sync_api import sync_playwright

from measure_deck_design import pixels, text_metrics, ocr_words, contact_sheet, summary

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'docs'/'deck-design-analysis'
PREVIEW=OUT/'renders'/'consulting'
PDF=ROOT/'submission'/'ParkFlow-Consulting-Deck.pdf'


def contrast(a,b):
    def luminance(h):
        rgb=[int(h[i:i+2],16)/255 for i in (1,3,5)]
        values=[v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4 for v in rgb]
        return sum(x*w for x,w in zip(values,[.2126,.7152,.0722]))
    x,y=sorted([luminance(a),luminance(b)])
    return round((y+.05)/(x+.05),2)


def ocr_enrich(row):
    with Image.open(ROOT/row['render']) as im:
        words=ocr_words(im)
    metrics=text_metrics(words)
    row.update({'visible_ocr_'+key:value for key,value in metrics.items()})
    row['text_box_union_pct']=metrics['text_box_union_pct']
    return row


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--layout-only',action='store_true')
    args=parser.parse_args()
    original=ROOT/'site-vnext'/'index.html'
    before=hashlib.sha256(original.read_bytes()).hexdigest()
    PREVIEW.mkdir(parents=True,exist_ok=True)
    errors=[]
    rows=[]
    with sync_playwright() as p:
        browser=p.chromium.launch()
        page=browser.new_page(viewport={'width':1600,'height':900},reduced_motion='reduce')
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.goto((ROOT/'site-consulting'/'index.html').as_uri())
        page.wait_for_function('window.__consultingReady===true')
        slides=page.locator('.slide')
        ids=slides.evaluate_all('ss=>ss.map(s=>s.id)')
        assert len(ids)==34 and ids[1]=='team'
        assert ids.index('thanks')+1==ids.index('a-cost')
        main_count=ids.index('thanks')+1
        for i,slide_id in enumerate(ids,1):
            slide=page.locator('#'+slide_id)
            slide.evaluate("s=>s.scrollIntoView({behavior:'instant',block:'start'})")
            page.wait_for_timeout(30)
            data=slide.evaluate('''s=>{
              const f=s.querySelector('.frame'),fr=f.getBoundingClientRect(),c=s.querySelector('.content'),cr=c.getBoundingClientRect();
              const h=s.querySelector('.slide-title');
              const text=s.innerText.trim();
              const overflow=[...c.querySelectorAll('p,li,h1,h2,h3,table,img,.decision-strip,.equation,.sources-list')].filter(e=>{
                const r=e.getBoundingClientRect();return r.width&&r.height&&(r.bottom>cr.bottom+2||r.right>cr.right+2||r.left<cr.left-2);
              }).map(e=>({tag:e.tagName,text:e.textContent.slice(0,70),bottom:Math.round(e.getBoundingClientRect().bottom-cr.bottom)}));
              const source=s.querySelector('.source');
              const sourceOverflow=source.scrollHeight>source.clientHeight+1;
              return {id:s.id,word_count:text.split(/\\s+/).length,section:s.dataset.section,overflow,sourceOverflow,tables:s.querySelectorAll('table').length,images:s.querySelectorAll('img').length,
                heading:h?{font:getComputedStyle(h).fontFamily,size_px:parseFloat(getComputedStyle(h).fontSize),x:Math.round(h.getBoundingClientRect().left-fr.left),y:Math.round(h.getBoundingClientRect().top-fr.top)}:null,
                content_height:cr.height,source_height:source.clientHeight,body_text:c.innerText};
            }''')
            im=Image.open(io.BytesIO(page.screenshot(type='png',style='.controls { visibility:hidden; }'))).convert('RGB')
            target=PREVIEW/f'{i:02d}-{slide_id}.png';im.save(target)
            rows.append({'document':'ParkFlow Consulting','page':i,**data,**pixels(im),'render':str(target.relative_to(ROOT)).replace('\\','/')})
        if args.layout_only:
            failures=[{'id':r['id'],'overflow':r['overflow'],'sourceOverflow':r['sourceOverflow']} for r in rows if r['overflow'] or r['sourceOverflow']]
            (OUT/'premium-layout.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
            print(json.dumps({'layout_findings':failures,'tables':sum(r['tables'] for r in rows),'main_table_slides':[r['id'] for r in rows[:main_count] if r['tables']],'image_slides':[r['id'] for r in rows if r['images']]},indent=2))
            browser.close()
            return
        # Prove the continuous transition with normal presentation navigation.
        page.goto((ROOT/'site-consulting'/'index.html').as_uri()+'#thanks')
        page.wait_for_function('window.__consultingReady===true')
        page.keyboard.press('ArrowRight')
        assert page.url.endswith('#a-cost')
        assert not errors,errors
        assert page.evaluate('Array.from(document.images).every(i=>i.complete&&i.naturalWidth>0)')
        for width,height in [(1280,720),(1366,768),(1920,1080)]:
            page.set_viewport_size({'width':width,'height':height});page.wait_for_timeout(50)
            box=page.locator('#a-cost .frame').bounding_box()
            assert box['width']<=width+1 and box['height']<=height+1,(width,height,box)
        page.set_viewport_size({'width':390,'height':844})
        page.locator('#reading').click()
        assert page.locator('body').get_attribute('class')=='read-mode'
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'), 'Reading mode horizontal page overflow'
        page.locator('#reading').click()
        page.set_viewport_size({'width':1600,'height':900})
        page.emulate_media(media='print')
        PDF.parent.mkdir(exist_ok=True)
        page.pdf(path=str(PDF),width='1600px',height='900px',print_background=True,prefer_css_page_size=True,tagged=True)
        browser.close()
    early_failures=[{'id':r['id'],'overflow':r['overflow'],'sourceOverflow':r['sourceOverflow']} for r in rows if r['overflow'] or r['sourceOverflow']]
    print('EARLY LAYOUT FINDINGS',json.dumps(early_failures,indent=2),flush=True)
    with ThreadPoolExecutor(max_workers=3) as pool:
        rows=list(pool.map(ocr_enrich,rows))
    contact_sheet(rows,OUT/'consulting-contact.jpg')
    colours=[('#102a43','#ffffff'),('#53647a','#ffffff'),('#245bd8','#ffffff'),('#ffffff','#102a43'),('#d2deee','#102a43'),('#53647a','#f2f5f9')]
    palette=[{'foreground':a,'background':b,'contrast':contrast(a,b)} for a,b in colours]
    assert all(pair['contrast']>=4.5 for pair in palette)
    with fitz.open(PDF) as doc:
        assert len(doc)==len(ids)
        assert 'thank you' in doc[ids.index('thanks')].get_text().lower()
        assert 'cost & scope' in doc[ids.index('a-cost')].get_text().lower()
        assert all(len(pg.get_text().strip())>40 for pg in doc)
        assert all(abs(pg.rect.width-1200)<1 and abs(pg.rect.height-675)<1 for pg in doc)
        doc.set_toc([[1,r['id'].replace('-',' ').title(),r['page']] for r in rows])
        doc.set_metadata({'title':'ParkFlow | Property and Product Edition','subject':f'{main_count} main slides, standalone Thank You, then {len(ids)-main_count} appendix slides'})
        doc.saveIncr()
    assert hashlib.sha256(original.read_bytes()).hexdigest()==before
    result={'slides':len(rows),'main':main_count,'appendix':len(rows)-main_count,'browser_errors':errors,'contrast_pairs':palette,
            'original_sha256':before,'original_unchanged':True,
            'all':summary(rows),'business_and_implementation':summary([r for r in rows if r['section'] in ['Business','Implementation']]),
            'product':summary([r for r in rows if r['section']=='Product']),'layout':rows,
            'main_table_slides':[r['id'] for r in rows[:main_count] if r['tables']],
            'image_slides':[r['id'] for r in rows if r['images']]}
    (OUT/'consulting-review.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    failures=[{'id':r['id'],'overflow':r['overflow'],'sourceOverflow':r['sourceOverflow']} for r in rows if r['overflow'] or r['sourceOverflow']]
    print(json.dumps({k:v for k,v in result.items() if k!='layout'},indent=2))
    print('LAYOUT FINDINGS',json.dumps(failures,indent=2))
    print('PDF',PDF)
    if failures:
        raise SystemExit(1)


if __name__=='__main__':
    main()
