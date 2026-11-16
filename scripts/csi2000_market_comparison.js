(async () => {
  'use strict';
  const get = id => document.getElementById(id);
  const form = get('filters');
  const dashboard = get('compare');
  const signalMode = get('signal-mode');
  const resetRange = get('reset-range');
  const closeExpanded = get('close-expanded');
  const rangeText = get('visible-range');
  const status = get('date-status');
  const optionButtons = [...document.querySelectorAll('[data-return-view]')];
  const curveLegend = [...document.querySelectorAll('[data-curve-lane]')];
  const series = [
    { market: 'sse', label: '沪市 11:30', cycle: 'morning', group: 0, dashed: false },
    { market: 'sse', label: '沪市 收盘', cycle: 'close', group: 0, dashed: true },
    { market: 'szse', label: '深市 11:30', cycle: 'morning', group: 1, dashed: false },
    { market: 'szse', label: '深市 收盘', cycle: 'close', group: 1, dashed: true }
  ];
  const phases = {
    development: { label: '开发 OOF', short: '开发' },
    seen: { label: '已看 Test', short: '已看' },
    unseen: { label: '未看 Test', short: '未看' }
  };
  const panels = {
    returns: { plot: get('return-plot'), svg: get('return-chart'), note: get('return-note'), figure: get('return-figure') },
    signal: { plot: get('signal-plot'), svg: get('signal-chart'), note: get('signal-note'), figure: get('signal-figure') }
  };
  const format = (v, digits = 2) => Number.isFinite(v) ? v.toFixed(digits).replace('-', '−') : '—';
  const coord = value => Number(value.toFixed(2));
  const style = info => info.market + (info.dashed ? ' close-line' : '');
  const metrics = ['tradeMean', 'mean', 'cumulative', 'sharpe', 'sharpeThrough', 'drawdown', 'calmar', 'volatility', 'winRate', 'payoff', 't'];
  const focusedLanes = { returns: null, signal: null };
  let data;
  let timeline;
  let visible;
  let portfolio;
  let weight;
  let sorting;
  let tradeFraction = '10';
  let phaseChoice = 'all';
  let view = 'wealth';
  let zoom = null;
  let selection = null;
  let pinned = false;
  let drag = null;
  let expanded = null;
  let expandedFrom = null;
  const isEnhancement = () => view === 'enhancement';
  const returnLabel = () => isEnhancement() ? '超额收益' : '绝对收益';
  const feeLabel = () => data.fees ? '扣税费后' : '费用前';
  const hasPoolReference = () => !isEnhancement();
  const configurationKey = cycle => [weight, sorting, cycle, ...portfolio].join('-') +
    (tradeFraction === '10' ? '' : '-t' + tradeFraction);

  function moments() {
    return { n: 0, mean: 0, m2: 0, wins: 0, losses: 0, gain: 0, loss: 0 };
  }

  function add(m, value) {
    if (!Number.isFinite(value)) return;
    m.n += 1;
    const d = value - m.mean;
    m.mean += d / m.n;
    m.m2 += d * (value - m.mean);
    if (value > 0) { m.wins += 1; m.gain += value; }
    if (value < 0) { m.losses += 1; m.loss -= value; }
  }

  function deviation(m) {
    return m.n > 1 ? Math.sqrt(m.m2 / (m.n - 1)) : null;
  }

  function sharpe(m) {
    const sd = deviation(m);
    return sd ? Math.sqrt(252) * m.mean / sd : null;
  }

  function timelineFor() {
    const byLane = series.map(({cycle}) => data.series[configurationKey(cycle)]);
    const staged = {};
    const dateRanges = {};
    const all = series.map(moments);
    const signal = series.map(() => ({ ic: 0, rankic: 0, nIC: 0, nRank: 0 }));
    const initial = data.initial[weight];
    const bases = data.base[weight];
    const points = data.dates.map((date, at) => {
      const phase = data.stages[at];
      if (!staged[phase]) {
        staged[phase] = series.map(() => ({
          sample: moments(), trade: moments(), peak: isEnhancement() ? 0 : 1, drawdown: 0, cumulative: null
        }));
        dateRanges[phase] = [at, at];
      }
      dateRanges[phase][1] = at;
      const values = series.map(({group}, lane) => {
        const row = byLane[lane][at];
        const a = row[group];
        const priorA = at ? byLane[lane][at - 1][group] : 0;
        const b = bases[at][group];
        const priorB = at ? bases[at - 1][group] : initial[group];
        const capital = initial[group];
        const priorW = priorB + priorA;
        const nav = (b + a) / capital;
        const baseNav = b / capital;
        const enhancement = priorB > 0 ? (a - priorA) / priorB : null;
        const wealthReturn = priorW > 0 ? (b + a) / priorW - 1 : null;
        const daily = isEnhancement() ? enhancement : wealthReturn;
        const cumulative = isEnhancement() ? a / capital : nav - 1;
        const start = dateRanges[phase][0];
        const a0 = start ? byLane[lane][start - 1][group] : 0;
        const b0 = start ? bases[start - 1][group] : capital;
        const relative = isEnhancement() ? (a - a0) / capital : (b0 + a0 > 0 ? (b + a) / (b0 + a0) : null);
        const local = staged[phase][lane];
        const tradeKey = configurationKey(series[lane].cycle);
        const tradeAmounts = data.trading?.[tradeKey]?.[at]?.[group];
        const tradeReturn = tradeAmounts?.[0] > 0 ? (tradeAmounts[1] - tradeAmounts[2]) / tradeAmounts[0] : null;
        add(local.trade, tradeReturn);
        add(local.sample, daily);
        add(all[lane], daily);
        if (Number.isFinite(relative)) {
          local.peak = Math.max(local.peak, relative);
          local.drawdown = Math.max(local.drawdown, isEnhancement() ? local.peak - relative : 1 - relative / local.peak);
          local.cumulative = isEnhancement() ? relative : relative - 1;
        }
        const [ic, rankic, validN, eligibleN] = data.signal[phase][lane][at - start] ?? [];
        const history = signal[lane];
        if (Number.isFinite(ic)) { history.ic += ic; history.nIC += 1; }
        if (Number.isFinite(rankic)) { history.rankic += rankic; history.nRank += 1; }
        return {
          daily: daily === null ? null : daily * 10000, cumulative: cumulative * 100, nav, baseNav,
          addition: a / capital * 100, enhancement: enhancement === null ? null : enhancement * 10000,
          poolCumulative: (baseNav - 1) * 100, selectedN: row[2 + group], filledN: row[4 + group],
          sharpe: sharpe(all[lane]), ic, rankic, validN, eligibleN,
          tradeReturn: tradeReturn === null ? null : tradeReturn * 10000,
          cumulativeIC: history.nIC ? history.ic : null,
          cumulativeRankIC: history.nRank ? history.rankic : null,
          meanIC: history.nIC ? history.ic / history.nIC : null,
          meanRankIC: history.nRank ? history.rankic / history.nRank : null
        };
      });
      for (const local of staged[phase].entries()) local[1].through = sharpe(all[local[0]]);
      return { date, phase, values, stageDay: at - dateRanges[phase][0] + 1 };
    });
    for (const point of points) {
      const [start, end] = dateRanges[point.phase];
      point.stageDays = end - start + 1;
    }
    return { points, dateRanges, staged };
  }

  __CHART_HELPERS__

  function dateNote(point, index, kind) {
    const lane = focusedLanes[kind];
    const label = kind === 'returns' ? ' · ' + portfolio.join('') + ' · 做 T ' + tradeFraction + '% · 累计' + returnLabel() : '';
    const head = '<div class="note-head"><div class="note-date"><time datetime="' + point.date + '">' +
      point.date + '</time><span>' + phases[point.phase].label + label + '</span></div>' +
      (pinned ? '<button class="demo-button note-dismiss" type="button" data-close-note>关闭</button>' : '') +
      '</div><p>本段第 ' + point.stageDay + '／' + point.stageDays + ' 日 · 全程 ' + (index + 1) + ' 日</p>';
    if (kind === 'signal') {
      return head + detailsTable(['日 IC', '日 RankIC', '累计 IC', '累计 RankIC'], point.values, row => [
        format(row.ic, 3), format(row.rankic, 3), format(row.cumulativeIC, 3), format(row.cumulativeRankIC, 3)
      ], lane);
    }
    return head + detailsTable(['交易净收益 bp', '当日增强 bp', '累计增强 %', '研究净值', '底仓净值', '入选', '有价成交'],
      point.values, row => [format(row.tradeReturn), format(row.enhancement), format(row.addition), format(row.nav, 4),
        format(row.baseNav, 4), row.selectedN, row.filledN], lane);
  }

  __SELECTION_HELPERS__

  function choose(index, kind, y, announce = false) {
    selection = { index, kind, y };
    refreshSelection();
    if (!announce) return;
    const point = timeline.points[index];
    const lane = focusedLanes[kind];
    status.textContent = point.date + ' ' + point.values.map((value, i) => {
      if (lane !== null && i !== lane) return '';
      const detail = kind === 'signal' ? format(value[signalMode.value], 3) :
        '累计' + returnLabel() + ' ' + format(value.cumulative) + '%';
      return series[i].label + ' ' + detail;
    }).filter(Boolean).join('，');
  }

  __POINTER_HELPERS__

  function updateScoreRows() {
    const table = get('score-rows');
    table.querySelector('[data-score-column="mean"]').textContent = isEnhancement() ? '底仓日均增强 bp' : '账户日均净收益 bp';
    table.querySelector('[data-score-column="cumulative"]').textContent = isEnhancement() ? '累计超额 %' : '累计绝对 %';
    table.querySelector('.score-fields [data-score-column="drawdown"]').textContent =
      isEnhancement() ? '回撤 pp' : '回撤 %';
    for (const body of table.tBodies) {
      const phase = body.dataset.stageBlock;
      body.hidden = phaseChoice !== 'all' && phaseChoice !== phase;
      for (const row of body.rows) {
        const { sample, trade, through, cumulative, drawdown } = timeline.staged[phase][Number(row.dataset.lane)];
        const sd = deviation(sample);
        const annual = cumulative === null || !sample.n ? null :
          isEnhancement() ? cumulative * 252 / sample.n :
            cumulative > -1 ? (1 + cumulative) ** (252 / sample.n) - 1 : null;
        const values = {
          tradeMean: trade.n ? trade.mean * 10000 : null,
          mean: sample.n ? sample.mean * 10000 : null,
          cumulative: cumulative === null ? null : cumulative * 100,
          sharpe: sharpe(sample), sharpeThrough: through, drawdown: sample.n ? drawdown * 100 : null,
          calmar: drawdown > 0 && annual !== null ? annual / drawdown : null,
          volatility: sd !== null ? Math.sqrt(252) * sd * 100 : null,
          winRate: sample.n ? sample.wins / sample.n * 100 : null,
          payoff: sample.wins && sample.losses ? (sample.gain / sample.wins) / (sample.loss / sample.losses) : null,
          t: sd ? Math.sqrt(sample.n) * sample.mean / sd : null
        };
        for (const metric of metrics) {
          const cell = row.querySelector('[data-metric="' + metric + '"]');
          if (!cell) continue;
          const value = values[metric];
          cell.textContent = format(value);
          cell.classList.toggle('negative', Number.isFinite(value) && value < 0);
        }
      }
    }
    const title = '中证 2000 · ' + (weight === 'index' ? '指数权重' : '等权') +
      ' · ' + (sorting === 'combined' ? '沪深合并排序' : '分市场排序');
    get('index-view-label').textContent = title;
    get('table-status').textContent = portfolio.join('') + ' · 做 T ' + tradeFraction + '% · ' +
      (phaseChoice === 'all' ? '全部阶段' : phases[phaseChoice].label) + ' · ' + returnLabel() + ' · ' + feeLabel();
    get('score-note').textContent = '交易日均净收益：每日按实际进场金额加权批次净收益率，再对有交易日期等权平均；跨日按进场日归属。其余指标按下述账户口径计算。' + (isEnhancement()
      ? '日超额为当日做 T 增量损益除以该市场昨日底仓价值。分段累计超额和回撤按该市场初始底仓折算，回撤单位为百分点。胜率统计做 T 增量为正的天数占比。'
      : '绝对收益包含底仓与做 T。各段累计收益和回撤以段前研究净值为起点，胜率统计整体日收益为正的天数占比。Sharpe 的「截至本段」从首个交易日算至该段末。');
  }

  function drawAll() {
    visible = getWindow();
    for (const kind of Object.keys(panels)) {
      for (const button of curveLegend) {
        if (button.dataset.curveKind !== kind) continue;
        const lane = focusedLanes[kind];
        button.setAttribute('aria-pressed', String(button.dataset.curveLane === (lane === null ? 'all' : String(lane))));
      }
      drawChart(kind);
    }
    get('pool-reference-note').hidden = !hasPoolReference();
    rangeText.textContent = visible.points[0].date + ' 至 ' + visible.points.at(-1).date +
      ' · ' + visible.points.length + ' 日';
    resetRange.disabled = phaseChoice === 'all' && zoom === null;
    refreshSelection();
  }

  function changeFilters() {
    const state = new FormData(form);
    weight = state.get('weight');
    sorting = state.get('sorting');
    tradeFraction = state.get('tradeFraction');
    portfolio = [state.get('strategy'), state.get('q')];
    const phase = state.get('phase');
    if (phase !== phaseChoice) {
      phaseChoice = phase;
      zoom = null;
      selection = null;
      pinned = false;
    }
    const title = '中证 2000 · 做 T ' + tradeFraction + '% · 全程累计' + returnLabel() + ' · ' + feeLabel();
    get('compare-heading').textContent = title;
    panels.returns.svg.setAttribute('aria-label', title);
    for (const button of optionButtons) button.setAttribute('aria-pressed', String(button.dataset.returnView === view));
    timeline = timelineFor();
    updateScoreRows();
    drawAll();
  }

  __EXPANSION_HELPERS__

  try {
    const bytes = Uint8Array.from(atob(get('csi2000-market-data').textContent), letter => letter.charCodeAt(0));
    data = await new Response(new Blob([bytes]).stream().pipeThrough(new DecompressionStream('gzip'))).json();
    for (const option of form.elements.tradeFraction.options) {
      option.disabled = !data.tradeFractions.includes(Number(option.value));
    }
  } catch {
    get('fill-status').hidden = false;
    get('fill-status').textContent = '回放数据加载失败。请重新打开展示，或查看研究报告。';
    return;
  }

  form.addEventListener('submit', event => event.preventDefault());
  form.addEventListener('change', changeFilters);
  signalMode.addEventListener('change', drawAll);
  optionButtons.forEach(button => button.addEventListener('click', () => {
    view = button.dataset.returnView;
    changeFilters();
  }));
  curveLegend.forEach(button => button.addEventListener('click', () => {
    const { curveKind, curveLane } = button.dataset;
    focusedLanes[curveKind] = curveLane === 'all' ? null : Number(curveLane);
    drawAll();
  }));
  changeFilters();
  let observed = '';
  function reflow() {
    const size = Object.values(panels).map(p => p.plot.clientWidth).join('/') + '/' + window.innerHeight;
    if (size === observed) return;
    observed = size;
    drawAll();
  }
  if (typeof ResizeObserver === 'function') {
    const observer = new ResizeObserver(reflow);
    for (const panel of Object.values(panels)) observer.observe(panel.plot);
  }
  window.addEventListener('resize', reflow);
})();
