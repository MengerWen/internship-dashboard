const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

function render({density = 14, width = 1000, source = '2026-10-16', middle = '2026-10-16', target = '2026-10-16', dropped = false, records, radii = {}, closed = [], order = ['from', 'middle', 'to']} = {}) {
  const elements = new Map();
  const element = () => ({innerHTML: '', hidden: false, scrollLeft: 0, clientWidth: width, classList: {contains: () => true}, insertAdjacentHTML() {}});
  const get = name => {
    if (!elements.has(name)) elements.set(name, element());
    return elements.get(name);
  };
  const context = {window: {}, document: {activeElement: null, getElementById: get, querySelector: get}};
  vm.runInNewContext(fs.readFileSync('site/js/journal.js', 'utf8'), context);
  records ||= {from: [source], middle: [middle], to: [target]};
  const days = [...new Set(Object.values(records).flat())].sort().map(date => ({date, weekday: '工作日', chains: order.filter(id => records[id].includes(date))}));
  const view = Object.assign({}, context.window.JournalView, {
    mode: 'atlas', density, days, selection: null, selected: null,
    registry: {tracks: [{id: 'track', label: '任务'}], chains: order.map(id => ({id, track: 'track', label: id, short: id, fate: id === 'middle' && dropped ? 'dropped' : '', status: closed.includes(id) ? 'done' : 'active', end: records[id].at(-1)})), handoffs: [{from: 'from', to: 'to', date: target, source_date: source, type: '派生'}]},
    floatingNotes: {capture() {}}, visibleDays: () => days,
    pointRadius: (day, id) => radii[`${id}:${day.date}`] ?? 4, pointNote: (day, id) => id === 'middle' && dropped ? {outcome: 'dropped'} : {}, pointWeight: () => 1,
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

test('相邻密集列的跨日期关系不拱到起点之前，也不沿时间轴折返', () => {
  const source = '2026-07-07', target = '2026-07-23';
  const records = {from: [source, '2026-07-08', '2026-07-13'], to: [source, '2026-07-08', '2026-07-09', '2026-07-10', '2026-07-13', '2026-07-22', target]};
  const {svg, atlas} = render({width: 178, source, target, records, order: ['from', 'to']});
  const path = /class="journal-handoff-path"[^>]*d="([^"]+)"/.exec(svg)[1], samples = samplePath(path);
  assert(samples.every(p => p.y >= atlas.y(source) - .01 && p.y <= atlas.y(target) + .01), '连线不能绕到更早或更晚的日期，制造无意义的鼓包');
  assert(samples.every((p, i) => !i || p.y >= samples[i - 1].y - .01), '跨日期的线应始终向下推进');
  assert(!/[LQ]/.test(path), '不能用台阶拼接代替流畅的走势');
});

test('跨过一列连续记录时，转向摊开在日期跨度中，不拼水平台阶', () => {
  const source = '2026-09-08', target = '2026-09-20';
  const records = {from: [source, '2026-09-09'], middle: [source, '2026-09-09', '2026-09-10', '2026-09-11'], to: ['2026-09-18', target, '2026-09-21']};
  const {svg, atlas} = render({width: 224, source, target, records});
  const path = /class="journal-handoff-path"[^>]*d="([^"]+)"/.exec(svg)[1], samples = samplePath(path);
  assert(!/[LQ]/.test(path), '长线不能用水平横杆与圆角拼成');
  assert(samples.every((p, i) => !i || p.y >= samples[i - 1].y - .001), '避让不能沿日期折返');
  for (const date of records.middle) {
    const distance = Math.min(...samples.map(p => Math.hypot(p.x - atlas.positions.get('middle'), p.y - atlas.y(date))));
    assert(distance >= 7.2, '缓变曲线仍需避开连续节点');
  }
});

test('中段上下都有节点、端点附近还有一列密集点时，仍使用完整曲线', () => {
  const records = {
    from: ['2026-10-15', '2026-10-16'], to: ['2026-10-15', '2026-10-16'],
    middle: ['2026-10-13', '2026-10-14', '2026-10-15', '2026-10-16'],
    near: ['2026-10-17', '2026-10-18', '2026-10-19', '2026-10-20', '2026-10-21']
  };
  for (const width of [390, 1280]) {
    const {svg, atlas} = render({width, records, order: ['to', 'near', 'middle', 'from']});
    const path = /class="journal-handoff-path"[^>]*d="([^"]+)"/.exec(svg)[1], samples = samplePath(path);
    assert.match(path, /^M[^A-Z]+ C[^A-Z]+$/, '密集区应先调整两端弧度，而不是退回台阶');
    for (const [id, dates] of Object.entries(records)) for (const date of dates) {
      if (['from', 'to'].includes(id) && date === '2026-10-16') continue;
      const distance = Math.min(...samples.map(p => Math.hypot(p.x - atlas.positions.get(id), p.y - atlas.y(date))));
      assert(distance >= 7.2, `${width}px 时曲线侵入 ${id} / ${date} 的留白`);
    }
  }
});

test('绕点时整条线连续舒展，不在端点附近突然折向', () => {
  const {svg, atlas} = render();
  const path = /class="journal-handoff-path"[^>]*d="([^"]+)"/.exec(svg)[1];
  assert.match(path, /^M[^A-Z]+ C[^A-Z]+$/, '这条简单关系应以一段完整曲线绕点，不能拼出直角台阶');
  const points = samplePath(path), span = atlas.positions.get('to') - atlas.positions.get('from');
  const angles = points.slice(1).map((p, i) => Math.atan2(p.y - points[i].y, p.x - points[i].x));
  const turning = angles.slice(1).reduce((sum, angle, i) => sum + Math.abs(angle - angles[i]), 0);
  assert(turning < Math.PI / 2, '平缓的同日连线不应先急转再折回');
  assert(points.every(p => p.x >= atlas.positions.get('from') && p.x <= atlas.positions.get('to')), '绕行不能回头');
  assert(Math.max(...points.map(p => Math.abs(p.y - atlas.y('2026-10-16')))) < span / 4, '绕点弧度应随跨度舒展');
});

test('同日交接绕过大小不等的密集节点时，弧顶不能挤成尖角', () => {
  const source = '2026-10-24', records = {
    from: ['2026-10-20', '2026-10-21', '2026-10-22', '2026-10-23', source],
    middle: [source, '2026-10-25'], to: [source, '2026-10-25']
  };
  const radii = {
    'from:2026-10-20': 5.663, 'from:2026-10-21': 8.507, 'from:2026-10-22': 9.449,
    'from:2026-10-23': 8.25, 'from:2026-10-24': 6.480,
    'middle:2026-10-24': 7.125, 'middle:2026-10-25': 4.875,
    'to:2026-10-24': 4.875, 'to:2026-10-25': 9.144
  };
  const {svg, atlas} = render({width: 224, source, target: source, records, radii, closed: ['from']});
  const path = /class="journal-handoff-path"[^>]*d="([^"]+)"/.exec(svg)[1], points = samplePath(path);
  let minimumRadius = Infinity;
  for (let i = 1; i < points.length - 1; i++) {
    const [a, b, c] = points.slice(i - 1, i + 2);
    if (['from', 'to'].some(id => Math.hypot(b.x - atlas.positions.get(id), b.y - atlas.y(source)) < radii[`${id}:${source}`] + 4.2)) continue;
    const cross = Math.abs((b.x - a.x) * (c.y - a.y) - (b.y - a.y) * (c.x - a.x));
    if (cross > 1e-10) minimumRadius = Math.min(minimumRadius, Math.hypot(b.x - a.x, b.y - a.y) * Math.hypot(c.x - b.x, c.y - b.y) * Math.hypot(c.x - a.x, c.y - a.y) / (2 * cross));
  }
  assert(minimumRadius >= 8, `可见弧线的转弯半径只有 ${minimumRadius.toFixed(2)}px，仍有近似尖角`);
  for (const date of records.middle) {
    const distance = Math.min(...points.map(p => Math.hypot(p.x - atlas.positions.get('middle'), p.y - atlas.y(date))));
    assert(distance >= radii[`middle:${date}`] + 4.2, '平滑后仍须保留中间节点的留白');
  }
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

