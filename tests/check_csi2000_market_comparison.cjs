const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const {gunzipSync} = require('node:zlib');

const source = fs.readFileSync(process.argv[2], 'utf8');
const encoded = source.match(/id="csi2000-market-data">([^<]+)<\/script>/)[1];
const data = JSON.parse(gunzipSync(Buffer.from(encoded, 'base64')));
const code = source.match(/<script>\s*([\s\S]*?)\s*<\/script>/)[1];

class Element {
  constructor(dataset = {}) {
    this.dataset = dataset;
    this.handlers = {};
    this.attributes = {};
    this.style = {};
    this.hidden = false;
    this.clientWidth = 1200;
    this.offsetWidth = 450;
    this.offsetHeight = 160;
    this.textContent = '';
    this.innerHTML = '';
    this.classList = {toggle() {}, add() {}, remove() {}};
    this.children = new Map();
  }
  addEventListener(type, callback) { this.handlers[type] = callback; }
  setAttribute(key, value) { this.attributes[key] = value; }
  querySelector(selector) {
    if (!this.children.has(selector)) this.children.set(selector, new Element());
    return this.children.get(selector);
  }
  focus() {}
  scrollIntoView() {}
  getBoundingClientRect() { return {left: 0, top: 0, width: 1200, height: 670}; }
  setPointerCapture() {}
  hasPointerCapture() { return false; }
}

const elements = new Map();
const get = id => {
  if (!elements.has(id)) elements.set(id, new Element());
  return elements.get(id);
};
get('csi2000-market-data').textContent = encoded;
get('signal-mode').value = 'rankic';
const controls = {weight: 'index', sorting: 'combined', strategy: 'L', q: '5', phase: 'all'};
get('filters').elements = {phase: {set value(value) { controls.phase = value; }}};
const metrics = ['mean', 'cumulative', 'sharpe', 'sharpeThrough', 'drawdown',
  'calmar', 'volatility', 'winRate', 'payoff', 't'];
const bodies = ['development', 'seen', 'unseen'].map(phase => ({
  dataset: {stageBlock: phase},
  rows: [0, 1, 2, 3].map(lane => new Element({lane: String(lane)}))
}));
get('score-rows').tBodies = bodies;
const legends = ['returns', 'signal'].flatMap(kind => ['all', '0', '1', '2', '3'].map(
  lane => new Element({curveKind: kind, curveLane: lane})
));
const options = ['wealth', 'enhancement'].map(returnView => new Element({returnView}));
const expanders = ['returns', 'signal'].map(enlarge => new Element({enlarge}));
const document = {
  getElementById: get,
  querySelectorAll(selector) {
    return {'[data-enlarge]': expanders, '[data-return-view]': options, '[data-curve-lane]': legends}[selector] || [];
  },
  addEventListener() {},
  body: {classList: {add() {}, remove() {}}}
};
const context = {
  document, window: {innerHeight: 1000, addEventListener() {}}, Blob, Response, DecompressionStream,
  atob, FormData: class {get(key) { return controls[key]; }},
  ResizeObserver: class {observe() {}}, console
};

function numeric(cell) {
  return Number(cell.textContent.replace('−', '-'));
}

function close(actual, expected, tolerance = .00501) {
  assert.ok(Math.abs(actual - expected) < tolerance, actual + ' versus ' + expected);
}

async function main() {
  await vm.runInNewContext(code, context);
  assert.notEqual(get('fill-status').hidden, false, 'Data failed to load');
}

(async () => {
  // The HTML keeps the error status hidden until loading actually fails.
  get('fill-status').hidden = true;
  await main();
  let checks = 0;
  for (const weight of ['index', 'equal']) {
    for (const sorting of ['combined', 'separate']) {
      for (const strategy of ['L', 'A']) {
        for (const q of ['1', '5', '10', '20']) {
          Object.assign(controls, {weight, sorting, strategy, q});
          for (const view of ['wealth', 'enhancement']) {
            options.find(button => button.dataset.returnView === view).handlers.click();
            const html = get('return-chart').innerHTML;
            assert.equal((html.match(/class="series-line /g) || []).length, 4);
            assert.equal((html.match(/class="pool-line /g) || []).length, view === 'wealth' ? 4 : 0);
            const key = [weight, sorting, 'morning', strategy, q].join('-');
            const start = 484;
            const lane = 0;
            const group = 0;
            const base = data.base[weight];
            const rows = data.series[key];
            const returns = [];
            for (let i = start; i < 566; i += 1) {
              const priorA = rows[i - 1][group];
              const priorB = base[i - 1][group];
              const a = rows[i][group];
              const b = base[i][group];
              returns.push(view === 'wealth' ? (b + a) / (priorB + priorA) - 1 : (a - priorA) / priorB);
            }
            const expectedMean = returns.reduce((s, value) => s + value, 0) / 82 * 10000;
            const row = bodies[2].rows[lane];
            if (data.trading) {
              const trading = data.trading[key].slice(start).map(day => day[group]);
              const weighted = trading.filter(amounts => amounts[0] > 0).map(
                amounts => (amounts[1] - amounts[2]) / amounts[0]);
              close(numeric(row.querySelector('[data-metric="tradeMean"]')),
                weighted.reduce((sum, value) => sum + value, 0) / weighted.length * 10000);
              assert.match(get('table-status').textContent, /扣税费后/);
            }
            close(numeric(row.querySelector('[data-metric="mean"]')), expectedMean);
            const wins = returns.filter(value => value > 0).length / returns.length * 100;
            close(numeric(row.querySelector('[data-metric="winRate"]')), wins);
            const mean = expectedMean / 10000;
            const sd = Math.sqrt(returns.reduce((sum, value) => sum + (value - mean) ** 2, 0) / (returns.length - 1));
            close(numeric(row.querySelector('[data-metric="sharpe"]')), mean / sd * Math.sqrt(252));
            assert.match(get('table-status').textContent, view === 'wealth' ? /绝对收益/ : /超额收益/);
            assert.match(get('score-note').textContent, view === 'wealth' ? /整体日收益/ : /做 T 增量/);
            const lastA = rows[565][group], lastB = base[565][group];
            const initial = data.initial[weight][group];
            const expectedCumulative = view === 'wealth'
              ? ((lastB + lastA) / (base[start - 1][group] + rows[start - 1][group]) - 1) * 100
              : (lastA - rows[start - 1][group]) / initial * 100;
            close(numeric(row.querySelector('[data-metric="cumulative"]')), expectedCumulative);
            checks += 1;
          }
        }
      }
    }
  }
  controls.phase = 'unseen';
  get('filters').handlers.change();
  assert.match(get('visible-range').textContent, /82 日/);
  assert.equal(bodies[0].hidden, true);
  legends.find(b => b.dataset.curveKind === 'returns' && b.dataset.curveLane === '2').handlers.click();
  assert.equal((get('return-chart').innerHTML.match(/class="series-line /g) || []).length, 1);
  get('return-plot').handlers.keydown({target: get('return-plot'), key: 'Home', preventDefault() {}});
  assert.match(get('return-note').innerHTML, /研究净值/);
  get('signal-mode').value = 'ic';
  get('signal-mode').handlers.change();
  assert.match(get('signal-chart').innerHTML, /累计 IC/);
  expanders[0].handlers.click();
  get('close-expanded').handlers.click();
  get('reset-range').handlers.click();
  assert.match(get('visible-range').textContent, /566 日/);
  console.log(JSON.stringify({filters: checks, daily_rows: 566, stages: 3,
    interactions: ['legend', 'phase', 'date-keyboard', 'signal-mode', 'expand', 'reset']}));
})().catch(error => { console.error(error); process.exitCode = 1; });
