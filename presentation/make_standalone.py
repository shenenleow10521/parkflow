"""Bundle a site-consulting deck into one self-contained HTML file (CSS, JS, images, font inlined).

Usage: python presentation/make_standalone.py site-consulting/index.html final/ParkFlow-Red-Consulting.html
"""
import base64
import mimetypes
import re
import sys
from pathlib import Path

src, dst = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
base = src.parent
h = src.read_text(encoding='utf-8')
mimetypes.add_type('image/webp', '.webp')
mimetypes.add_type('font/ttf', '.ttf')


def data_uri(rel):
    p = base / rel
    mime = mimetypes.guess_type(p.name)[0] or 'application/octet-stream'
    return f'data:{mime};base64,' + base64.b64encode(p.read_bytes()).decode()


def inline_css(css):
    return re.sub(r"url\(['\"]?(assets/[^'\")]+)['\"]?\)", lambda m: f"url('{data_uri(m.group(1))}')", css)


# Stylesheets and scripts
h = re.sub(r'<link[^>]*href="([^"]+\.css)"[^>]*/?>',
           lambda m: f'<style>{inline_css((base / m.group(1)).read_text(encoding="utf-8"))}</style>', h)
h = re.sub(r'<script[^>]*src="([^"]+\.js)"[^>]*>\s*</script>',
           lambda m: f'<script>{(base / m.group(1)).read_text(encoding="utf-8")}</script>', h)
# The font preload is redundant once the @font-face carries the data URI
h = re.sub(r'<link[^>]*rel="preload"[^>]*>', '', h)
h = inline_css(h)

# Images: encode each file once, then reuse the data URI for repeated <img> tags
cache = {}
h = re.sub(r'src="(assets/[^"]+)"', lambda m: 'src="%s"' % cache.setdefault(m.group(1), data_uri(m.group(1))), h)

# Relative links to repo files cannot resolve outside the repo; point them at the GitHub copies
REPO = 'https://github.com/shenenleow10521/parkflow/blob/main/'
h = re.sub(r'href="\.\./([^"]+)"', lambda m: f'href="{REPO}{m.group(1)}"', h)
h = re.sub(r'href="(financial-sources\.md)"', lambda m: f'href="{REPO}site-consulting/{m.group(1)}"', h)

left = re.findall(r'(?:src|href)="(?!data:|https?:|#|mailto:)([^"]+)"', h)
assert not left, f'unresolved local references: {sorted(set(left))}'
dst.parent.mkdir(parents=True, exist_ok=True)
dst.write_text(h, encoding='utf-8', newline='')
print(f'{dst.name}: {dst.stat().st_size / 1e6:.1f} MB')
