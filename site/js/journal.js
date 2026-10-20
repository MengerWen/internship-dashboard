(function () {
  "use strict";
  const esc = value => String(value ?? "").replace(/[&<>"']/g, c => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}[c]));
  const $ = id => document.getElementById(id);
  const JournalView = {
    init(manifest, app) {
      this.app = app;
      this.days = manifest.journal || [];
      this.registry = manifest.chains || {tracks: [], chains: [], handoffs: []};
      this.chains = new Map(this.registry.chains.map(c => [c.id, c]));
      this.reports = new Map(manifest.daily.map(d => [d.date, d]));
      this.selected = null;
      this.selection = null;
      let preferences = {};
      try { preferences = JSON.parse(localStorage.getItem("journal-atlas-preferences") || "{}"); } catch (_) { /* 无可用设置时使用默认值。 */ }
      this.window = ["1m", "3m"].includes(preferences?.window) ? preferences.window : "all";
      this.density = [7, 11, 17].includes(preferences?.density) ? preferences.density : 11;
      this.chain = "";
      this.query = "";
      this.evidence = new Map();
      this.mode = matchMedia("(min-width: 860px)").matches ? "atlas" : "list";
      $("journal-title").textContent = $("tab-journal").textContent;
      $("journal-chain").innerHTML = '<option value="">全部链条</option>' + this.registry.tracks.map(t =>
        `<optgroup label="${esc(t.label)}">${this.registry.chains.filter(c => c.track === t.id).map(c => `<option value="${esc(c.id)}">${esc(c.label)}</option>`).join("")}</optgroup>`).join("");
      $("journal-window").addEventListener("change", e => { this.window = e.target.value; this.savePreferences(); this.render(); this.writeHash(); });
      $("journal-density").addEventListener("change", e => { this.density = Number(e.target.value); this.savePreferences(); this.render(); });
      $("journal-chain").addEventListener("change", e => this.focusChain(e.target.value));
      $("journal-clear").addEventListener("click", () => this.clearSelection());
      $("journal-find").addEventListener("input", e => { this.query = e.target.value; this.render(); });
      document.querySelectorAll("[data-journal-view]").forEach(button => button.addEventListener("click", () => {
        this.mode = button.dataset.journalView; this.render(); this.writeHash();
      }));
      $("view-journal").addEventListener("click", e => {
        $("view-journal").classList.toggle("is-keyboard", e.detail === 0);
        const retry = e.target.closest("[data-journal-evidence]");
        if (retry) this.loadEvidence(retry.dataset.journalEvidence, true);
        const point = e.target.closest("[data-journal-point]");
        if (point) { this.select(point.dataset.date, false, point.dataset.journalPoint); return; }
        const day = e.target.closest("[data-journal-day]");
        if (day) { e.preventDefault(); this.select(day.dataset.journalDay, !day.closest("#journal-figure")); return; }
        const chain = e.target.closest("[data-journal-chain]");
        if (chain) { this.focusChain(chain.dataset.journalChain); return; }
        const row = e.target.closest("tr[data-date]");
        if (row && !e.target.closest("a,button")) this.select(row.dataset.date, true);
      });
      document.addEventListener("click", e => {
        if (!this.selection || !$("view-journal").classList.contains("is-active") || e.defaultPrevented || e.detail === 0) return;
        if (e.target.closest("a, button, input, select, textarea, label, summary, details, [role='button'], [contenteditable], .journal-controls, .journal-annotation, #journal-detail, tr[data-date]")) return;
        if (!window.getSelection()?.isCollapsed) return;
        this.clearSelection();
      });
      $("view-journal").addEventListener("keydown", e => {
        $("view-journal").classList.add("is-keyboard");
        if (e.key === "Escape") { this.clearSelection(); return; }
        if (!e.target.closest("#journal-figure")) return;
        const day = e.target.closest("[data-journal-day]");
        if (day && ["Enter", " "].includes(e.key)) { e.preventDefault(); this.select(day.dataset.journalDay); return; }
        if (!["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown"].includes(e.key)) return;
        e.preventDefault();
        const dates = this.visibleDays(true), index = dates.findIndex(d => d.date === this.selected);
        if (["ArrowUp", "ArrowDown"].includes(e.key)) {
          const next = dates[index < 0 ? 0 : index + (e.key === "ArrowUp" ? -1 : 1)];
          if (next) this.select(next.date);
        } else {
          const current = dates[index];
          if (!current?.chains.length) return;
          const previous = this.selection?.kind === "point" ? current.chains.indexOf(this.selection.chain) : -1;
          const next = previous < 0 ? (e.key === "ArrowLeft" ? current.chains.length - 1 : 0) :
            (previous + (e.key === "ArrowLeft" ? -1 : 1) + current.chains.length) % current.chains.length;
          this.select(current.date, false, current.chains[next]);
        }
      });
      this.resizeObserver = new ResizeObserver(entries => {
        const width = entries[0].contentRect.width;
        if (width <= 0 || Math.abs(width - (this.measuredWidth || 0)) < 1) return;
        this.measuredWidth = width;
        cancelAnimationFrame(this.resizeFrame);
        this.resizeFrame = requestAnimationFrame(() => this.renderAtlas());
      });
      this.resizeObserver.observe($("view-journal"));
    },
    savePreferences() {
      try { localStorage.setItem("journal-atlas-preferences", JSON.stringify({density: this.density, window: this.window})); } catch (_) { /* 离线或禁用存储时仍可操作。 */ }
    },
    show(key) {
      const params = new URLSearchParams(location.hash.split("?")[1] || "");
      this.mode = ["atlas", "list"].includes(params.get("view")) ? params.get("view") : (matchMedia("(min-width: 860px)").matches ? "atlas" : "list");
      this.chain = this.chains.has(params.get("chain")) ? params.get("chain") : "";
      if (params.has("window")) this.window = ["1m", "3m"].includes(params.get("window")) ? params.get("window") : "all";
      this.selected = null;
      this.selection = this.chain ? {kind: "chain", chain: this.chain} : null;
      if (this.days.some(d => d.date === key)) {
        this.selected = key;
        if (!this.chain) this.selection = {kind: "day", date: key};
        const point = params.get("point");
        if (!this.chain && this.days.find(d => d.date === key).chains.includes(point)) this.selection = {kind: "point", date: key, chain: point};
        if (!this.visibleDays(true).some(d => d.date === key)) this.window = "all";
      }
      this.render();
      if (key) requestAnimationFrame(() => $("journal-detail").scrollIntoView({block: "start"}));
    },
    visibleDays(context = false) {
      const end = this.days.at(-1)?.date;
      if (!end) return [];
      const start = new Date(`${end}T00:00:00Z`);
      if (this.window !== "all") start.setUTCMonth(start.getUTCMonth() - (this.window === "1m" ? 1 : 3));
      const cutoff = this.window === "all" ? "0000" : start.toISOString().slice(0, 10);
      const q = this.query.trim().toLocaleLowerCase();
      return this.days.filter(d => d.date >= cutoff && (context || !this.chain || d.chains.includes(this.chain)) &&
        (context || this.mode !== "list" || !q || [d.date, d.headline, ...d.chains.map(cid => this.chains.get(cid)?.label || cid)].join(" ").toLocaleLowerCase().includes(q)));
    },
    writeHash() {
      const params = new URLSearchParams();
      if (this.chain) params.set("chain", this.chain);
      if (this.selection?.kind === "point") params.set("point", this.selection.chain);
      params.set("view", this.mode);
      if (this.window !== "all") params.set("window", this.window);
      history.replaceState(null, "", `#/journal${this.selected ? "/" + this.selected : ""}${params.size ? "?" + params : ""}`);
    },
    select(key, scroll = false, cid = "") {
      if (!this.days.some(d => d.date === key)) return;
      this.selected = key;
      this.chain = "";
      this.selection = cid ? {kind: "point", date: key, chain: cid} : {kind: "day", date: key};
      this.query = ""; $("journal-find").value = "";
      if (!this.visibleDays(true).some(d => d.date === key)) this.window = "all";
      if (scroll) this.mode = "atlas";
      this.render(); this.writeHash();
      if (scroll) {
        $("journal-detail").scrollIntoView({block: "start"});
        const scroller = document.querySelector(".journal-scroller");
        if (cid) scroller.scrollLeft = Math.max(0, this.atlas.positions.get(cid) - scroller.clientWidth / 2);
      }
    },
    focusChain(cid) {
      if (!cid) { this.clearSelection(); return; }
      this.chain = this.chains.has(cid) ? cid : "";
      this.selected = null;
      this.selection = this.chain ? {kind: "chain", chain: this.chain} : null;
      this.render(); this.writeHash();
    },
    clearSelection() {
      this.chain = ""; this.selected = null; this.selection = null;
      this.render(); this.writeHash();
    },
    pointNote(day, cid) {
      return day.chain_notes?.[cid] || {note: "", outcome: this.chains.get(cid)?.fate || "landed", outcome_note: this.chains.get(cid)?.fate_note || ""};
    },
    reportLinks(day) {
      return (day.reports_covering || (day.report ? [day.report] : [])).map(d => `<a href="#/daily/${esc(d)}">${esc(d)}</a>`).join(" ");
    },
    chainButtons(day) {
      return day.chains.map(cid => `<button type="button" class="journal-chain-link" data-journal-chain="${esc(cid)}">${esc(this.chains.get(cid)?.short || cid)}${day.chain_confidence[cid] === "inferred" ? ' <small>待核</small>' : ""}</button>`).join(" ") || "未归类";
    },
    render() {
      const focus = document.activeElement;
      const wasFocused = focus?.classList.contains("journal-atlas");
      const focusDay = focus?.getAttribute("data-journal-day");
      const focusChain = focus?.getAttribute("data-journal-chain");
      const headerFocused = focus?.classList.contains("journal-chain-label");
      const focusedNav = document.activeElement?.dataset.journalNav;
      this.visible = this.visibleDays();
      if (!this.chain && !this.visible.some(d => d.date === this.selected)) { this.selected = null; this.selection = null; }
      $("journal-window").value = this.window;
      $("journal-chain").value = this.chain;
      $("journal-density").value = String(this.density);
      document.querySelector(".journal-density-control").hidden = this.mode !== "atlas";
      $("journal-clear").hidden = !this.selection;
      const reports = new Set(this.visible.flatMap(d => d.reports_covering || []));
      $("journal-count").textContent = `${this.visible.length} 天 / ${reports.size} 篇汇报`;
      document.querySelectorAll("[data-journal-view]").forEach(b => b.setAttribute("aria-pressed", String(b.dataset.journalView === this.mode)));
      $("journal-figure").hidden = this.mode !== "atlas";
      $("journal-list").hidden = this.mode !== "list";
      document.querySelector(".journal-find").hidden = this.mode !== "list";
      this.renderAtlas();
      this.renderList();
      this.renderDetail();
      if (wasFocused) document.querySelector(".journal-atlas")?.focus({preventScroll: true});
      if (focusDay && focus?.closest("#journal-figure")) document.querySelector(`.journal-day-hit[data-journal-day="${CSS.escape(focusDay)}"]`)?.focus({preventScroll: true});
      if (headerFocused) document.querySelector(`.journal-chain-label[data-journal-chain="${CSS.escape(focusChain)}"]`)?.focus({preventScroll: true});
      if (focusedNav) {
        const buttons = [...document.querySelectorAll("[data-journal-nav]")];
        const next = buttons.find(b => b.dataset.journalNav === focusedNav && !b.disabled) || buttons.find(b => !b.disabled);
        next?.focus({preventScroll: true});
      }
    },
    renderAtlas() {
      if (this.mode !== "atlas" || !$("view-journal").classList.contains("is-active")) return;
      const days = this.visibleDays(true);
      const scroller = document.querySelector(".journal-scroller");
      const head = document.querySelector(".journal-head-scroller");
      if (!days.length) { scroller.innerHTML = '<p class="journal-empty">暂无日志。</p>'; head.innerHTML = ""; return; }
      const previousScroll = scroller.scrollLeft;
      const num = d => Date.parse(d + "T00:00:00Z") / 86400000;
      const first = num(days[0].date), last = num(days.at(-1).date);
      const dateWidth = 86, padding = 18, gap = 12, top = 18;
      const ordered = this.registry.tracks.flatMap(t => this.registry.chains.filter(c => c.track === t.id));
      const groups = this.registry.tracks.filter(t => ordered.some(c => c.track === t.id));
      const width = Math.max(scroller.clientWidth, dateWidth + 2 * padding + gap * Math.max(0, groups.length - 1) + ordered.length * 22);
      const colWidth = (width - dateWidth - 2 * padding - gap * Math.max(0, groups.length - 1)) / Math.max(1, ordered.length);
      const positions = new Map();
      ordered.forEach((c, i) => positions.set(c.id, dateWidth + padding + (i + .5) * colWidth + groups.findIndex(t => t.id === c.track) * gap));
      const y = d => top + (num(d) - first) * this.density;
      const height = top + (last - first) * this.density + 28, right = width - padding;
      const radius = d => Math.min(7, Math.max(2.1, 2.1 + .46 * Math.sqrt(d.total_commits)));
      const active = new Map(ordered.map(c => [c.id, days.filter(d => d.chains.includes(c.id))]));
      const header = [`<div class="journal-header-inner" style="width:${width}px"><span class="journal-date-heading">工作日期</span>`];
      groups.forEach(track => {
        const chains = ordered.filter(c => c.track === track.id);
        const left = positions.get(chains[0].id) - colWidth / 2;
        const end = positions.get(chains.at(-1).id) + colWidth / 2;
        header.push(`<span class="journal-track-label" style="left:${left}px;width:${end - left}px">${esc(track.label)}</span>`);
        if (end + gap < right) header.push(`<span class="journal-head-separator" style="left:${end + gap / 2}px"></span>`);
      });
      ordered.forEach(chain => header.push(`<button type="button" class="journal-chain-label${chain.fate === "dropped" ? " is-dropped" : ""}" data-journal-chain="${esc(chain.id)}" style="left:${positions.get(chain.id)}px;width:${Math.min(32, colWidth - 2)}px" aria-pressed="false" aria-label="${esc(chain.label)}${chain.fate === "dropped" ? "，未采用" : ""}"><span class="journal-chain-name">${esc(chain.short)}</span>${chain.fate === "dropped" ? '<small class="journal-fate-badge">未采用</small>' : ""}</button>`));
      head.innerHTML = header.join("") + "</div>";
      const parts = [`<div class="journal-canvas" style="width:${width}px"><svg class="journal-atlas" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}" tabindex="0" role="group" aria-labelledby="journal-atlas-title journal-atlas-desc" data-days="${days.length}" data-density="${this.density}"><title id="journal-atlas-title">工作日期与任务链条</title><desc id="journal-atlas-desc">日期从上到下，28 条链各占一列，按六个轨道分组。点的大小表示提交数。实心点表示工作写进了汇报，日期旁的短刻度表示当天发布了汇报。叉号表示未采用。点击日期、列头链名或单个点查看说明；上下键换日，左右键换点，Esc 取消。清单与下方说明提供文字入口。</desc>`];
      for (let n = first; n <= last; n++) {
        const date = new Date(n * 86400000).toISOString().slice(0, 10);
        const weekday = new Date(n * 86400000).getUTCDay();
        if ([0, 6].includes(weekday)) parts.push(`<rect class="journal-weekend" x="${dateWidth}" y="${y(date) - this.density / 2}" width="${right - dateWidth}" height="${this.density}"/>`);
        if (date.endsWith("-01") || n === first) parts.push(`<path class="journal-month-rule" d="M${dateWidth - 8},${y(date)} H${right}"/><text class="journal-axis-label" x="0" y="${y(date) - 5}">${Number(date.slice(5, 7))}月</text>`);
      }
      groups.slice(0, -1).forEach(track => {
        const end = ordered.filter(c => c.track === track.id).at(-1);
        const x = positions.get(end.id) + colWidth / 2 + gap / 2;
        parts.push(`<path class="journal-rule" d="M${x},0 V${height}"/>`);
      });
      days.forEach(d => {
        parts.push(`<rect class="journal-day-hit" data-journal-day="${d.date}" x="0" y="${y(d.date) - this.density / 2}" width="${dateWidth}" height="${this.density}" tabindex="0" role="button" aria-label="${d.date} ${esc(d.weekday)}，${esc(d.headline)}" aria-pressed="false"/>`);
        if (this.density >= 11 || new Date(d.date + "T00:00:00Z").getUTCDay() === 1) parts.push(`<text class="journal-date-label" data-date="${d.date}" x="${dateWidth - 12}" y="${y(d.date) + 4}" text-anchor="end">${d.date.slice(5)}</text>`);
        if (d.reports_published?.length) parts.push(`<path class="journal-report-tick" data-date="${d.date}" d="M${dateWidth - 6},${y(d.date)} h8"/>`);
      });
      this.registry.handoffs.forEach(edge => {
        const from = active.get(edge.from), to = active.get(edge.to);
        if (!from?.length || !to?.length) return;
        const target = to.find(d => !edge.date || d.date >= edge.date)?.date || to.at(-1).date;
        const source = from.filter(d => d.date <= target).at(-1)?.date || from[0].date;
        const x1 = positions.get(edge.from), x2 = positions.get(edge.to), y1 = y(source), y2 = y(target);
        const dash = edge.type === "派生" ? "4 3" : edge.type === "依赖解除" ? "1 3" : edge.type === "收口" ? "7 2 1 2" : (edge.confidence === "inferred" ? "2 5" : "");
        const bend = Math.max(22, Math.abs(y2 - y1) / 2);
        const path = `M${x1},${y1} C${x1},${y1 + bend} ${x2},${y2 - bend} ${x2},${y2}`;
        parts.push(`<g class="journal-unit journal-handoff" data-chains="${esc(edge.from)} ${esc(edge.to)}" data-type="${esc(edge.type)}" data-date="${target}"><path class="journal-halo" d="${path}"/><path class="journal-handoff-path" stroke-dasharray="${dash}" d="${path}"/></g>`);
      });
      ordered.forEach(chain => {
        const dates = active.get(chain.id), cx = positions.get(chain.id);
        parts.push(`<g class="journal-unit journal-chain-unit" data-chains="${esc(chain.id)}" data-chain-x="${cx}">`);
        if (dates.length) {
          parts.push(`<path class="journal-column-guide" d="M${cx},${y(dates[0].date)} V${y(dates.at(-1).date)}"/>`);
          dates.forEach((day, i) => {
            if (!i) return;
            const prev = dates[i - 1];
            const dropped = chain.fate === "dropped" || [day, prev].some(d => this.pointNote(d, chain.id).outcome === "dropped");
            const cls = dropped ? "journal-dropped-line" : num(day.date) - num(prev.date) > 3 ? "journal-pause" : "journal-chain-line";
            const path = `M${cx},${y(prev.date)} V${y(day.date)}`;
            parts.push(`<path class="journal-halo" d="${path}"/><path class="${cls}" d="${path}"/>`);
          });
          dates.forEach(day => {
            const r = radius(day), cy = y(day.date), dropped = this.pointNote(day, chain.id).outcome === "dropped";
            parts.push(`<circle class="journal-dot-halo" cx="${cx}" cy="${cy}" r="${r + 1.8}"/>`);
            if (dropped) {
              const a = Math.max(3.4, r);
              parts.push(`<path class="journal-dot journal-cross" data-date="${day.date}" data-chain="${esc(chain.id)}" d="M${cx - a},${cy - a} L${cx + a},${cy + a} M${cx + a},${cy - a} L${cx - a},${cy + a}"/>`);
            } else parts.push(`<circle class="journal-dot${day.reports_covering?.length ? " has-report" : ""}" data-date="${day.date}" data-chain="${esc(chain.id)}" cx="${cx}" cy="${cy}" r="${r}"/>`);
          });
          if (chain.fate !== "dropped" && (chain.status === "done" || chain.fate === "parked") && chain.end === dates.at(-1).date) {
            parts.push(`<rect class="journal-seal${chain.fate === "parked" ? " is-parked" : ""}" x="${cx - 3.5}" y="${y(dates.at(-1).date) - 3.5}" width="7" height="7"/>`);
          }
        }
        parts.push("</g>");
      });
      ordered.forEach(chain => active.get(chain.id).forEach(day => parts.push(`<rect class="journal-point-hit" data-journal-point="${esc(chain.id)}" data-date="${day.date}" x="${positions.get(chain.id) - 9}" y="${y(day.date) - (this.density + 6) / 2}" width="18" height="${this.density + 6}" role="button" tabindex="-1" aria-label="${day.date}，${esc(chain.label)}，${esc(this.pointNote(day, chain.id).note || day.headline)}"/>`)));
      parts.push('<g class="journal-selection-overlay" aria-hidden="true"></g></svg><div class="journal-annotations"></div></div>');
      scroller.innerHTML = parts.join("");
      scroller.scrollLeft = previousScroll;
      head.scrollLeft = scroller.scrollLeft;
      scroller.onscroll = () => { head.scrollLeft = scroller.scrollLeft; };
      head.onscroll = () => { if (head.scrollLeft !== scroller.scrollLeft) scroller.scrollLeft = head.scrollLeft; };
      document.querySelector("#journal-figure figcaption").innerHTML = '<p>日期从上往下，28 条链各占一列。点的大小表示当天提交数；实心点表示这天的工作写进了汇报，空心点表示未写入。左侧短刻度表示当天发布了汇报。超过 3 天的空档用虚线；实心方块表示收口，空心方块表示暂搁；叉号与点线表示未采用。</p><p>点击日期看当天各条链，点击列头链名看整条链，点击单个点看该点。点击空白处或按 Esc 取消选中。上下键换日，左右键切换当天的点。</p><div class="journal-handoff-legend" aria-label="交接线型">' + [["延续", ""], ["派生", "4 3"], ["依赖解除", "1 3"], ["收口", "7 2 1 2"]].map(([label, dash]) => `<span><svg aria-hidden="true" viewBox="0 0 34 8"><path d="M1 4 H33" stroke-dasharray="${dash}"/></svg>${label}</span>`).join("") + '<span>推断关系在脉络中标明</span></div>';
      this.atlas = {y, positions, days, height, width, dateWidth, right, radius, ordered, active};
      if (this.chain && !this.visible.length) document.querySelector("#journal-figure figcaption").insertAdjacentHTML("beforeend", '<p class="journal-window-empty" role="status">此时间窗内没有这条链的记录。下方链条卡展示它的全部历史；可将时间窗改为“全部”查看图谱。</p>');
      this.highlightAtlas();
    },
    highlightAtlas() {
      const sel = this.selection, a = this.atlas;
      if (!a) return;
      const day = this.days.find(d => d.date === sel?.date);
      const live = new Set(sel?.kind === "chain" || sel?.kind === "point" ? [sel.chain] : day?.chains || []);
      document.querySelectorAll(".journal-chain-label").forEach(label => {
        const lit = live.has(label.dataset.journalChain);
        label.classList.toggle("is-selected", lit);
        label.classList.toggle("is-dimmed", Boolean(sel) && !lit);
        label.setAttribute("aria-pressed", String(lit));
      });
      document.querySelectorAll(".journal-unit").forEach(g => {
        const lit = g.dataset.chains.split(" ").some(id => live.has(id));
        g.classList.toggle("is-dimmed", Boolean(sel) && !lit);
        g.classList.toggle("is-focused", sel?.kind === "chain" && lit);
      });
      document.querySelectorAll(".journal-day-hit").forEach(hit => hit.setAttribute("aria-pressed", String(hit.dataset.journalDay === sel?.date)));
      document.querySelectorAll(".journal-date-label").forEach(label => label.classList.toggle("is-selected", label.dataset.date === sel?.date));
      const svg = document.querySelector(".journal-atlas"), overlay = svg.querySelector(".journal-selection-overlay");
      const annotations = document.querySelector(".journal-annotations");
      if (!sel) return;
      if (sel.kind === "chain") {
        const scroller = document.querySelector(".journal-scroller");
        const cx = a.positions.get(sel.chain), dates = a.active.get(sel.chain) || [];
        const unit = [...svg.querySelectorAll(".journal-chain-unit")].find(g => g.dataset.chains === sel.chain);
        if (unit) svg.insertBefore(unit, svg.querySelector(".journal-point-hit"));
        const onRight = cx < a.width / 2;
        const noteWidth = Math.min(330, scroller.clientWidth - 50, onRight ? a.right - cx - 24 : cx - a.dateWidth - 24);
        const left = onRight ? cx + 22 : cx - noteWidth - 22;
        if (this.mode === "atlas" && scroller.clientWidth < 600) {
          scroller.scrollLeft = Math.max(0, Math.min(a.width - scroller.clientWidth, Math.min(left, cx) - 10));
          document.querySelector(".journal-head-scroller").scrollLeft = scroller.scrollLeft;
        }
        annotations.innerHTML = dates.map(d => this.annotationHtml(d, sel.chain, noteWidth, "journal-chain-annotation")).join("");
        const cards = [...annotations.children];
        let nextY = 8;
        const ys = cards.map((card, i) => {
          const desired = Math.max(a.y(dates[i].date) - 12, nextY);
          card.style.left = left + "px";
          nextY = desired + card.offsetHeight + 8;
          return desired;
        });
        const shift = Math.min(Math.max(0, nextY - a.height + 10), ys[0] || 0);
        const lines = [];
        cards.forEach((card, i) => {
          const cy = ys[i] - shift;
          card.style.top = cy + "px";
          lines.push(`<path class="journal-annotation-leader" d="M${cx},${a.y(dates[i].date)} H${onRight ? left - 8 : left + noteWidth + 8} V${cy + 12} H${onRight ? left : left + noteWidth}"/>`);
        });
        const expanded = Math.max(a.height, nextY - shift + 10);
        svg.setAttribute("height", expanded); svg.setAttribute("viewBox", `0 0 ${a.width} ${expanded}`);
        overlay.innerHTML = lines.join("");
        return;
      }
      if (!day) return;
      const ids = sel.kind === "point" ? [sel.chain] : [...day.chains].sort((x, z) => a.positions.get(x) - a.positions.get(z));
      const cy = a.y(day.date);
      const stack = document.querySelector(".journal-scroller").clientWidth < 600;
      const cardWidth = stack ? Math.min(270, document.querySelector(".journal-scroller").clientWidth - 20) : Math.min(236, (a.right - a.dateWidth - 10 * Math.max(0, ids.length - 1)) / Math.max(1, ids.length));
      annotations.innerHTML = ids.map(cid => this.annotationHtml(day, cid, cardWidth)).join("");
      const cards = [...annotations.children], xs = [];
      cards.forEach((card, i) => xs.push(stack ? Math.min(a.width - cardWidth - 10, document.querySelector(".journal-scroller").scrollLeft + 10) : Math.max(a.positions.get(ids[i]) - cardWidth / 2, i ? xs[i - 1] + cardWidth + 10 : 10)));
      if (!stack && xs.length) {
        const overflow = Math.max(0, xs.at(-1) + cardWidth - a.width + 10);
        xs.forEach((x, i) => { xs[i] = x - overflow; });
      }
      const totalHeight = stack ? cards.reduce((sum, card) => sum + card.offsetHeight + 10, -10) : Math.max(0, ...cards.map(card => card.offsetHeight));
      let bandY = cy + 22;
      if (bandY + totalHeight > a.height - 10) bandY = Math.max(8, cy - totalHeight - 22);
      const paths = [`<path class="journal-selection-line" d="M${a.dateWidth},${cy} H${a.right}"/>`];
      cards.forEach((card, i) => {
        card.style.left = xs[i] + "px"; card.style.top = bandY + "px";
        const cx = a.positions.get(ids[i]);
        paths.push(`<circle class="journal-selection-ring" data-date="${day.date}" data-chain="${esc(ids[i])}" cx="${cx}" cy="${cy}" r="${a.radius(day) + 3}"/>`);
        const edgeY = bandY > cy ? bandY : bandY + card.offsetHeight;
        paths.push(`<path class="journal-annotation-leader" d="M${cx},${cy} V${cy + (bandY > cy ? 12 : -12)} H${xs[i] + cardWidth / 2} V${edgeY}"/>`);
        if (stack) bandY += card.offsetHeight + 10;
      });
      overlay.innerHTML = paths.join("");
      const expanded = Math.max(a.height, bandY + (stack ? 10 : totalHeight + 10));
      svg.setAttribute("height", expanded); svg.setAttribute("viewBox", `0 0 ${a.width} ${expanded}`);
    },
    annotationHtml(day, cid, width, extra = "") {
      const note = this.pointNote(day, cid), dropped = note.outcome === "dropped";
      return `<article class="journal-annotation ${extra}${dropped ? " is-dropped" : ""}" data-annotation-chain="${esc(cid)}" data-date="${day.date}" style="width:${width}px"><p><time>${day.date.slice(5)}</time> ${esc(this.chains.get(cid)?.short)}</p><strong>${esc(note.note || "注解待补")}</strong>${dropped ? '<span class="journal-fate-badge">未采用</span>' : ""}${extra ? "" : `<small>${esc(day.weekday)}　${day.total_commits} 次提交</small><small>${day.reports_covering?.length ? "工作已写入汇报" : "工作未写入汇报"}；当天发布 ${day.reports_published?.length || 0} 篇</small>`}</article>`;
    },
    renderList() {
      $("journal-list").innerHTML = this.visible.length ? `<table><caption class="sr-only">按真实工作日期排列的日志</caption><thead><tr><th scope="col">日期</th><th scope="col">这天做了什么</th><th scope="col">链条</th><th scope="col">提交</th><th scope="col">汇报</th></tr></thead><tbody>${this.visible.map(d => `<tr class="${d.report ? "has-report" : ""}" data-date="${d.date}" ${d.date === this.selected ? 'aria-current="date"' : ""}><td><a href="#/journal/${d.date}" data-journal-day="${d.date}">${d.date}</a><small>${esc(d.weekday)}</small></td><td><a href="#/journal/${d.date}" data-journal-day="${d.date}">${esc(d.headline)}</a>${d.headline_source === "commit" ? '<small>待写</small>' : ""}</td><td>${this.chainButtons(d)}</td><td class="journal-number">${d.total_commits}</td><td>${this.reportLinks(d) || "—"}</td></tr>`).join("")}</tbody></table>` : '<p class="journal-empty">没有匹配的日期。请调整时间窗、链条或查找词。</p>';
    },
    flowHtml(ids) {
      return ids.map(cid => {
        const links = this.registry.handoffs.filter(h => h.from === cid || h.to === cid).map(h => {
          const incoming = h.to === cid, other = incoming ? h.from : h.to;
          return `<li>${incoming ? "承接" : "交给"} ${this.chainButton(other)} <small>${esc(h.type)}${h.confidence === "inferred" ? "，推断" : ""}</small></li>`;
        });
        return `<section><h4>${esc(this.chains.get(cid)?.label)}</h4><ul>${links.join("") || "<li>尚未登记交接</li>"}</ul></section>`;
      }).join("");
    },
    chainButton(cid) {
      return `<button type="button" class="journal-chain-link" data-journal-chain="${esc(cid)}">${esc(this.chains.get(cid)?.short || cid)}</button>`;
    },
    navButton(day, label) {
      return `<button type="button" data-journal-nav="${esc(label)}" ${day ? `data-journal-day="${day.date}"` : "disabled"}>${label}${day ? ` ${day.date} ${esc(day.headline.slice(0, 28))}${day.headline.length > 28 ? "…" : ""}` : ""}</button>`;
    },
    renderDetail() {
      if (this.chain) { this.renderChainCard(); return; }
      const day = this.days.find(d => d.date === this.selected);
      if (!day || !this.visible.length) { $("journal-detail").innerHTML = ""; return; }
      const all = this.visibleDays(true), index = all.indexOf(day);
      const lineage = day.chains.map(cid => {
        const dates = this.days.filter(d => d.chains.includes(cid)), i = dates.indexOf(day);
        return `<p>${this.chainButton(cid)} 的相邻记录</p><div class="journal-chain-neighbors">${this.navButton(dates[i - 1], "上一天")}${this.navButton(dates[i + 1], "下一天")}</div>`;
      }).join("");
      const pointNotes = day.chains.map(cid => {
        const note = this.pointNote(day, cid);
        return `<li>${this.chainButton(cid)}：${esc(note.note || "注解待补")}${note.outcome === "dropped" ? ' <span class="journal-fate-badge">未采用</span>' : ""}${note.outcome_note ? `<p>${esc(note.outcome_note)}</p>` : ""}</li>`;
      }).join("");
      $("journal-detail").innerHTML = `<nav class="journal-day-nav" aria-label="相邻工作日">${this.navButton(all[index - 1], "前一天")}${this.navButton(all[index + 1], "后一天")}</nav><article class="journal-day-card" data-selected-date="${day.date}"><div class="journal-day-top"><p><time>${day.date}</time>　${esc(day.weekday)}　${day.total_commits} 次提交</p>${day.report ? `<a href="#/daily/${day.report}">每日汇报 ↗</a>` : ""}</div><h2 class="${day.headline_source === "commit" ? "journal-draft" : ""}">${esc(day.headline)}${day.headline_source === "commit" ? " <small>待写</small>" : ""}</h2><p>${this.chainButtons(day)}</p><div class="journal-card-columns"><div><section><h3>做了什么</h3><ul id="journal-highlights">${day.highlights.map(h => `<li>${esc(h)}</li>`).join("") || '<li>当天没有可展示的提交或计划。</li>'}</ul></section><section><h3>脉络</h3>${this.flowHtml(day.chains) || '<p>未归类</p>'}${lineage}</section><div id="journal-body" class="markdown-body"></div></div><section><h3>根据</h3><details class="journal-evidence" data-evidence-date="${day.date}"><summary>提交、计划与汇报 <small>${day.total_commits} 次提交</small></summary><div id="journal-evidence-content"><p>正在读取证据…</p></div></details></section></div></article>`;
      document.querySelector(".journal-evidence").addEventListener("toggle", e => {
        if (e.target.open) this.loadEvidence(day.date);
      });
      if (pointNotes) $("journal-highlights").innerHTML = pointNotes;
      if (day.has_body) this.app.loadFragment(`journal/${day.date}.html`, `journal-body-${day.date}`).then(html => {
        if (this.selected === day.date && !this.chain) { $("journal-body").innerHTML = html; this.app.enhanceContent($("journal-body")); }
      }).catch(() => { if ($("journal-body")) $("journal-body").textContent = "正文读取失败，请刷新重试。"; });
    },
    async loadEvidence(key, retry = false) {
      const node = $("journal-evidence-content");
      if (!node) return;
      node.innerHTML = "<p>正在读取证据…</p>";
      try {
        if (retry) this.evidence.delete(key);
        if (!this.evidence.has(key)) {
          const inline = $(`journal-ev-${key}`);
          const request = inline ? Promise.resolve(JSON.parse(inline.textContent)) : fetch(this.days.find(d => d.date === key).evidence_path).then(r => {
            if (!r.ok) throw new Error("证据读取失败"); return r.json();
          });
          this.evidence.set(key, request);
        }
        const ev = await this.evidence.get(key);
        if (this.selected !== key || this.chain || !node.isConnected) return;
        node.innerHTML = this.evidenceHtml(ev);
        const day = this.days.find(d => d.date === key);
        if (!day.highlights.length && !Object.values(day.chain_notes || {}).some(note => note.note)) {
          const highlights = ev.plans?.length ? ev.plans.map(p => p.title) : ev.repos.flatMap(r => r.items.map(i => i.subject));
          $("journal-highlights").innerHTML = highlights.slice(0, 3).map(h => `<li>${esc(h)}</li>`).join("") || "<li>当天没有可展示的提交或计划。</li>";
        }
      } catch (error) {
        this.evidence.delete(key);
        if (node.isConnected) node.innerHTML = `<p role="alert">当天证据读取失败。</p><button type="button" data-journal-evidence="${key}">重试</button>`;
      }
    },
    evidenceHtml(ev) {
      const repos = (ev.repos || []).map(repo => `<details class="journal-repo"><summary>${esc(repo.repo)} ${repo.commits} 次${repo.commits > repo.items.length ? `（列出前 ${repo.items.length} 条）` : ""}</summary><p>${(repo.top_paths || []).map(([p, n]) => `${esc(p)} ${n}`).join(" / ")}</p><ul>${repo.items.map(item => {
        const url = String(repo.commit_url || "").replace("{sha}", item.sha);
        const sha = /^[a-f0-9]{7,40}$/.test(item.sha) && /^https:\/\/github\.com\//.test(url) ? `<a href="${esc(url)}" target="_blank" rel="noopener noreferrer">${item.sha.slice(0, 7)}</a>` : esc(item.sha?.slice(0, 7));
        return `<li>${sha} ${esc(item.subject)}</li>`;
      }).join("")}</ul></details>`).join("");
      const report = d => `<li><a href="#/daily/${esc(d)}">${esc(d)} ${esc(this.reports.get(d)?.title || "每日汇报")}</a><p>${esc(this.reports.get(d)?.summary)}</p></li>`;
      const reverts = (ev.repos || []).reduce((sum, repo) => sum + (repo.revert_count || 0), 0);
      return (reverts ? `<p>本日回滚 ${reverts} 次（提交回滚记录）</p>` : "") + repos + `<h4>计划</h4><ul>${(ev.plans || []).map(p => `<li>${esc(p.title)}<small>${esc(p.repo)} / ${esc(p.file)}</small></li>`).join("") || "<li>无计划文件</li>"}</ul><h4>覆盖这天工作的汇报</h4><ul>${(ev.reports_covering || []).filter(d => this.reports.has(d)).map(report).join("") || "<li>无</li>"}</ul><h4>这天发布的汇报</h4><ul>${(ev.reports_published || []).filter(d => this.reports.has(d)).map(report).join("") || "<li>无</li>"}</ul>`;
    },
    renderChainCard() {
      const chain = this.chains.get(this.chain);
      const days = this.days.filter(d => d.chains.includes(chain.id));
      const reports = [...new Set([...days.flatMap(d => d.reports_covering || []), ...(chain.closes_into?.daily || [])])].filter(d => this.reports.has(d));
      const track = this.registry.tracks.find(t => t.id === chain.track);
      const windowNote = !this.visible.length ? '<p class="journal-window-empty" role="status">此时间窗内没有这条链的记录。下面展示这条链的全部历史。</p>' : "";
      $("journal-detail").innerHTML = `<article class="journal-day-card journal-chain-card">${windowNote}<p>${esc(track?.label)}　${days.length} 天　${chain.start} 至 ${chain.end}</p><h2>${esc(chain.label)}</h2><p>${esc(chain.purpose)}</p><h3>承接与交接</h3>${this.flowHtml([chain.id])}<h3>落成的汇报与成果</h3><ul>${reports.map(d => `<li><a href="#/daily/${d}">${d} ${esc(this.reports.get(d).title)}</a></li>`).join("") || "<li>尚无关联汇报</li>"}${chain.closes_into?.showcase ? `<li><a href="#/showcase/${esc(chain.closes_into.showcase)}">正式成果：${esc(this.app.getStage(chain.closes_into.showcase).label)}</a></li>` : ""}</ul><h3>这条链上的每一天</h3><div class="journal-chain-days">${days.map(d => `<button type="button" data-journal-day="${d.date}"><time>${d.date}</time><span>${esc(d.headline)}</span>${d.chain_confidence[chain.id] === "inferred" ? '<small>归属待核</small>' : ""}</button>`).join("")}</div></article>`;
      const fate = {landed: "已采用", folded: "已并入后续工作", parked: "暂搁", dropped: "未采用"};
      document.querySelector(".journal-chain-card h2").insertAdjacentHTML("afterend", `<p>${fate[chain.fate] || fate.landed}${chain.fate_note ? `：${esc(chain.fate_note)}` : ""}</p>`);
      document.querySelectorAll(".journal-chain-days button").forEach((button, i) => {
        const note = this.pointNote(days[i], chain.id);
        button.querySelector("span").innerHTML = esc(note.note || days[i].headline) + (note.outcome === "dropped" ? ' <span class="journal-fate-badge">未采用</span>' : "");
      });
    },
  };
  window.JournalView = JournalView;
})();
