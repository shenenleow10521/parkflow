"""Download verified public assets into the separate deck, with provenance."""
from pathlib import Path
import hashlib
import json
import requests

ROOT=Path(__file__).resolve().parents[1]
ASSETS=ROOT/'site-consulting'/'assets'
DOWNLOADS=[
    ('kl-east-exterior.jpg','https://imagedelivery.net/TdjZsXzzZt_je48pBzV3SA/f81bbb9c-4938-4cd0-65b7-32d6765a4800/1920','https://www.simedarbyproperty.com/malls/kleast-mall/','Official property exterior photograph; identify the proposed pilot location.'),
    ('sdp-logo.png','https://www.simedarbyproperty.com/home/images/sdp-logo-coloured.png?v2','https://www.simedarbyproperty.com/home/','Official current organisation mark; proposal recipient, not endorsement.'),
    ('1utama.png','https://www.onecard.com.my/Files/Logos/1Utama.png','https://www.onecard.com.my/','Official comparator identity.'),
    ('onecard.png','https://www.onecard.com.my/Files/Logos/ONECARD.png','https://www.onecard.com.my/','Official comparator identity.'),
    ('sunway-pyramid.png','https://www.sunwaypyramid.com/static/pyramid-logopngori-1730968244654.png','https://www.sunwaypyramid.com/','Official comparator identity.'),
    ('public-sans.ttf','https://raw.githubusercontent.com/google/fonts/main/ofl/publicsans/PublicSans%5Bwght%5D.ttf','https://github.com/uswds/public-sans','Self-hosted variable typeface; SIL Open Font License.'),
    ('public-sans-OFL.txt','https://raw.githubusercontent.com/google/fonts/main/ofl/publicsans/OFL.txt','https://github.com/google/fonts/tree/main/ofl/publicsans','Font licence.'),
]


def main():
    ASSETS.mkdir(parents=True,exist_ok=True)
    manifest=[]
    for name,url,page,purpose in DOWNLOADS:
        response=requests.get(url,timeout=45)
        response.raise_for_status()
        if name.endswith(('.png','.jpg')):
            assert response.headers.get('content-type','').startswith('image/'),(name,response.headers.get('content-type'))
        (ASSETS/name).write_bytes(response.content)
        manifest.append(dict(file=name,url=url,source_page=page,purpose=purpose,date='2026-11-07',sha256=hashlib.sha256(response.content).hexdigest(),bytes=len(response.content)))
        print(name,len(response.content))
    (ASSETS/'public-assets.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')


if __name__=='__main__':
    main()
