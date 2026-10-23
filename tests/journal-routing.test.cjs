const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

function render({density = 14, width = 1000, middle = '2026-10-16', target = '2026-10-16', dropped = false} = {}) {
  const elements = new Map();
  const element = () => ({innerHTML: '', hidden: false, scrollLeft: 0, clientWidth: width, classList: {contains: () => true}, insertAdjacentHTML() {}});
  const get = name => {
    if (!elements.has(name)) elements.set(name, element());
    return elements.get(name);
  };
  const context = {window: {}, document: {activeElement: null, getElementById: get, querySelector: get}};
  vm.runInNewContext(fs.readFileSync('site/js/journal.js', 'utf8'), context);
  const days = [...new Set(['2026-10-16', middle, target])].sort().map(date => ({date, weekday: '工作日', chains: ['from', 'middle', 'to'].filter(id => date === ({from: '2026-10-16', middle, to: target})[id])}));
  const view = Object.assign({}, context.window.JournalView, {
    mode: 'atlas', density, days, selection: null, selected: null,
    registry: {tracks: [{id: 'track', label: '任务'}], chains: ['from', 'middle', 'to'].map(id => ({id, track: 'track', label: id, short: id, fate: id === 'middle' && dropped ? 'dropped' : ''})), handoffs: [{from: 'from', to: 'to', date: target, source_date: '2026-10-16', type: '派生'}]},
    floatingNotes: {capture() {}}, visibleDays: () => days,
    pointRadius: () => 4, pointNote: (day, id) => id === 'middle' && dropped ? {outcome: 'dropped'} : {}, pointWeight: () => 1,
    pointEvidence: () => ({status: 'artifact'}), weightLabel: () => '', evidenceLabel: () => '',
    weightLegendHtml: () => '', highlightAtlas() {}
  });
  view.renderAtlas();
  return {svg: get('.journal-scroller').innerHTML, atlas: view.atlas, view};
}

// 独立采样实际输出的 SVG 路径，避免测试复用寻路器的碰撞判断。
function samplePath(path) {
  const tokens = path.match(/[MLCQ]|-?\d+(?:\.\d+)?(?:e[+-]?\d+)?/gi), points = [];
  let i = 0, current;
  while (i < tokens.length) {
    const command = tokens[i++], count = {M: 2, L: 2, C: 6, Q: 4}[command];
    assert(count, `不支持的路径指令 ${command}`);
    const values = tokens.slice(i, i += count).map(Number), end = {x: values.at(-2), y: values.at(-1)};
    if (command === 'M') { current = end; points.push(end); continue; }
    const steps = Math.ceil(Math.hypot(end.x - current.x, end.y - current.y) * 4) + 40;
    for (let n = 1; n <= steps; n++) {
      const t = n / steps, u = 1 - t;
      const x = command === 'L' ? current.x * u + end.x * t : command === 'Q' ? current.x * u * u + 2 * u * t * values[0] + t * t * end.x : current.x * u ** 3 + 3 * u * u * t * values[0] + 3 * u * t * t * values[2] + t ** 3 * end.x;
      const y = command === 'L' ? current.y * u + end.y * t : command === 'Q' ? current.y * u * u + 2 * u * t * values[1] + t * t * end.y : current.y * u ** 3 + 3 * u * u * t * values[1] + 3 * u * t * t * values[3] + t ** 3 * end.y;
      points.push({x, y});
    }
    current = end;
  }
  return points;
}

test('同日横跨三列时，真实交接线绕过中间节点并保留关系', () => {
  const {svg, atlas} = render();
  const path = /class="journal-handoff-path"[^>]*d="([^"]+)"/.exec(svg)[1];
  const distance = Math.min(...samplePath(path).map(p => Math.hypot(p.x - atlas.positions.get('middle'), p.y - atlas.y('2026-10-16'))));
  assert(distance >= 7.2, `交接线仍遮住中间节点，中心距离只有 ${distance.toFixed(2)}px`);
  assert(svg.includes('data-chains="from to"'));
  assert(svg.includes('stroke-dasharray="4 3"'));
});

test('不同日期与窄列宽下，曲线仍避让中间节点', () => {
  for (const width of [390, 1440]) for (const density of [7, 14, 20, 44]) {
    const {svg, atlas} = render({width, density, middle: '2026-10-17', target: '2026-10-18'});
    const path = /class="journal-handoff-path"[^>]*d="([^"]+)"/.exec(svg)[1];
    const distance = Math.min(...samplePath(path).map(p => Math.hypot(p.x - atlas.positions.get('middle'), p.y - atlas.y('2026-10-17'))));
    assert(distance >= 7.2, `${width}px / 间距 ${density}：中心距离 ${distance}`);
  }
});

test('节点保护层独立于高亮状态，压缩后仍覆盖圆点和未采用标记', () => {
  for (const dropped of [false, true]) {
    const {svg} = render({density: 4, dropped});
    assert.match(svg, /<mask[^>]*id="journal-handoff-clearance"[^>]*maskUnits="userSpaceOnUse"/);
    assert.match(svg, /class="journal-unit journal-handoff"[^>]*mask="url\(#journal-handoff-clearance\)"/);
    const mask = /<mask[\s\S]*?<\/mask>/.exec(svg)[0];
    assert.equal((mask.match(/fill="black"/g) || []).length, 3, '每个节点都应有固定留白');
    if (dropped) assert.match(mask, /<rect[^>]*fill="black"/);
  }
});

