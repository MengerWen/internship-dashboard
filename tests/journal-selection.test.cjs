const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

function fixture() {
  const listeners = new Map(), elements = new Map();
  const element = () => ({classList: {toggle() {}}, addEventListener() {}, value: '', hidden: false, innerHTML: ''});
  const get = id => {
    if (!elements.has(id)) elements.set(id, element());
    return elements.get(id);
  };
  const overlay = {...element(), replaceChildren() { this.innerHTML = ''; }};
  const svg = {querySelector: () => overlay};
  const annotations = {parentElement: {}};
  const labels = ['a', 'b'].map(id => ({dataset: {journalChain: id}, classList: {toggle(name, value) { this[name] = value; }}, setAttribute() {}}));
  const document = {
    getElementById: get, addEventListener() {},
    querySelector: selector => ({'.journal-atlas': svg, '.journal-annotations': annotations, '.journal-scroller': get('scroller'), '.journal-evidence': get('evidence')})[selector],
    querySelectorAll: selector => selector === '.journal-chain-label' ? labels : []
  };
  get('view-journal').addEventListener = (name, handler) => listeners.set(name, handler);
  let rendered;
  const context = {CSS: {escape: value => value}, window: {JournalFloatingNotes: class {
    constructor(onFocus) { this.onFocus = onFocus; }
    render(config) { rendered = config; }
    clear() {}
  }}, document, localStorage: {getItem() { return null; }}, matchMedia: () => ({matches: true}), ResizeObserver: class { observe() {} }};
  vm.runInNewContext(fs.readFileSync('site/js/journal.js', 'utf8'), context);
  const day = {date: '2026-10-20', weekday: '周二', headline: '当天工作总述', chains: ['a', 'b'], chain_confidence: {}, chain_notes: {a: {note: '甲任务进展'}, b: {note: '乙任务进展'}}, chain_weights: {a: {value: 1}, b: {value: 2}}, highlights: ['整天的其他工作'], reports_covering: []};
  const view = Object.assign({}, context.window.JournalView);
  view.init({journal: [day], daily: [], chains: {tracks: [], handoffs: [], chains: [{id: 'a', short: '甲任务', label: '甲任务链'}, {id: 'b', short: '乙任务', label: '乙任务链'}]}}, {});
  view.atlas = {positions: new Map([['a', 100], ['b', 200]]), dateWidth: 50, right: 300, y: () => 80, radius: () => 4, ordered: [], active: new Map()};
  view.visible = [day]; view.selected = day.date; view.mode = 'atlas';
  view.writeHash = () => {}; view.render = () => {};
  return {view, day, get, labels, overlay, listeners, rendered: () => rendered};
}

test('点选只渲染该点，日期选中仍渲染整日', () => {
  const f = fixture();
  f.view.selection = {kind: 'point', date: f.day.date, chain: 'b'};
  f.view.highlightAtlas();
  assert.deepEqual(Array.from(f.rendered().ids), ['b']);
  assert.equal(f.labels[0].classList['is-selected'], false);
  assert.equal(f.labels[1].classList['is-selected'], true);
  assert(!f.overlay.innerHTML.includes('journal-selection-line'));
  f.view.selection = {kind: 'day', date: f.day.date};
  f.view.highlightAtlas();
  assert.deepEqual(Array.from(f.rendered().ids), ['a', 'b']);
  assert(f.overlay.innerHTML.includes('journal-selection-line'));
});

test('整链展开后点击链上的点，也切换到单点阅读', () => {
  const f = fixture();
  f.view.chain = 'b'; f.view.selection = {kind: 'chain', chain: 'b'};
  f.view.focusChainEvent = () => assert.fail('点击图上的点不能继续整链阅读');
  const point = {dataset: {date: f.day.date, journalPoint: 'b'}};
  f.listeners.get('click')({detail: 1, target: {closest: selector => selector === '[data-journal-point]' ? point : null}});
  assert.equal(f.view.selection.kind, 'point');
  assert.equal(f.view.selection.chain, 'b');
  assert.equal(f.view.chain, '');
});

test('整日浮窗内聚焦另一张卡，保留整日阅读范围', () => {
  const f = fixture();
  f.view.selection = {kind: 'day', date: f.day.date};
  f.view.floatingNotes.onFocus('a');
  assert.equal(f.view.selection.kind, 'day');
  assert.equal(f.rendered().focused, 'a');
  assert.deepEqual(Array.from(f.rendered().ids), ['a', 'b']);
});

test('单点详情只介绍当前任务，不混入当天其他任务', () => {
  const f = fixture();
  f.view.selection = {kind: 'point', date: f.day.date, chain: 'b'};
  f.view.renderDetail();
  const html = f.get('journal-detail').innerHTML;
  assert(html.includes('乙任务进展'));
  assert(!html.includes('甲任务进展'));
  assert(!html.includes('整天的其他工作'));
});

test('同一天从日期切到单点，再切回日期，浮窗与详情同步变化', () => {
  const f = fixture();
  f.view.selection = {kind: 'day', date: f.day.date};
  f.view.select(f.day.date, false, 'b');
  assert.equal(f.rendered().mode, 'point');
  assert.equal(f.rendered().group, 'point:2026-10-20:b');
  assert(!f.get('journal-detail').innerHTML.includes('甲任务进展'));
  f.view.select(f.day.date);
  assert.equal(f.rendered().mode, 'day');
  assert.equal(f.rendered().group, 'day:2026-10-20');
  assert(f.get('journal-detail').innerHTML.includes('甲任务进展'));
  assert(f.get('journal-detail').innerHTML.includes('整天的其他工作'));
});

test('单点说明被吸顶栏挡住时，校正滚动位置并同时保留点位', () => {
  const context = {window: {scrollBy: options => scrolls.push(options)}, innerHeight: 720,
    document: {querySelector: selector => selector === '.card' ? card : {getBoundingClientRect: () => ({bottom: 300})}}};
  const scrolls = [], card = {hidden: false, offsetTop: 1400, offsetHeight: 240, parentElement: {getBoundingClientRect: () => ({top: -1300})}};
  vm.runInNewContext(fs.readFileSync('site/js/journal.js', 'utf8'), context);
  const view = Object.assign({}, context.window.JournalView, {floatingNotes: {open: true}, atlas: {y: () => 1670}});
  view.revealFloatingNote('.card', '2026-10-20');
  assert.equal(scrolls.length, 1);
  assert.equal(scrolls[0].top, -228);
  card.parentElement.getBoundingClientRect = () => ({top: -1072});
  view.revealFloatingNote('.card', '2026-10-20');
  assert.equal(scrolls.length, 1, '点与卡片都已可见时，不额外滚动');
});
