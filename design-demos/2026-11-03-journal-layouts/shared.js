/* 五种结构共用正式内容与阅读层；本文件不改变正式日志。 */
(function () {
  "use strict";
  window.JournalVariants = window.JournalVariants || {};
  const data = window.JOURNAL_DATA;
  const chainMap = new Map(data.chains.map(c => [c.id, c]));
  const trackMap = new Map(data.tracks.map(t => [t.id, t]));
  const dayMap = new Map(data.days.map(d => [d.date, d]));
  const names = {A: "方向总览", B: "按日日志", C: "链条工作台", D: "阶段章节", E: "月历日程"};
  const descriptions = {A: "先看全局，再沿研究方向深入", B: "按天直接阅读全部并行工作", C: "围绕一条链，读目标、过程与承接", D: "把研究过程读成连续的五个阶段", E: "用日期找工作，看清同一天的并行任务"};
  const esc = value => String(value ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
  const dayTasks = day => (day?.chains || []).filter(c => chainMap.has(c.id)).map(c => ({date: day.date, note: c.note, chain: chainMap.get(c.id), day, outcome: c.outcome || chainMap.get(c.id).fate}));
  const points = ({chainId, trackId, from, to, query, reverse = true} = {}) => {
    const term = (query || "").trim().toLocaleLowerCase();
    const result = data.days.filter(d => (!from || d.date >= from) && (!to || d.date <= to)).flatMap(dayTasks).filter(p =>
      (!chainId || p.chain.id === chainId) && (!trackId || p.chain.track === trackId) &&
      (!term || `${p.date} ${p.note} ${p.chain.label} ${p.day.headline}`.toLocaleLowerCase().includes(term)));
    return reverse ? result.reverse() : result;
  };
  const api = {
    data, esc, points, dayTasks,
    chain: id => chainMap.get(id), track: id => trackMap.get(id), day: date => dayMap.get(date),
    daysForChain: id => data.days.filter(d => d.chains.some(c => c.id === id)),
    formatDate: date => `${Number(date.slice(5, 7))}月${Number(date.slice(8, 10))}日`,
    range: key => {
      const end = new Date(data.asOf + "T00:00:00Z");
      if (key === "all") return {from: data.days[0].date, to: data.asOf};
      end.setUTCMonth(end.getUTCMonth() - (key === "3m" ? 3 : 1));
      return {from: end.toISOString().slice(0,10), to: data.asOf};
    },
    chainLink: (id, text) => `<button type="button" class="chain-link" data-open-chain="${esc(id)}">${esc(text || chainMap.get(id)?.label || id)}</button>`,
    pointLink: (p, text) => `<button type="button" class="point-link" data-open-point="${esc(p.chain.id)}" data-open-date="${esc(p.date)}">${esc(text || p.note)}</button>`,
    openChain, openDay, openPoint,
  };
  function sourceList(chain) {
    const refs = (chain.source_refs || []).filter(r => /^https:\/\/github\.com\//.test(r.url || ""));
    return refs.length ? `<ul class="source-list">${refs.map(r => `<li><a href="${esc(r.url)}" target="_blank" rel="noreferrer">${esc(r.title || r.path || "查看资料")}</a></li>`).join("")}</ul>` : '<p class="muted">此链暂无独立资料链接，可从对应日的正式研究日志查阅原始记录。</p>';
  }
  function reveal(html) {
    const dialog = document.getElementById("reading-dialog");
    document.getElementById("reading-content").innerHTML = html;
    if (!dialog.open) dialog.showModal();
    dialog.scrollTop = 0;
  }
  function openChain(id) {
    const chain = chainMap.get(id);
    if (!chain) return;
    const rows = points({chainId: id, reverse: false});
    const relations = data.handoffs.filter(e => e.from === id || e.to === id);
    reveal(`<p class="reading-label">${esc(trackMap.get(chain.track)?.label)} / ${rows.length} 个记录日</p><h2 id="reading-title">${esc(chain.label)}</h2><p class="reading-summary">${esc(chain.purpose)}</p>${chain.fate_note ? `<p>${esc(chain.fate_note)}</p>` : ""}<section class="reading-section"><h3>这条链的具体进展</h3><ol class="reading-points">${rows.map(p => `<li><time datetime="${p.date}">${p.date}</time><div>${api.pointLink(p)}${p.outcome === "dropped" ? '<small class="muted">　历史方案未采用</small>' : ""}</div></li>`).join("")}</ol></section><section class="reading-section"><h3>从哪里接来，交给了谁</h3>${relations.length ? relations.map(e => {const other = e.from === id ? e.to : e.from; return `<div class="reading-handoff"><small>${e.from === id ? "后续承接" : "前置来源"} / ${esc(e.type)} / ${esc(e.source_date)} 至 ${esc(e.date)}</small><div>${api.chainLink(other)}</div><p>${esc(e.note)}</p></div>`;}).join("") : '<p class="muted">当前未登记跨链承接。</p>'}</section><section class="reading-section"><h3>这条链的资料</h3>${sourceList(chain)}</section>`);
  }
  function openDay(date) {
    const day = dayMap.get(date);
    if (!day) return;
    reveal(`<p class="reading-label">${esc(date)} / ${day.chains.length} 项工作</p><h2 id="reading-title">${esc(day.headline)}</h2><section class="reading-section"><h3>当天各项工作</h3><ol class="reading-points">${dayTasks(day).map(p => `<li><span>${api.chainLink(p.chain.id, p.chain.short || p.chain.label)}</span><p>${api.pointLink(p)}</p></li>`).join("")}</ol></section><section class="reading-section"><h3>补充进展</h3>${(day.highlights || []).map(h => `<p>${esc(h)}</p>`).join("")}</section><p><a href="https://internship-dashboard.mengerwenjie.workers.dev/#/journal/${esc(date)}" target="_blank" rel="noreferrer">在正式研究日志中查看当日记录</a></p>`);
  }
  function openPoint(date, id) {
    const point = dayTasks(dayMap.get(date)).find(p => p.chain.id === id);
    if (!point) return;
    const siblings = points({chainId: id, reverse: false});
    const at = siblings.findIndex(p => p.date === date);
    reveal(`<p class="reading-label">${esc(date)} / ${esc(trackMap.get(point.chain.track)?.label)}</p><h2 id="reading-title">${esc(point.note)}</h2><p>${api.chainLink(id)}</p><p class="reading-summary">${esc(point.chain.purpose)}</p><div class="toolbar">${at > 0 ? api.pointLink(siblings[at - 1], `上一条 · ${siblings[at - 1].date}`) : ""}${at < siblings.length - 1 ? api.pointLink(siblings[at + 1], `下一条 · ${siblings[at + 1].date}`) : ""}</div><section class="reading-section"><h3>当天的其他工作</h3>${dayTasks(point.day).filter(p => p.chain.id !== id).map(p => `<div class="reading-handoff">${api.chainLink(p.chain.id)}<p>${esc(p.note)}</p></div>`).join("") || '<p class="muted">当天只登记了这一项工作。</p>'}</section><section class="reading-section"><h3>这条链的资料</h3>${sourceList(point.chain)}</section>`);
  }
  function storageGet(key) { try { return localStorage.getItem(key); } catch { return null; } }
  function storageSet(key, value) { try { localStorage.setItem(key, value); } catch { /* 文件预览禁用存储时，仍可浏览。 */ } }
  function start() {
    const params = new URLSearchParams(location.search);
    const variant = Object.hasOwn(names, params.get("variant")) ? params.get("variant") : "A";
    document.body.dataset.variant = variant;
    document.body.classList.toggle("is-embedded", params.get("embed") === "1");
    document.title = `${variant} ${names[variant]} · 研究日志设计初稿`;
    document.getElementById("prototype-description").textContent = `${variant} ${names[variant]}：${descriptions[variant]}`;
    document.getElementById("data-date").textContent = data.asOf;
    document.getElementById("variant-switcher").innerHTML = Object.entries(names).map(([key,label]) => `<a href="demo.html?variant=${key}" ${key === variant ? 'aria-current="page"' : ""}><b>${key}</b><span>${label}</span></a>`).join("");
    const mark = document.getElementById("mark-choice");
    const updateMark = () => { const picked = storageGet("journal-layout-preference"); mark.textContent = picked === variant ? "已标记为偏好" : "标记为偏好"; mark.setAttribute("aria-pressed", String(picked === variant)); };
    updateMark();
    mark.onclick = () => {storageSet("journal-layout-preference", variant); updateMark();};
    document.getElementById("close-reading").onclick = () => document.getElementById("reading-dialog").close();
    document.addEventListener("click", e => {
      const point = e.target.closest("[data-open-point]");
      if (point) {openPoint(point.dataset.openDate, point.dataset.openPoint); return;}
      const chain = e.target.closest("[data-open-chain]");
      if (chain) {openChain(chain.dataset.openChain); return;}
      const day = e.target.closest("[data-open-day]");
      if (day) openDay(day.dataset.openDay);
    });
    document.addEventListener("keydown", e => {
      if (e.defaultPrevented || e.altKey || e.ctrlKey || e.metaKey || document.getElementById("reading-dialog").open || e.target.closest("input,textarea,select,[contenteditable]")) return;
      if (e.key !== "ArrowLeft" && e.key !== "ArrowRight") return;
      e.preventDefault();
      const keys = Object.keys(names), at = keys.indexOf(variant);
      location.href = `demo.html?variant=${keys[(at + (e.key === "ArrowRight" ? 1 : 4)) % 5]}`;
    });
    const root = document.getElementById("demo-root");
    if (typeof window.JournalVariants[variant] === "function") window.JournalVariants[variant](root,api);
    else root.innerHTML = '<p class="empty">此方向尚在生成，请稍后重新打开。</p>';
  }
  window.JournalDemo = {start, api, names, descriptions};
}());
