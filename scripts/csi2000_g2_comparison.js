/* 共同开发期内的新旧模型金额路径。 */
(() => {
  function curves(data, key, market, view) {
    const weight = key.split('-')[0];
    const indices = market === 'all' ? [0, 1] : [market === 'sh' ? 0 : 1];
    const total = values => indices.reduce((sum, i) => sum + values[i], 0);
    const capital = total(data.initial[weight]);
    const base = data.base[weight].map(row => total(row) / capital * 100);
    const old = data.series.baseline[key].map(row => total(row) / capital * 100);
    const added = data.series.G2[key].map(row => total(row) / capital * 100);
    return {
      baseline: old.map((value, i) => value + (view === 'wealth' ? base[i] - 100 : 0)),
      G2: added.map((value, i) => value + (view === 'wealth' ? base[i] - 100 : 0)),
      base: view === 'wealth' ? base.map(value => value - 100) : null,
      delta: added.map((value, i) => value - old[i])
    };
  }
  if (typeof module !== 'undefined') module.exports = { curves };
  if (typeof document === 'undefined') return;
  const root = document.getElementById('g2-comparison');
  if (!root) return;
  const get = id => document.getElementById('g2-' + id);
  const filters = document.getElementById('filters');
  const own = get('filters');
  const slider = get('date');
  const ns = 'http://www.w3.org/2000/svg';
  const colors = ['var(--blue)', 'var(--focus)', 'var(--text)'];
  let data, paths, selected = 307;
  const make = (tag, attributes, text) => {
    const node = document.createElementNS(ns, tag);
    for (const [name, value] of Object.entries(attributes)) node.setAttribute(name, String(value));
    if (text !== undefined) node.textContent = text;
    return node;
  };
  const signed = value => (value > 0 ? '+' : '') + value.toFixed(4);
  function draw(svg, series, labels, difference = false) {
    const width = Math.max(280, svg.parentElement.clientWidth);
    const height = difference ? 185 : 290;
    const left = width < 500 ? 54 : 70, right = 20, top = 20, bottom = 32;
    const finite = series.flat().filter(Number.isFinite);
    let low = Math.min(0, ...finite), high = Math.max(0, ...finite);
    const padding = (high - low || .01) * .12;
    low -= padding; high += padding;
    const x = i => left + i / (data.dates.length - 1) * (width - left - right);
    const y = v => top + (high - v) / (high - low) * (height - top - bottom);
    svg.setAttribute('viewBox', `0 0 ${width} ${height}`);
    svg.style.height = height + 'px';
    svg.replaceChildren();
    svg.append(make('title', {}, labels.join('、') + '，' + data.dates[0] + '至' + data.dates.at(-1)));
    for (let k = 0; k <= 4; k++) {
      const v = low + k * (high - low) / 4;
      svg.append(make('line', { x1: left, x2: width - right, y1: y(v), y2: y(v), stroke: 'var(--line-soft)', 'stroke-width': .6 }));
      svg.append(make('text', { x: left - 8, y: y(v) + 4, 'text-anchor': 'end', fill: 'var(--text)', 'font-size': 12 }, v.toFixed(2)));
    }
    svg.append(make('line', { x1: left, x2: width - right, y1: y(0), y2: y(0), stroke: 'var(--line)', 'stroke-width': 1 }));
    const ticks = width < 500 ? [0, 153, 307] : [0, 77, 154, 231, 307];
    ticks.forEach((i, k) => svg.append(make('text', { x: x(i), y: height - 9,
      'text-anchor': k === 0 ? 'start' : k === ticks.length - 1 ? 'end' : 'middle', fill: 'var(--text)', 'font-size': 12 }, data.dates[i])));
    series.forEach((values, k) => {
      let connected = false;
      const d = values.map((v, i) => {
        if (!Number.isFinite(v)) { connected = false; return ''; }
        const operation = connected ? 'L' : 'M'; connected = true;
        return `${operation}${x(i).toFixed(2)},${y(v).toFixed(2)}`;
      }).join(' ');
      svg.append(make('path', { d, fill: 'none', stroke: difference ? 'var(--blue)' : colors[k],
        'stroke-width': k === 2 ? 1 : 2.2, 'stroke-dasharray': !difference && k === 0 ? '6 3' : !difference && k === 2 ? '2 3' : 'none' }));
    });
    svg.append(make('line', { x1: x(selected), x2: x(selected), y1: top, y2: height - bottom,
      stroke: 'var(--text)', 'stroke-width': .8, 'stroke-dasharray': '3 4' }));
    svg.onpointermove = event => {
      if (event.pointerType === 'touch') return;
      const box = svg.getBoundingClientRect();
      select(Math.max(0, Math.min(307, Math.round(((event.clientX - box.left) * width / box.width - left) / (width - left - right) * 307))));
    };
  }
  function select(index) {
    selected = index; slider.value = String(index);
    get('readout').textContent = `${data.dates[index]}　baseline ${signed(paths.baseline[index])}%　G2 ${signed(paths.G2[index])}%　差额 ${signed(paths.delta[index])} 个百分点`;
    paint();
  }
  function paint() {
    const series = [paths.baseline, paths.G2];
    if (paths.base) series.push(paths.base);
    draw(get('main'), series, paths.base ? ['baseline', 'G2', '底仓'] : ['baseline', 'G2']);
    draw(get('delta'), [paths.delta], ['G2减baseline，百分点'], true);
  }
  function update() {
    if (!data) return;
    const shared = filters.elements, local = own.elements;
    const fraction = Number(shared.tradeFraction.value);
    const key = [shared.weight.value, shared.sorting.value, local.horizon.value, shared.strategy.value, shared.q.value].join('-') + (fraction === 10 ? '' : '-t' + fraction);
    paths = curves(data, key, local.market.value, local.view.value);
    get('unit').textContent = local.view.value === 'wealth' ? '累计研究收益（%）' : '累计底仓增强（%）';
    get('base-legend').hidden = !paths.base;
    get('end').textContent = `期末：baseline ${signed(paths.baseline.at(-1))}%　G2 ${signed(paths.G2.at(-1))}%　增量 ${signed(paths.delta.at(-1))} 个百分点`;
    select(selected);
  }
  async function start() {
    try {
      const bytes = Uint8Array.from(atob(get('data').textContent.trim()), c => c.charCodeAt(0));
      data = JSON.parse(await new Response(new Blob([bytes]).stream().pipeThrough(new DecompressionStream('gzip'))).text());
      filters.addEventListener('change', update);
      own.addEventListener('change', update);
      slider.addEventListener('input', () => select(Number(slider.value)));
      new ResizeObserver(() => { if (paths) paint(); }).observe(get('main').parentElement);
      update();
    } catch (error) {
      get('readout').textContent = 'G2比较数据读取失败：' + error.message;
      get('readout').setAttribute('role', 'alert');
    }
  }
  start();
})();
