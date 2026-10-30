const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const root = path.resolve(__dirname, '../..');
const manifest = JSON.parse(fs.readFileSync(path.join(root, 'dist/manifest.json')));
const code = fs.readFileSync(process.argv[3] || path.join(root, 'site/js/journal.js'), 'utf8');
const output = [];
for (const width of [1100, 1440, 2300]) for (const density of [4, 7, 14, 23, 44]) {
  const elements = new Map();
  const get = name => {
    if (!elements.has(name)) elements.set(name, {innerHTML: '', hidden: false, scrollLeft: 0, clientWidth: width, classList: {contains: () => true}, insertAdjacentHTML() {}});
    return elements.get(name);
  };
  const context = {window: {}, document: {activeElement: null, getElementById: get, querySelector: get}};
  vm.runInNewContext(code, context);
  const view = Object.assign({}, context.window.JournalView, {
    mode: 'atlas', density, days: manifest.journal, selection: null, selected: null,
    registry: manifest.chains, chains: new Map(manifest.chains.chains.map(c => [c.id, c])),
    reports: new Map(manifest.daily.map(d => [d.date, d])),
    floatingNotes: {capture() {}}, visibleDays: () => manifest.journal, highlightAtlas() {}
  });
  const start = performance.now();
  view.renderAtlas();
  const svg = get('.journal-scroller').innerHTML;
  const edges = [];
  for (const match of svg.matchAll(/<g class="journal-unit journal-handoff"([^>]+)>[\s\S]*?<path class="journal-handoff-path"[^>]*d="([^"]+)"/g)) {
    const tokens = match[2].match(/[MC]|-?\d+(?:\.\d+)?(?:e[+-]?\d+)?/gi);
    const curves = [];
    let p, i = 0;
    while (i < tokens.length) {
      const command = tokens[i++];
      const point = () => ({x: Number(tokens[i++]), y: Number(tokens[i++])});
      if (command === 'M') p = point();
      else { const a = point(), b = point(), q = point(); curves.push([p, a, b, q]); p = q; }
    }
    const tangent = points => {
      for (let k = 1; k < 4; k++) {
        const v = {x: points[k].x - points[0].x, y: points[k].y - points[0].y};
        if (Math.hypot(v.x, v.y) > 1e-7) return v;
      }
      return {x: 0, y: 0};
    };
    const angles = curves.slice(1).map((curve, k) => {
      const a = tangent(curves[k].slice().reverse()), b = tangent(curve);
      const length = Math.hypot(a.x, a.y) * Math.hypot(b.x, b.y);
      return length ? Math.acos(Math.max(-1, Math.min(1, -(a.x * b.x + a.y * b.y) / length))) * 180 / Math.PI : 0;
    });
    let minRadius = Infinity, tightAt;
    for (const [a, b, c, d] of curves) for (let n = 1; n < 1000; n++) {
      const t = n / 1000, u = 1 - t;
      const x = a.x * u ** 3 + 3 * b.x * u * u * t + 3 * c.x * u * t * t + d.x * t ** 3;
      const y = a.y * u ** 3 + 3 * b.y * u * u * t + 3 * c.y * u * t * t + d.y * t ** 3;
      const v = {}, acc = {};
      for (const key of ['x', 'y']) {
        v[key] = 3 * (u * u * (b[key] - a[key]) + 2 * u * t * (c[key] - b[key]) + t * t * (d[key] - c[key]));
        acc[key] = 6 * (u * (c[key] - 2 * b[key] + a[key]) + t * (d[key] - 2 * c[key] + b[key]));
      }
      const radius = Math.hypot(v.x, v.y) ** 3 / Math.abs(v.x * acc.y - v.y * acc.x);
      if (radius < minRadius) { minRadius = radius; tightAt = {x, y}; }
    }
    edges.push({chains: /data-chains="([^"]+)"/.exec(match[1])[1], source: /data-source-date="([^"]+)"/.exec(match[1])[1], date: /data-date="([^"]+)"/.exec(match[1])[1], maxJoin: Math.max(0, ...angles), minRadius, tightAt, segments: curves.length, path: match[2]});
  }
  output.push({width, density, duration: performance.now() - start, edges});
  if ((width === 1100 || width === 2300) && density === 14) fs.writeFileSync(path.join(__dirname, process.argv[2] + '-' + width + '-atlas.svg'), svg.slice(0, svg.indexOf('</svg>') + 6));
}
fs.writeFileSync(path.join(__dirname, (process.argv[2] || 'audit') + '.json'), JSON.stringify(output, null, 2));
console.log(JSON.stringify(output.map(row => ({width: row.width, density: row.density, duration: row.duration, edges: row.edges.length, maxJoin: Math.max(...row.edges.map(e => e.maxJoin))})), null, 2));
