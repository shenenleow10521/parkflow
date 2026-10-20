// Build: tsc -> bundle -> inline into the page fragment (dist/parkflow.html) and a local test page.
import { execSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';

const root = path.resolve(path.dirname(new URL(import.meta.url).pathname), '..');
process.chdir(root);
fs.rmSync('build', { recursive: true, force: true });
execSync('tsc -p .', { stdio: 'inherit' });
execSync('node tools/bundle.mjs dist/app.js', { stdio: 'inherit' });
execSync('node tools/bundle.mjs dist/driver.js --driver', { stdio: 'inherit' });
// guard: modules in one bundle share one scope, so their top-level names must be unique
const { adminOrder, driverOrder } = await import('./bundle.mjs');
for (const [name, list] of [['admin', adminOrder], ['driver', driverOrder]]) {
  const seen = new Map();
  for (const f of list) {
    for (const line of fs.readFileSync(path.join('build', f + '.js'), 'utf8').split('\n')) {
      const m = /^(?:export\s+)?(?:async\s+)?(?:function|const|let|class|var)\s+([A-Za-z_$][\w$]*)/.exec(line);
      if (!m) continue;
      if (seen.has(m[1]) && seen.get(m[1]) !== f) throw new Error(`${name} bundle: duplicate top-level name ${m[1]} in ${f} and ${seen.get(m[1])}`);
      seen.set(m[1], f);
    }
  }
}
const js = fs.readFileSync('dist/app.js', 'utf8');
if (js.includes('</script')) throw new Error('bundle contains a closing script tag');
const css = fs.readFileSync('src/styles.css', 'utf8');
const tpl = fs.readFileSync('src/template.html', 'utf8');
const page = tpl.replace('/*__CSS__*/', () => css).replace('/*__JS__*/', () => js);
fs.writeFileSync('dist/parkflow.html', page);
// Local test harness mimicking the artifact skeleton
const test = `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover"><style>:root{color-scheme:light;padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}body{margin:0;font:14px system-ui}img{max-width:100%}[hidden]{display:none!important}</style></head><body>${page}</body></html>`;
fs.writeFileSync('dist/test.html', test);
console.log('page', (fs.statSync('dist/parkflow.html').size / 1024).toFixed(1), 'KB');

// Driver app page
const djs = fs.readFileSync('dist/driver.js', 'utf8');
if (djs.includes('</script')) throw new Error('driver bundle contains a closing script tag');
const dcss = fs.readFileSync('src/mobile/styles.css', 'utf8');
const dtpl = fs.readFileSync('src/mobile/template.html', 'utf8');
const dpage = dtpl.replace('/*__CSS__*/', () => dcss).replace('/*__JS__*/', () => djs);
fs.writeFileSync('dist/parkflow-driver.html', dpage);
fs.writeFileSync('dist/test-driver.html', `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover"><style>:root{color-scheme:light;padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}body{margin:0;font:14px system-ui}img{max-width:100%}[hidden]{display:none!important}</style></head><body>${dpage}</body></html>`);
console.log('driver page', (fs.statSync('dist/parkflow-driver.html').size / 1024).toFixed(1), 'KB');

// Standalone site for GitHub Pages (or any static host): full HTML documents in docs/.
// index.html is the operator command centre, driver.html the driver app.
function standalone(fragment, title) {
  const cut = fragment.search(/^<div /m);
  const head = fragment.slice(0, cut);
  const body = fragment.slice(cut);
  return `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<style>:root{padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}body{margin:0}img{max-width:100%}[hidden]{display:none!important}</style>
${head}</head>
<body>
${body}</body>
</html>
`;
}
fs.mkdirSync('docs', { recursive: true });
fs.writeFileSync('docs/index.html', standalone(page, 'ParkFlow Command Centre'));
fs.writeFileSync('docs/driver.html', standalone(dpage, 'ParkFlow Driver'));
fs.writeFileSync('docs/.nojekyll', '');
console.log('site docs/index.html + docs/driver.html');
