const assert = require('node:assert/strict');
const fs = require('node:fs');
const { gunzipSync } = require('node:zlib');
const { curves } = require('../scripts/csi2000_g2_comparison.js');

const page = fs.readFileSync('content/daily/2026-11-16.show.html', 'utf8');
const packed = JSON.parse(gunzipSync(Buffer.from(page.match(/id="g2-data"[^>]*>([^<]+)/)[1], 'base64')));
const original = JSON.parse(gunzipSync(Buffer.from(page.match(/id="csi2000-market-data"[^>]*>([^<]+)/)[1], 'base64')));
assert.equal(packed.dates.length, 308);
assert.equal(original.dates.length, 566);
assert.deepEqual(packed.dates, original.dates.slice(0, 308));
const ids = [...page.matchAll(/\bid="([^"]+)"/g)].map(x => x[1]);
assert.equal(new Set(ids).size, ids.length);
let checked = 0;
for (const key of Object.keys(packed.series.baseline)) {
  packed.series.baseline[key].forEach((row, i) => row.forEach((v, market) => {
    assert.ok(Math.abs(v - original.series[key][i][market]) < 1.1e-12);
  }));
  for (const market of ['sh', 'sz', 'all']) for (const view of ['wealth', 'enhancement']) {
    const values = curves(packed, key, market, view);
    assert.equal(values.delta.length, 308);
    values.G2.forEach((value, i) => {
      assert.ok(Number.isFinite(value));
      assert.ok(Math.abs(value - values.baseline[i] - values.delta[i]) < 1e-10);
    });
    checked++;
  }
}
const example = { initial: {equal: [.4, .6]}, base: {equal: [[.4, .6]]},
  series: {baseline: {'equal-test': [[.1, .2]]}, G2: {'equal-test': [[.2, .4]]}} };
assert.ok(Math.abs(curves(example, 'equal-test', 'all', 'enhancement').baseline[0] - 30) < 1e-10);
assert.ok(Math.abs(curves(example, 'equal-test', 'sz', 'enhancement').baseline[0] - 100/3) < 1e-10);
assert.equal((page.match(/G2-COMPARISON-BEGIN/g) || []).length, 1);
console.log(JSON.stringify({views: checked, baselinePrefixDays: 308, baselineFullDays: 566, uniqueIds: ids.length}));

// Run the actual initialization and filter handlers against the exported page data.
const vm = require('node:vm');
class Element {
  constructor() { this.handlers = {}; this.attributes = {}; this.style = {}; this.nodes = []; this.textContent = ''; this.parentElement = {clientWidth: 1000}; }
  setAttribute(key, value) { this.attributes[key] = value; }
  addEventListener(type, callback) { this.handlers[type] = callback; }
  replaceChildren() { this.nodes = []; }
  append(node) { this.nodes.push(node); }
  getBoundingClientRect() { return {left: 0, width: 1000}; }
}
const elements = new Map();
const get = id => { if (!elements.has(id)) elements.set(id, new Element()); return elements.get(id); };
get('g2-data').textContent = page.match(/id="g2-data"[^>]*>([^<]+)/)[1];
get('filters').elements = Object.fromEntries(Object.entries({weight: 'equal', sorting: 'combined', strategy: 'A', q: '5', tradeFraction: '10'}).map(([k,value]) => [k,{value}]));
get('g2-filters').elements = Object.fromEntries(Object.entries({market: 'sz', horizon: 'close', view: 'enhancement'}).map(([k,value]) => [k,{value}]));
const context = {document: {getElementById: get, createElementNS: () => new Element()},
  Blob, Response, DecompressionStream, atob, ResizeObserver: class {observe() {}}, console};
(async () => {
  const source = fs.readFileSync('scripts/csi2000_g2_comparison.js', 'utf8').replace('  start();', '  return start();');
  await vm.runInNewContext(source, context);
  assert.equal(get('g2-readout').attributes.role, undefined, get('g2-readout').textContent);
  assert.ok(get('g2-readout').textContent.includes('0.1805%'));
  assert.equal(get('g2-main').nodes.filter(n => n.attributes.d).length, 2);
  get('filters').elements.tradeFraction.value = '30';
  get('filters').handlers.change();
  const expected = curves(packed, 'equal-combined-close-A-5-t30', 'sz', 'enhancement');
  assert.ok(get('g2-readout').textContent.includes(expected.G2.at(-1).toFixed(4)));
  get('g2-filters').elements.view.value = 'wealth';
  get('g2-filters').elements.market.value = 'all';
  get('g2-filters').handlers.change();
  assert.equal(get('g2-main').nodes.filter(n => n.attributes.d).length, 3);
  get('g2-date').value = '0'; get('g2-date').handlers.input();
  assert.ok(get('g2-readout').textContent.startsWith('2024-07-01'));
  assert.equal(get('g2-base-legend').hidden, false);
  console.log(JSON.stringify({g2Initialization: 'passed', controls: ['shared-fraction','market','view','date']}));
})().catch(error => { console.error(error); process.exitCode = 1; });
