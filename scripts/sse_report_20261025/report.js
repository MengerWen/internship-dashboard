(() => {
  "use strict";
  const DATA = JSON.parse(document.getElementById("report-data").textContent);
  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));
  const NS = "http://www.w3.org/2000/svg";
  const fmt = (n, d = 0) => Number(n).toLocaleString("en-US", {minimumFractionDigits: d, maximumFractionDigits: d});
  const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;"}[c]));
  const C = {teal: "#087b78", ochre: "#d29a3a", rust: "#b24f35", gray: "#a9b2ae", ink: "#243648", rule: "#ced3c9", soft: "#e2e4dc", card: "#fbfaf6", paper: "#f5f3eb", tealWash: "#e1eee9", rustWash: "#f5e5dd"};

  function svg(tag, attrs = {}, parent) {
    const el = document.createElementNS(NS, tag);
    for (const [k, v] of Object.entries(attrs)) if (v !== undefined && v !== null) el.setAttribute(k, v);
    if (parent) parent.appendChild(el);
    return el;
  }
  function text(parent, x, y, str, attrs = {}) {
    const t = svg("text", {x, y, class: "lbl", ...attrs}, parent);
    t.textContent = str;
    return t;
  }
  // Bar with a 4px rounded data end and a square baseline.
  function hbar(parent, x, y, w, h, fill) {
    const r = Math.min(4, w / 2, h / 2);
    if (w <= 0) return null;
    const d = `M${x},${y}H${x + w - r}Q${x + w},${y} ${x + w},${y + r}V${y + h - r}Q${x + w},${y + h} ${x + w - r},${y + h}H${x}Z`;
    return svg("path", {d, fill}, parent);
  }
  function onResize(fn) {
    let last = 0;
    const ro = new ResizeObserver((entries) => {
      const w = Math.round(entries[0].contentRect.width);
      if (w && w !== last) { last = w; fn(w); }
    });
    return ro;
  }

  /* ---------- tooltip ---------- */
  const tip = $("#tip");
  function showTip(html, x, y) {
    tip.innerHTML = html;
    tip.hidden = false;
    const r = tip.getBoundingClientRect();
    let left = x + 14, top = y + 14;
    if (left + r.width > window.innerWidth - 8) left = x - r.width - 14;
    if (top + r.height > window.innerHeight - 8) top = y - r.height - 14;
    tip.style.left = Math.max(8, left) + "px";
    tip.style.top = Math.max(8, top) + "px";
  }
  function hideTip() { tip.hidden = true; }

  /* ---------- glossary popover ---------- */
  const GLOSSARY = {
    szse: ["深市逐笔委托", "深交所在每笔报单进入系统时就发布一条委托记录，包含价格、数量、方向和申报类型；之后的成交和撤单都能对回这笔委托。项目的因子最初就是在这种数据上开发和验收的。"],
    atc: ["A / T / C", "本页对沪市公开消息的简写：A 是新增挂单（订单进入盘口），T 是成交，C 是撤单。沪市不在报单进场时单独发布委托。"],
    logical: ["逻辑订单", "由若干条公开消息拼回的“同一笔订单”。例如先成交 600 股、再挂出 400 股，是一笔 1,000 股的订单，不是两笔。"],
    public: ["公开口径（public v5）", "只用沪市公开行情能核实的事实来定义因子输入，第 5 次修订版。它规定价格、数量、时间等怎样从公开消息中取值，但不声称恢复了原始报单。"],
    qv: ["可见数量 Qv", "订单在公开行情里能看到的总量：刚进场时的成交量 + 公开挂出的余量。没有公布就被系统撤掉的剩余部分看不到，不计入。"],
    pxact: ["px / act 两个版本", "对“立即成交的订单”，部分响应类因子有两种算法并行保留：px 看公开成交价的变化，act 看订单实际可成交程度的变化。两者分别计算、分别定参。"],
    union: ["综合行为强度（union）", "把 57 个行为成员的得分合成一个综合分，衡量订单行为的总体强度。它是行为强度的聚合，不是经过校准的“算法交易概率”。"],
    replay: ["回放", "按时间顺序把逐笔消息重新执行一遍，重建每一时刻的盘口（各价位的挂单量）和每笔订单的状态。"],
    ledger: ["独立账本", "只用 Python 标准库另写的一套计算，从原始字段直接算出动作前后盘口、订单生命周期数量等答案，用来对照正式程序。它不调用正式程序的任何结果。"],
    clock: ["消息时钟 Q_equity", "用“中间隔了多少条消息”而不是秒数衡量两个动作的远近。深市可用交易所的原始序号；沪市只能用同一通道内公开的 A 股消息重新排一条序列，称为 Q_equity。"],
    scaled: ["截面尺度误差", "两种算法的差 |H − S|，除以该因子在全市场股票之间的离散程度（四分位距 ÷ 1.349，正态时约等于一个标准差）。0.01 表示差异约为股票间正常差异的 1%。图中取每列 2,888 只股票误差的 p99。"],
    calib: ["定参", "用数据估计因子公式里的尺度参数和门槛。只使用行情本身，不读收益和 IC，避免按预测效果挑参数。"],
    kernel: ["核尺度 θ", "因子里常用权重 exp(−距离 / θ)：距离越远权重越小。θ 取样本中距离的中位数除以 ln2，所以在中位距离处权重正好是 0.5。中位数按“股票日 → 日期 → 全期”三层计算，避免活跃股票和活跃日期主导结果。"],
    z12: ["Z12", "一组深度尺度参数，只服务 f97、f129、f130 这 6 列。这 6 列不在本次 340 列范围内，所以本次不估 Z12。"],
    p75: ["P75 日", "在 13 个已认证交易日中，按当天事件条数排序取第 75 百分位的那一天（2026-06-30），用作偏重的代表日来测耗时。它不是 601 个交易日耗时的 P75。"],
    f26: ["f26 主动成交簇", "把同一方向、时间间隔和消息间隔都足够近的主动成交连成“簇”，按簇的长度、连接的时间质量、数量稳定性和吃掉的深度打分。f27 使用同一套簇。"],
    stockday: ["股票日", "一只股票的一个交易日，是验收和计算的基本单位。"],
    window: ["计算窗口", "本项目的因子只看开盘后 09:30 至 09:35（不含 09:35）的正常连续竞价，即 open 5 min。"],
    guard: ["guard", "项目在服务器上运行计算的受控入口：限定 16 核、100 GiB 内存、不使用 swap，并记录从启动到退出的完整耗时和资源。"],
    engineering: ["工程试算", "用一个代表日把完整定参流程跑一遍，检查程序、资源和存储能否正确复原。它产出的参数只用于检查流程，不作为正式参数。"],
    percentile: ["P05 / P50 / P75 / P99", "分位数。P50 是中位数；P75 表示 75% 的样本不超过它；P05、P99 分别接近分布的低端和高端。"],
    f40: ["F40 配对门", "判断“新单是否在替换某笔旧单”的一组门槛，分四个阶段依次估计：连续片段间隔 → 首个合法锚点 → 配对代价 → 一次精确匹配。"],
    dm: ["dm03 / dm04", "两个因子（买卖共 4 列），按既有决定在沪市停用，不生成沪市版本。"],
    corrected: ["深市 344 列（corrected-344）", "深市当前正式使用的修正版 344 列因子及其八组结构参数，是本次沪市定参的方法基准和对照范围。"],
  };
  const pop = $("#term-pop");
  let popFor = null;
  function closePop(returnFocus) {
    if (!popFor) return;
    popFor.setAttribute("aria-expanded", "false");
    if (returnFocus) popFor.focus();
    popFor = null;
    pop.hidden = true;
  }
  function openPop(btn) {
    const entry = GLOSSARY[btn.dataset.term];
    if (!entry) return;
    if (popFor === btn) { closePop(false); return; }
    closePop(false);
    popFor = btn;
    btn.setAttribute("aria-expanded", "true");
    $(".pop-title", pop).textContent = entry[0];
    $(".pop-body", pop).textContent = entry[1];
    pop.hidden = false;
    const b = btn.getBoundingClientRect();
    const p = pop.getBoundingClientRect();
    let left = Math.min(Math.max(16, b.left), window.innerWidth - p.width - 16);
    let top = b.bottom + 8;
    if (top + p.height > window.innerHeight - 12) top = Math.max(12, b.top - p.height - 8);
    pop.style.left = left + "px";
    pop.style.top = top + "px";
  }
  $$(".term").forEach((btn) => {
    btn.setAttribute("aria-expanded", "false");
    btn.setAttribute("aria-controls", "term-pop");
    btn.addEventListener("click", (e) => { e.stopPropagation(); openPop(btn); });
  });
  $(".pop-close", pop).addEventListener("click", () => closePop(true));
  pop.addEventListener("click", (e) => e.stopPropagation());
  document.addEventListener("click", () => closePop(false));
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") { closePop(true); hideTip(); } });
  window.addEventListener("scroll", () => { closePop(false); hideTip(); }, {passive: true});

  /* ---------- order demo ---------- */
  const BASE_BOOK = [["卖二", 10.05, 400], ["卖一", 10.00, 600], ["买一", 9.99, 500], ["买二", 9.97, 800]];
  const SCENARIOS = [
    {
      tab: "先成交，再挂余量",
      origin: "买入 · 限价 10.03 元 · 1,000 股",
      book0: BASE_BOOK,
      steps: [
        {msg: ["T", "成交 10.00 × 600 股"], book: [["卖二", null, null, "blank"], ["卖一", 10.05, 400], ["买一", 9.99, 500], ["买二", 9.97, 800]], gone: [10.00],
          note: "订单先吃掉卖一的 600 股，行情发布一条成交 T。此时还看不出这笔订单一共有多少股。"},
        {msg: ["A", "挂单 买 10.03 × 400 股"], book: [["卖二", null, null, "blank"], ["卖一", 10.05, 400], ["买一", 10.03, 400, "chg"], ["买二", 9.99, 500]],
          note: "剩下的 400 股挂进盘口，行情再发布一条挂单 A。它是同一笔订单的余量，不是一笔新订单。"},
      ],
      start: "订单刚提交，行情里还没有任何记录。",
      known: "这是一笔订单：可见数量 Qv = 600 + 400 = 1,000 股；入场时刻在第一笔成交之前；价格取挂出价 10.03。",
      unknown: "原始订单类型：不同的申报方式可能打出完全相同的两条消息。",
    },
    {
      tab: "直接挂单",
      origin: "买入 · 限价 9.99 元 · 300 股",
      book0: BASE_BOOK,
      steps: [
        {msg: ["A", "挂单 买 9.99 × 300 股"], book: [["卖二", 10.05, 400], ["卖一", 10.00, 600], ["买一", 9.99, 800, "chg"], ["买二", 9.97, 800]],
          note: "订单没有立即成交，直接挂进买一，行情发布一条挂单 A，买一从 500 股变成 800 股。"},
        {msg: ["C", "撤单 买 9.99 × 300 股"], book: [["卖二", 10.05, 400], ["卖一", 10.00, 600], ["买一", 9.99, 500, "chg"], ["买二", 9.97, 800]],
          note: "之后这笔订单被撤销，行情发布撤单 C，买一恢复为 500 股。"},
      ],
      start: "订单刚提交，行情里还没有任何记录。",
      known: "挂单价格 9.99、数量 300 股、挂单时刻、在盘口里存续了多久、后来被撤销。",
      unknown: "原始订单类型：同样的记录也可能来自其他会转成挂单的申报方式。",
    },
    {
      tab: "只有成交",
      origin: "两种可能（行情无法区分）：限价 ≥ 10.05 元买入 1,000 股；或市价买入 1,200 股，成交不了的 200 股被系统撤销",
      book0: BASE_BOOK,
      steps: [
        {msg: ["T", "成交 10.00 × 600 股"], book: [["卖二", null, null, "blank"], ["卖一", 10.05, 400], ["买一", 9.99, 500], ["买二", 9.97, 800]],
          note: "订单先吃掉卖一的 600 股。"},
        {msg: ["T", "成交 10.05 × 400 股"], book: [["卖二", null, null, "blank"], ["卖一", null, null, "blank"], ["买一", 9.99, 500], ["买二", 9.97, 800]],
          note: "再吃掉卖二的 400 股。之后这笔订单在行情里就结束了：没有挂单，也没有撤单。"},
      ],
      start: "订单刚提交，行情里还没有任何记录。",
      known: "订单身份、买卖方向、两笔成交明细和首次生效的位置；可见成交 1,000 股；价格代理取最深成交价 10.05。",
      unknown: "原始限价（10.05 以上任何价格都可能）、是不是市价单、有没有没公布就被撤掉的剩余数量。",
    },
    {
      tab: "完全不可见",
      origin: "买入 · 市价（即时成交、剩余撤销） · 300 股，但此刻卖方没有挂单",
      book0: [["卖二", null, null, "blank"], ["卖一", null, null, "blank"], ["买一", 10.00, 9600], ["买二", 9.99, 500]],
      steps: [
        {msg: null, book: [["卖二", null, null, "blank"], ["卖一", null, null, "blank"], ["买一", 10.00, 9600], ["买二", 9.99, 500]],
          note: "订单一股也成交不了，又不允许挂单，被系统直接撤销。行情里可能不留下任何记录。"},
      ],
      start: "订单刚提交。",
      known: "没有。行情里找不到这笔订单。",
      unknown: "这笔订单是否存在、方向和数量。我们不会凭空补造它。",
    },
  ];
  const demo = $("#order-demo");
  if (demo) {
    const tabs = $(".demo-tabs", demo);
    const slot = (n) => $(`[data-slot="${n}"]`, demo);
    let sc = 0, step = 0;
    SCENARIOS.forEach((s, i) => {
      const b = document.createElement("button");
      b.type = "button";
      b.setAttribute("role", "tab");
      b.id = "demo-tab-" + i;
      b.textContent = s.tab;
      b.addEventListener("click", () => { sc = i; step = 0; render(); });
      b.addEventListener("keydown", (e) => {
        if (e.key !== "ArrowRight" && e.key !== "ArrowLeft") return;
        e.preventDefault();
        sc = (sc + (e.key === "ArrowRight" ? 1 : SCENARIOS.length - 1)) % SCENARIOS.length;
        step = 0; render(); tabs.children[sc].focus();
      });
      tabs.appendChild(b);
    });
    $(".demo-body", demo).setAttribute("role", "tabpanel");
    const prev = $('[data-act="prev"]', demo), next = $('[data-act="next"]', demo);
    prev.addEventListener("click", () => { if (step > 0) { step--; render(); } });
    next.addEventListener("click", () => { if (step < SCENARIOS[sc].steps.length) { step++; render(); } });
    function bookRows(rows, prevPrices) {
      return rows.map(([lvl, price, qty, flag]) => {
        const side = lvl.startsWith("卖") ? "ask" : "bid";
        if (price === null) return `<tr class="${side} blank"><td>${lvl}</td><td class="r">—</td><td class="r">—</td></tr>`;
        return `<tr class="${side} ${flag || ""}"><td>${lvl}</td><td class="r">${price.toFixed(2)}</td><td class="r">${fmt(qty)}</td></tr>`;
      }).join("");
    }
    function render() {
      const s = SCENARIOS[sc];
      [...tabs.children].forEach((b, i) => { b.setAttribute("aria-selected", i === sc ? "true" : "false"); b.tabIndex = i === sc ? 0 : -1; });
      $(".demo-body", demo).setAttribute("aria-labelledby", "demo-tab-" + sc);
      slot("origin").textContent = s.origin;
      const items = s.steps.map((st, i) => {
        const shown = i < step;
        if (!st.msg) return `<li class="empty ${shown ? "" : "pending"}">${shown ? "（没有任何公开消息）" : "等待播放"}</li>`;
        const cls = shown ? (i === step - 1 ? "fresh" : "") : "pending";
        return `<li class="${cls}"><span class="k ${st.msg[0]}" aria-hidden="true">${st.msg[0]}</span><span class="v">${shown ? esc(st.msg[1]) : "等待播放"}</span></li>`;
      });
      slot("msgs").innerHTML = items.join("");
      const book = step === 0 ? s.book0 : s.steps[step - 1].book;
      slot("book").innerHTML = bookRows(book);
      slot("note").textContent = step === 0 ? s.start + " 点击“播放下一条消息”。" : s.steps[step - 1].note;
      const done = step === s.steps.length;
      slot("known").textContent = done ? s.known : "播放完全部消息后显示。";
      slot("unknown").textContent = done ? s.unknown : "播放完全部消息后显示。";
      slot("count").textContent = `${step} / ${s.steps.length}`;
      prev.disabled = step === 0;
      next.disabled = done;
      next.textContent = done ? "已播放完" : "播放下一条消息";
    }
    render();
  }

  /* ---------- 100% stacked bars ---------- */
  function stacked(el, parts, totalLabel) {
    const host = document.createElement("div");
    const legend = document.createElement("div");
    legend.className = "mix-legend";
    el.append(host, legend);
    const total = parts.reduce((a, p) => a + p.value, 0);
    legend.innerHTML = parts.map((p) => `<span><i style="background:${p.color}"></i>${esc(p.label)} <em>${fmt(p.value)} · ${(p.value / total * 100).toFixed(1)}%</em></span>`).join("");
    onResize((w) => {
      host.innerHTML = "";
      const h = 34, top = 24, gap = 2;
      const s = svg("svg", {viewBox: `0 0 ${w} ${top + h + 4}`, role: "img", "aria-label": parts.map((p) => `${p.label} ${(p.value / total * 100).toFixed(1)}%`).join("，")}, host);
      let x = 0;
      const usable = w - gap * (parts.length - 1);
      parts.forEach((p, i) => {
        const pw = Math.max(3, usable * p.value / total);
        const r = svg("rect", {x, y: top, width: pw, height: h, fill: p.color}, s);
        const pct = (p.value / total * 100).toFixed(1) + "%";
        const lx = i === parts.length - 1 ? x + pw : x;
        const anchor = i === parts.length - 1 ? "end" : "start";
        if (pw > 46 || i !== 1) text(s, lx, top - 8, pct, {class: "lbl strong big", "text-anchor": anchor});
        else text(s, x + pw / 2, top - 8, pct, {class: "lbl strong big", "text-anchor": "middle"});
        r.addEventListener("pointermove", (e) => showTip(`<b>${esc(p.label)}</b>${fmt(p.value)}（${pct}）`, e.clientX, e.clientY));
        r.addEventListener("pointerleave", hideTip);
        x += pw + gap;
      });
      if (totalLabel) svg("title", {}, s).textContent = totalLabel;
    }).observe(host);
  }
  const mix = $('[data-chart="mix"]');
  if (mix) stacked(mix, [
    {label: "直接挂单", value: 4483212, color: C.teal},
    {label: "先成交，再挂余量", value: 105881, color: C.ochre},
    {label: "只有成交", value: 2025856, color: C.rust},
  ]);
  const cons = $('[data-chart="conservation"]');
  if (cons) stacked(cons, [
    {label: "成交", value: 8420838682, color: C.teal},
    {label: "撤单", value: 3183029451, color: C.ochre},
    {label: "09:35 时仍挂着的余量", value: 2652244034, color: C.rust},
  ], "合计 14,256,112,167 股");

  /* ---------- tables: days, ledger, groups ---------- */
  const daysBody = $('[data-table="days"]');
  if (daysBody) {
    const rows = DATA.days.map(([d, p, x, e]) => `<tr><td>${d}</td><td class="r">${fmt(p)}</td><td class="r">${x}</td><td class="r">${e}</td></tr>`);
    const t = DATA.days.reduce((a, r) => [a[0] + r[1], a[1] + r[2], a[2] + r[3]], [0, 0, 0]);
    rows.push(`<tr class="total"><td>合计</td><td class="r">${fmt(t[0])}</td><td class="r">${t[1]}</td><td class="r">${t[2]}</td></tr>`);
    daysBody.innerHTML = rows.join("");
  }
  const ledgerBody = $('[data-table="ledger"]');
  if (ledgerBody) {
    const rows = DATA.ledger.map(([k, n, d]) => `<tr><td>${esc(k)}</td><td class="r">${fmt(n)}</td><td class="r">${d}</td></tr>`);
    rows.push(`<tr class="total"><td>合计</td><td class="r">${fmt(DATA.ledger.reduce((a, r) => a + r[1], 0))}</td><td class="r">0</td></tr>`);
    ledgerBody.innerHTML = rows.join("");
  }
  const groupsBody = $('[data-table="groups"]');
  if (groupsBody) {
    groupsBody.innerHTML = DATA.groups.map((g) => `<tr><td><b>${esc(g.code)}</b>${esc(g.name)}</td><td>${esc(g.use)}</td><td>${esc(g.how)}</td><td>${esc(g.note)}</td></tr>`).join("");
  }

  /* ---------- kernels ---------- */
  const KERNELS = [
    ["θ_wall", "时间", "两个动作相隔几秒算“近”", "沪市独立估计"],
    ["θ_events", "消息数", "两个动作之间隔几条消息算“近”", "沪市独立估计"],
    ["θ_qty", "数量", "新旧订单数量相差多少算“相近”", "沪市独立估计"],
    ["θ_price", "价格", "新旧报价相差几个价位算“近”", "沪市独立估计"],
    ["θ_bbo", "离最优报价的距离", "报价离最优价几个价位算“靠近盘口”", "沪市独立估计"],
    ["θ_mkt", "离立即成交的距离", "公开软分支订单首动作前，挂出价距对手可执行前沿几档", "每订单一次 · 独立估计"],
  ];
  const kHost = $('[data-slot="kernels"]');
  if (kHost) kHost.innerHTML = KERNELS.map(([sym, what, use, how], i) => `<div class="kernel${i === 5 ? " independent" : ""}"><span class="sym">${sym}</span><span class="what">${what}</span><span class="use">${use}</span><span class="how">${how}${i === 5 ? ' · <a href="#sixth">取样</a>' : ""}</span></div>`).join("");

  /* ---------- columns reconciliation ---------- */
  const recon = $('[data-chart="columns"]');
  if (recon) recon.innerHTML = `
    <div class="eq"><div class="box"><b>344</b>深市当前正式列</div><span>−</span><div class="box minus"><b>4</b>dm03/dm04 沪市停用</div><span>=</span><div class="box res"><b>340</b>本次定参范围</div></div>
    <div class="eq"><div class="box"><b>352</b>沪市公开口径可算的列</div><span>−</span><div class="box minus"><b>12</b>Z12 专用 6 列 + 结构恒零 6 列</div><span>=</span><div class="box res"><b>340</b>同一组列</div></div>`;

  /* ---------- clock error dot histogram ---------- */
  const clockEl = $('[data-chart="clock"]');
  const SIDE = {buy: "买侧", sell: "卖侧"};
  function colLabel(col) {
    const parts = col.split("__");
    const base = parts[0];
    const side = parts.map((p) => p.match(/^side_(buy|sell)$/)).find(Boolean);
    const extra = parts.slice(1).filter((p) => !/^side_|^den_all_orders$|^win_0930_0935$/.test(p));
    const plain = DATA.factorNames[base];
    return {base, side: side ? SIDE[side[1]] : "", extra: extra.join(" · "), plain};
  }
  const errors = DATA.errors.map(([col, p99, max, rho, changed, zero]) => ({col, p99, max, rho, changed, zero, ...colLabel(col)}));
  function mechFor(e) {
    const key = e.base + "__side_" + (e.side === "买侧" ? "buy" : "sell");
    return DATA.mechanisms[key];
  }
  function tipHtml(e) {
    const name = e.plain ? `${esc(e.plain)} · ${e.side}` : `${esc(e.base)}${e.side ? " · " + e.side : ""}`;
    const m = mechFor(e);
    return `<b>${name}</b>${e.extra ? `<span class="m">${esc(e.extra)}</span><br>` : ""}p99 误差 ${e.p99 === 0 ? "0" : e.p99.toPrecision(3)} · 最大 ${e.max.toPrecision(3)}<br>秩相关 ${e.rho === null ? "—" : e.rho.toFixed(8)} · 变化股票 ${fmt(e.changed)} / 2,888${m ? `<br><span class="m">${esc(m.replace(/^【[^】]+】/, ""))}</span>` : ""}`;
  }
  if (clockEl) {
    const plotted = errors.filter((e) => !e.zero);
    const zeros = plotted.filter((e) => e.p99 === 0);
    const pos = plotted.filter((e) => e.p99 > 0);
    const lo = -4, hi = -1, binW = 0.1;
    const nb = Math.round((hi - lo) / binW);
    const bins = Array.from({length: nb}, () => []);
    pos.forEach((e) => { const i = Math.min(nb - 1, Math.max(0, Math.floor((Math.log10(e.p99) - lo) / binW))); bins[i].push(e); });
    bins.forEach((b) => b.sort((a, c) => a.p99 - c.p99));
    let dots = [];
    const search = $("#col-search"), hint = $(".search-hint");
    let query = "";
    function matches(e) { return query && (e.col.toLowerCase().includes(query) || (e.plain || "").includes(query)); }
    function draw(w) {
      clockEl.innerHTML = "";
      dots = [];
      const narrow = w < 560;
      const zeroW = narrow ? 64 : 104, padL = zeroW + 26, padR = 14, axisH = 40;
      const plotW = w - padL - padR;
      const bw = plotW / nb;
      const r = narrow ? 2.6 : 3.4, pitch = r * 2 + 2;
      const perRow = Math.max(1, Math.floor((bw - 1) / pitch));
      const zeroPer = Math.max(1, Math.floor((zeroW - 6) / pitch));
      const maxH = Math.max(...bins.map((b) => Math.ceil(b.length / perRow)), Math.ceil(zeros.length / zeroPer));
      const plotH = Math.max(120, maxH * pitch + 24);
      const s = svg("svg", {viewBox: `0 0 ${w} ${plotH + axisH}`, role: "img", "aria-label": "352 列 p99 截面尺度误差分布：p99 为 0 的 74 列，10⁻⁴ 至 10⁻³ 的 70 列，10⁻³ 至 10⁻² 的 159 列，10⁻² 至 10⁻¹ 的 43 列，超过 0.1 的 0 列"}, clockEl);
      const base = plotH;
      const xOf = (lg) => padL + (lg - lo) / (hi - lo) * plotW;
      // decade bands + grid
      [-4, -3, -2, -1].forEach((d) => {
        svg("line", {x1: xOf(d), x2: xOf(d), y1: 6, y2: base, stroke: C.soft}, s);
        const t = text(s, xOf(d), base + 18, "", {"text-anchor": d === -1 ? "end" : "middle", class: "lbl"});
        t.textContent = ["0.0001", "0.001", "0.01", "0.1"][d + 4];
      });
      svg("line", {x1: padL, x2: w - padR, y1: base + 0.5, y2: base + 0.5, stroke: C.rule}, s);
      svg("line", {x1: 0, x2: zeroW, y1: base + 0.5, y2: base + 0.5, stroke: C.rule}, s);
      text(s, zeroW / 2, base + 18, "p99 = 0", {"text-anchor": "middle"});
      text(s, padL + plotW / 2, base + 36, "p99 截面尺度误差（对数刻度）", {"text-anchor": "middle"});
      const place = (e, cx, cy) => {
        const hit = matches(e);
        const c = svg("circle", {cx, cy, r: hit ? r + 1.4 : r, fill: query && !hit ? C.gray : C.teal, "fill-opacity": query && !hit ? 0.45 : 1, stroke: hit ? C.rust : C.card, "stroke-width": hit ? 2 : 1}, s);
        dots.push({e, cx, cy, c});
      };
      zeros.forEach((e, i) => place(e, 4 + r + (i % zeroPer) * pitch, base - r - 2 - Math.floor(i / zeroPer) * pitch));
      bins.forEach((b, bi) => b.forEach((e, i) => {
        const col = i % perRow, row = Math.floor(i / perRow);
        const x0 = padL + bi * bw + (bw - perRow * pitch) / 2 + r + 1;
        place(e, x0 + col * pitch, base - r - 2 - row * pitch);
      }));
      // label the worst column directly
      const worst = dots.reduce((a, d) => (d.e.p99 > a.e.p99 ? d : a));
      const ly = Math.min(worst.cy - 30, 18);
      svg("line", {x1: worst.cx, x2: worst.cx, y1: worst.cy - r - 2, y2: ly + 5, stroke: C.ink}, s);
      text(s, worst.cx + 3, ly, `最差：f43 买侧 ${worst.e.p99.toFixed(3)}`, {"text-anchor": "end", class: "lbl strong"});
      // nearest-dot hover layer
      const hitLayer = svg("rect", {x: 0, y: 0, width: w, height: plotH, fill: "transparent"}, s);
      let active = null;
      hitLayer.addEventListener("pointermove", (ev) => {
        const pt = s.getBoundingClientRect();
        const sx = (ev.clientX - pt.left) * (w / pt.width), sy = (ev.clientY - pt.top) * ((plotH + axisH) / pt.height);
        let best = null, bd = 18 * 18;
        for (const d of dots) { const dd = (d.cx - sx) ** 2 + (d.cy - sy) ** 2; if (dd < bd) { bd = dd; best = d; } }
        if (active && active !== best) active.c.setAttribute("stroke", matches(active.e) ? C.rust : C.card), active.c.setAttribute("stroke-width", matches(active.e) ? 2 : 1);
        active = best;
        if (best) { best.c.setAttribute("stroke", C.ink); best.c.setAttribute("stroke-width", 2); showTip(tipHtml(best.e), ev.clientX, ev.clientY); }
        else hideTip();
      });
      hitLayer.addEventListener("pointerleave", () => { hideTip(); if (active) { active.c.setAttribute("stroke", matches(active.e) ? C.rust : C.card); active.c.setAttribute("stroke-width", matches(active.e) ? 2 : 1); active = null; } });
    }
    let lastW = 0;
    onResize((w) => { lastW = w; draw(w); }).observe(clockEl);
    search.addEventListener("input", () => {
      query = search.value.trim().toLowerCase();
      const n = query ? plotted.filter(matches).length : 0;
      hint.textContent = query ? (n ? `匹配 ${n} 列，已用红圈标出` : "没有匹配的列（6 个结构恒零列不在图中）") : "";
      if (lastW) draw(lastW);
    });
    const binsEl = $('[data-slot="bins"]');
    const cnt = (f) => plotted.filter(f).length;
    binsEl.innerHTML = [
      ["p99 = 0", cnt((e) => e.p99 === 0)], ["10⁻⁴ ～ 10⁻³", cnt((e) => e.p99 > 1e-4 && e.p99 <= 1e-3)], ["10⁻³ ～ 10⁻²", cnt((e) => e.p99 > 1e-3 && e.p99 <= 1e-2)],
      ["10⁻² ～ 10⁻¹", cnt((e) => e.p99 > 1e-2 && e.p99 <= 1e-1)], ["> 0.1", cnt((e) => e.p99 > 0.1)],
    ].map(([k, v]) => `<div><b>${v}</b>${k}</div>`).join("");
    const worstEl = $('[data-slot="worst"]');
    const top = [...plotted].sort((a, b) => b.p99 - a.p99).slice(0, 8);
    worstEl.innerHTML = `<h4>p99 误差最大的 8 列</h4><ol>${top.map((e) => {
      const m = mechFor(e) || "";
      const tag = (m.match(/^【([^】]+)】/) || [])[1];
      return `<li><span>${esc(e.plain || e.base)} · ${e.side}</span><span class="v">${e.p99.toFixed(4)}</span><span class="why">${tag ? `<i>${tag}</i> ` : ""}${esc(m.replace(/^【[^】]+】/, ""))}</span></li>`;
    }).join("")}</ol><p class="fig-note">原因说明中，“事实”指已由代码路径确认，“推测”指尚未做逐项消融拆分。</p>`;
    const toggle = $('details[data-table-toggle="clock"]');
    toggle.addEventListener("toggle", () => {
      const table = $('[data-table="clock"]');
      if (!toggle.open || table.dataset.ready) return;
      const sorted = [...errors].sort((a, b) => (b.p99 ?? -1) - (a.p99 ?? -1));
      table.innerHTML = `<thead><tr><th scope="col">列</th><th scope="col">方向</th><th scope="col" class="r">变化股票</th><th scope="col" class="r">p99 误差</th><th scope="col" class="r">最大误差</th><th scope="col" class="r">秩相关</th></tr></thead><tbody>${sorted.map((e) => `<tr><td><code>${esc(e.base)}</code>${e.extra ? `<br><code>${esc(e.extra)}</code>` : ""}</td><td>${e.side}</td><td class="r">${fmt(e.changed)}</td><td class="r">${e.zero ? "结构恒零" : e.p99.toPrecision(3)}</td><td class="r">${e.zero ? "—" : e.max.toPrecision(3)}</td><td class="r">${e.rho === null ? "—" : e.rho.toFixed(8)}</td></tr>`).join("")}</tbody>`;
      table.dataset.ready = "1";
    });
  }

  /* ---------- grouped horizontal bars (priority fix) ---------- */
  const prio = $('[data-chart="priority"]');
  if (prio) {
    const rows = [["买侧", 85.9072, 25.7271], ["卖侧", 88.6427, 25.6233]];
    const legend = document.createElement("div");
    legend.className = "mix-legend";
    legend.innerHTML = `<span><i style="background:${C.gray}"></i>v4 修正前</span><span><i style="background:${C.teal}"></i>v5 修正后</span>`;
    const host = document.createElement("div");
    prio.append(host, legend);
    onResize((w) => {
      host.innerHTML = "";
      const padL = 52, padR = 70, bh = 18, gapIn = 4, gapOut = 22;
      const plotW = w - padL - padR;
      const H = rows.length * (bh * 2 + gapIn + gapOut) + 24;
      const s = svg("svg", {viewBox: `0 0 ${w} ${H}`, role: "img", "aria-label": "排队优先度分量差异股票占比：买侧 85.9% 降到 25.7%，卖侧 88.6% 降到 25.6%"}, host);
      [0, 25, 50, 75, 100].forEach((v) => {
        const x = padL + plotW * v / 100;
        svg("line", {x1: x, x2: x, y1: 0, y2: H - 22, stroke: C.soft}, s);
        text(s, x, H - 6, v + "%", {"text-anchor": "middle"});
      });
      rows.forEach(([lab, a, b], i) => {
        const y = i * (bh * 2 + gapIn + gapOut) + 6;
        text(s, 0, y + bh + 4, lab, {class: "lbl strong big"});
        hbar(s, padL, y, plotW * a / 100, bh, C.gray);
        text(s, padL + plotW * a / 100 + 6, y + bh - 4, a.toFixed(1) + "%", {class: "lbl"});
        hbar(s, padL, y + bh + gapIn, plotW * b / 100, bh, C.teal);
        text(s, padL + plotW * b / 100 + 6, y + bh * 2 + gapIn - 4, b.toFixed(1) + "%", {class: "lbl strong"});
      });
    }).observe(host);
  }

  /* ---------- speed bars ---------- */
  const speed = $('[data-chart="speed"]');
  if (speed) {
    const rows = [["10-24 首版", "db6cdd45", 509.217, C.gray], ["10-25 上午", "c56482f8", 172.818, C.gray], ["10-25 独立核", "5820e273", DATA.currentResearch.p75_command_seconds, C.teal]];
    onResize((w) => {
      speed.innerHTML = "";
      const padL = 96, padR = 56, bh = 22, gap = 18, top = 26;
      const plotW = w - padL - padR, max = 540;
      const H = top + rows.length * (bh + gap) + 22;
      const s = svg("svg", {viewBox: `0 0 ${w} ${H}`, role: "img", "aria-label": "单日工程命令：509.2 秒、172.8 秒、82.01 秒；最新方法另有 P05 收尾复核 8.53 秒；历史目标 60 秒已停止冲刺"}, speed);
      const xOf = (v) => padL + plotW * v / max;
      [0, 100, 200, 300, 400, 500].forEach((v) => {
        svg("line", {x1: xOf(v), x2: xOf(v), y1: top - 6, y2: H - 22, stroke: C.soft}, s);
        text(s, xOf(v), H - 6, String(v), {"text-anchor": "middle"});
      });
      rows.forEach(([lab, sha, v, col], i) => {
        const y = top + i * (bh + gap);
        text(s, 0, y + 11, lab, {class: "lbl strong"});
        text(s, 0, y + 25, sha, {class: "lbl"});
        hbar(s, padL, y, xOf(v) - padL, bh, col);
        text(s, xOf(v) + 6, y + 16, v.toFixed(1), {class: i === 2 ? "lbl strong big" : "lbl big"});
      });
      svg("line", {x1: xOf(60), x2: xOf(60), y1: top - 14, y2: H - 22, stroke: C.rust, "stroke-width": 2}, s);
      text(s, xOf(60) + 5, top - 10, "历史目标 60 秒", {class: "lbl strong", fill: C.rust, style: `fill:${C.rust}`});
    }).observe(speed);
  }

  /* ---------- f26 ---------- */
  const f26 = $("#f26");
  if (f26) {
    const gateEl = $('[data-chart="gate"]', f26), tlEl = $('[data-chart="timeline"]', f26), result = $('[data-slot="f26-result"]', f26);
    let axis = "S", wGate = 0, wTl = 0;
    const T0 = 33 * 60 + 10, T1 = 35 * 60 + 12, CUT = 35 * 60, H = 8.969206;
    const A_END = 33 * 60 + 31.30, B_START = A_END + 7.63, B_END = 34 * 60 + 57.94;
    const tfmt = (t) => `09:${String(Math.floor(t / 60)).padStart(2, "0")}:${(t % 60).toFixed(2).padStart(5, "0")}`;
    function drawGate(w) {
      gateEl.innerHTML = "";
      const lo = 114050, hi = 114290, padL = 6, padR = 6, H0 = 100, narrow = w < 560;
      const xOf = (v) => padL + (v - lo) / (hi - lo) * (w - padL - padR);
      const s = svg("svg", {viewBox: `0 0 ${w} ${H0}`, role: "img", "aria-label": axis === "S" ? "原始消息轴：消息间隔 114,216 条，超过门槛 114,141，不连接" : "公开消息轴：消息间隔 114,125 条，不超过门槛 114,141，连成一簇"}, gateEl);
      const thr = 114141.45, y = 50;
      text(s, padL, 14, narrow ? "← 连成一簇" : "← 不超过门槛：连成一簇", {class: "lbl", style: `fill:${C.teal}`});
      text(s, w - padR, 14, narrow ? "不连 →" : "超过门槛：不连 →", {"text-anchor": "end", class: "lbl"});
      svg("rect", {x: xOf(lo), y: y - 9, width: xOf(thr) - xOf(lo), height: 18, fill: C.tealWash}, s);
      svg("rect", {x: xOf(thr), y: y - 9, width: xOf(hi) - xOf(thr), height: 18, fill: "#ece9de"}, s);
      svg("line", {x1: xOf(thr), x2: xOf(thr), y1: y - 16, y2: y + 30, stroke: C.rust, "stroke-width": 2}, s);
      text(s, xOf(thr) + 5, y + 30, "门槛 114,141", {class: "lbl strong", style: `fill:${C.rust}`});
      const mark = (k, v, lab, ly, anchor, dx) => {
        const on = k === axis;
        svg("circle", {cx: xOf(v), cy: y, r: on ? 7 : 5, fill: on ? C.ink : C.card, stroke: on ? C.card : C.gray, "stroke-width": 2}, s);
        text(s, xOf(v) + dx, ly, lab, {"text-anchor": anchor, class: on ? "lbl strong" : "lbl"});
      };
      mark("S", 114216, "原始轴 114,216", y - 16, "middle", 0);
      mark("Q", 114125, "公开轴 114,125", y + 30, "end", -5);
    }
    function drawTl(w) {
      tlEl.innerHTML = "";
      const padL = 8, padR = 8, Hh = 150, narrow = w < 560;
      const xOf = (t) => padL + (t - T0) / (T1 - T0) * (w - padL - padR);
      const s = svg("svg", {viewBox: `0 0 ${w} ${Hh}`, role: "img", "aria-label": axis === "S" ? "原始消息轴：簇 A 在 09:33:31.30 结束，观察时间足够，计入；簇 B 在 09:34:57.94 结束，观察时间不足" : "公开消息轴：两簇合并为 548 单，在 09:34:57.94 结束，观察时间不足，整簇不计入"}, tlEl);
      const defs = svg("defs", {}, s);
      const g = svg("linearGradient", {id: "fade", x1: "0", x2: "1"}, defs);
      svg("stop", {offset: "0", "stop-color": C.teal, "stop-opacity": "0"}, g);
      svg("stop", {offset: "0.6", "stop-color": C.teal, "stop-opacity": "1"}, g);
      const g2 = svg("linearGradient", {id: "fade2", x1: "0", x2: "1"}, defs);
      svg("stop", {offset: "0", "stop-color": C.rust, "stop-opacity": "0"}, g2);
      svg("stop", {offset: "0.25", "stop-color": C.rust, "stop-opacity": "1"}, g2);
      const axisY = 118;
      [[33 * 60 + 15, "09:33:15"], [33 * 60 + 45, "09:33:45"], [34 * 60 + 15, "09:34:15"], [34 * 60 + 45, "09:34:45"]].forEach(([t, l]) => {
        svg("line", {x1: xOf(t), x2: xOf(t), y1: 10, y2: axisY, stroke: C.soft}, s);
        if (w > 520 || t % 60 === 15) text(s, xOf(t), axisY + 16, l, {"text-anchor": "middle"});
      });
      svg("line", {x1: padL, x2: w - padR, y1: axisY + 0.5, y2: axisY + 0.5, stroke: C.rule}, s);
      svg("rect", {x: xOf(CUT), y: 6, width: xOf(T1) - xOf(CUT), height: axisY - 6, fill: "#ece9de"}, s);
      svg("line", {x1: xOf(CUT), x2: xOf(CUT), y1: 2, y2: axisY + 4, stroke: C.ink, "stroke-width": 2}, s);
      text(s, xOf(CUT) - 4, axisY + 32, "09:35 截止", {"text-anchor": "end", class: "lbl strong"});
      const bar = (x0, x1, y, fill) => svg("rect", {x: xOf(x0), y, width: Math.max(2, xOf(x1) - xOf(x0)), height: 16, fill}, s);
      const win = (from, y, ok) => {
        const to = from + H;
        svg("line", {x1: xOf(from), x2: xOf(Math.min(to, T1)), y1: y + 8, y2: y + 8, stroke: ok ? C.teal : C.rust, "stroke-width": 2, "stroke-dasharray": "4 3"}, s);
        svg("line", {x1: xOf(Math.min(to, T1)), x2: xOf(Math.min(to, T1)), y1: y + 2, y2: y + 14, stroke: ok ? C.teal : C.rust, "stroke-width": 2}, s);
      };
      if (axis === "S") {
        bar(T0, A_END, 30, "url(#fade)");
        text(s, padL + 40, 24, "簇 A · 435 单", {class: "lbl strong"});
        win(A_END, 30, true);
        text(s, xOf(A_END + H) + 6, 43, narrow ? "足够 ✓" : "观察 8.97 秒：足够 ✓", {class: "lbl", style: `fill:${C.teal}`});
        bar(B_START, B_END, 72, C.gray);
        text(s, xOf(B_START), 66, narrow ? "簇 B · 113 单" : "簇 B · 113 单（相隔 7.63 秒，但消息间隔超门槛，单独成簇）", {class: "lbl"});
        win(B_END, 72, false);
        text(s, xOf(B_END) - 4, 104, "簇 B 结束太晚，观察不足，不计入", {"text-anchor": "end", class: "lbl"});
      } else {
        bar(T0, B_END, 50, "url(#fade2)");
        text(s, xOf(B_END) - 4, 44, "簇 A + 簇 B 合并 · 548 单", {"text-anchor": "end", class: "lbl strong"});
        win(B_END, 50, false);
        text(s, xOf(B_END) - 4, 84, narrow ? "只剩 2.06 秒，需要 8.97 秒 ✗" : `结束于 ${tfmt(B_END)}，只剩 2.06 秒，需要 8.97 秒 ✗`, {"text-anchor": "end", class: "lbl strong", style: `fill:${C.rust}`});
      }
      text(s, padL, 12, "起点略", {class: "lbl"});
    }
    function render() {
      $$(".seg button", f26).forEach((b) => b.setAttribute("aria-checked", b.dataset.axis === axis ? "true" : "false"));
      if (wGate) drawGate(wGate);
      if (wTl) drawTl(wTl);
      result.classList.toggle("bad", axis === "Q");
      result.innerHTML = axis === "S"
        ? "<b>原始消息轴：</b>关键边的消息间隔超过门槛，两簇分开。簇 A 结束得早，观察时间足够，计入因子（簇 B 结束太晚，不计入）；这只股票的 f26 为 <b>0.0015053</b>。"
        : "<b>公开消息轴：</b>消息间隔少了 91 条（约 0.08%），刚好落到门槛以内，两簇连成一簇。合并簇的分数仍为正（约 0.0057），但它结束得太晚，整簇失去观察资格；这只股票的 f26 变为 <b>0</b>。";
    }
    $$(".seg button", f26).forEach((b) => {
      b.addEventListener("click", () => { axis = b.dataset.axis; render(); });
      b.addEventListener("keydown", (e) => {
        if (!["ArrowLeft", "ArrowRight"].includes(e.key)) return;
        e.preventDefault(); axis = axis === "S" ? "Q" : "S"; render(); $(`.seg button[data-axis="${axis}"]`, f26).focus();
      });
    });
    onResize((w) => { wGate = w; drawGate(w); }).observe(gateEl);
    onResize((w) => { wTl = w; drawTl(w); }).observe(tlEl);
    render();
  }

  /* ---------- glossary list + sources ---------- */
  const gl = $('[data-slot="glossary"]');
  if (gl) gl.innerHTML = Object.values(GLOSSARY).map(([k, v]) => `<div><dt>${esc(k)}</dt><dd>${esc(v)}</dd></div>`).join("");
  const src = $('[data-slot="sources"]');
  if (src) src.innerHTML = DATA.sources.map(([label, url, rev]) => `<li><a href="${esc(url)}" target="_blank" rel="noopener">${esc(label)}</a>${rev ? `<code>${esc(rev)}</code>` : ""}</li>`).join("");

  /* ---------- scrollspy ---------- */
  const links = $$(".toc a");
  const targets = links.map((a) => document.getElementById(a.getAttribute("href").slice(1))).filter(Boolean);
  let current = null, queued = false;
  function spy() {
    queued = false;
    const line = Math.min(window.innerHeight * 0.35, 260);
    const cur = targets.filter((t) => t.getBoundingClientRect().top <= line).pop() || null;
    if (cur === current) return;
    current = cur;
    links.forEach((a) => {
      if (cur && a.getAttribute("href") === "#" + cur.id) {
        a.setAttribute("aria-current", "true");
        const row = a.parentElement;
        if (row.scrollWidth > row.clientWidth) row.scrollTo({left: a.offsetLeft - 16, behavior: "smooth"});
      } else a.removeAttribute("aria-current");
    });
  }
  window.addEventListener("scroll", () => { if (!queued) { queued = true; requestAnimationFrame(spy); } }, {passive: true});
  spy();
})();
