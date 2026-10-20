// Minimal bundler: concatenates tsc's ES module output in dependency order into one IIFE.
// Usage: node tools/bundle.mjs <out.js> [--core | --driver] [--test <extra.js>]
import fs from 'node:fs';
import path from 'node:path';

const root = path.resolve(path.dirname(new URL(import.meta.url).pathname), '..');
const order = [
  'core/rng', 'core/layout', 'core/scenarios', 'core/allocation', 'core/forecast', 'core/sim', 'core/metrics',
  'ui/dom', 'ui/store', 'render/scene3d', 'render/gl3d', 'ui/charts', 'ui/panels', 'ui/pages', 'ui/presentation', 'main'
];
// Driver app: the same simulation core plus its own UI modules.
export const driverOrder = ['core/rng', 'core/layout', 'core/scenarios', 'core/allocation', 'core/forecast', 'core/sim', 'ui/dom', 'mobile/motion', 'mobile/map', 'mobile/app'];
export const adminOrder = order;
const isMain = process.argv[1] && path.resolve(process.argv[1]) === path.resolve(new URL(import.meta.url).pathname);
const args = isMain ? process.argv.slice(2) : [];
const out = args[0];
const coreOnly = args.includes('--core');
const driver = args.includes('--driver');
const testIdx = args.indexOf('--test');
const files = coreOnly ? order.filter((f) => f.startsWith('core/')) : driver ? driverOrder : order;
if (!isMain) { /* imported for its order lists */ }
let code = '';
for (const f of isMain ? files : []) {
  const p = path.join(root, 'build', f + '.js');
  if (!fs.existsSync(p)) { console.error('missing', p); process.exit(1); }
  let src = fs.readFileSync(p, 'utf8');
  src = src.replace(/^import[\s\S]*?from\s+['"][^'"]+['"];?\s*$/gm, '');
  src = src.replace(/^import\s+['"][^'"]+['"];?\s*$/gm, '');
  src = src.replace(/^export\s+\{\s*\};?\s*$/gm, '');
  src = src.replace(/^export\s+(default\s+)?/gm, '');
  code += `// ---- ${f} ----\n${src}\n`;
}
if (isMain) {
  if (testIdx >= 0) code += fs.readFileSync(args[testIdx + 1], 'utf8');
  fs.writeFileSync(out, `(function(){\n'use strict';\n${code}\n})();\n`);
  console.log('bundled', files.length, 'files ->', out, fs.statSync(out).size, 'bytes');
}
