(function () {
  "use strict";
  const esc = value => String(value ?? "").replace(/[&<>"']/g, c => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}[c]));
  const $ = id => document.getElementById(id);
  const densityRange = {min: 4, max: 44};
  const densityPreferences = {version: 2, standard: 14, legacyStandard: 11};
  const handoffGap = 4.2;
  function segmentHitsNode(a, b, point, gap = handoffGap) {
    const r = point.r + gap;
    if (!point.square) {
      const dx = b.x - a.x, dy = b.y - a.y, length2 = dx * dx + dy * dy;
      const t = length2 ? Math.max(0, Math.min(1, ((point.x - a.x) * dx + (point.y - a.y) * dy) / length2)) : 0;
      return (a.x + dx * t - point.x) ** 2 + (a.y + dy * t - point.y) ** 2 <= r * r;
    }
    let low = 0, high = 1;
    for (const key of ["x", "y"]) {
      const delta = b[key] - a[key], start = point[key] - r, end = point[key] + r;
      if (Math.abs(delta) < 1e-8) {
        if (a[key] < start || a[key] > end) return false;
      } else {
        const t1 = (start - a[key]) / delta, t2 = (end - a[key]) / delta;
        low = Math.max(low, Math.min(t1, t2)); high = Math.min(high, Math.max(t1, t2));
        if (low > high) return false;
      }
    }
    return true;
  }
  function curveSegments(a, b, c, d, depth = 0) {
    const distance = p => {
      const dx = d.x - a.x, dy = d.y - a.y;
      return Math.abs(dy * (p.x - a.x) - dx * (p.y - a.y)) / (Math.hypot(dx, dy) || 1);
    };
    if (depth >= 12 || Math.max(distance(b), distance(c)) < .15) return [[a, d]];
    const mid = (p, q) => ({x: (p.x + q.x) / 2, y: (p.y + q.y) / 2});
    const ab = mid(a, b), bc = mid(b, c), cd = mid(c, d), abc = mid(ab, bc), bcd = mid(bc, cd), center = mid(abc, bcd);
    return [...curveSegments(a, ab, abc, center, depth + 1), ...curveSegments(center, bcd, cd, d, depth + 1)];
  }
  function flowSweep(from, to, departure = 0, arrival = 0) {
    const dx = to.x - from.x, dy = to.y - from.y;
    if (Math.abs(dy) < .01) return [];
    const a = departure * dx, b = arrival * dx;
    const c3 = 10 * dx - 6 * a - 4 * b, c4 = -15 * dx + 8 * a + 7 * b, c5 = 6 * dx - 3 * a - 3 * b;
    const point = t => ({x: from.x + a * t + c3 * t ** 3 + c4 * t ** 4 + c5 * t ** 5, y: from.y + dy * t});
    const slope = t => a + 3 * c3 * t * t + 4 * c4 * t ** 3 + 5 * c5 * t ** 4;
    // 五次缓变曲线在竖向段的交接处曲率为零；细分成三次曲线，误差小于 .02px。
    const fit = (start, end, depth = 0) => {
      const p = point(start), q = point(end), dt = end - start;
      const c1 = {x: p.x + slope(start) * dt / 3, y: p.y + dy * dt / 3}, c2 = {x: q.x - slope(end) * dt / 3, y: q.y - dy * dt / 3};
      const error = [.25, .5, .75].some(t => {
        const u = 1 - t, x = p.x * u ** 3 + 3 * c1.x * u * u * t + 3 * c2.x * u * t * t + q.x * t ** 3;
        return Math.abs(x - point(start + dt * t).x) > .02;
      });
      return error && depth < 7 ? [...fit(start, (start + end) / 2, depth + 1), ...fit((start + end) / 2, end, depth + 1)] : [[p, c1, c2, q]];
    };
    return fit(0, 1);
  }
  function routeHandoff(from, to, points, lanes, height) {
    const others = points.filter(p => p !== from && p !== to);
    // 紧密压缩时，端点本身可能已处于同列相邻点的留白内，重叠区由保护层裁掉。
    const obstacles = others.filter(p => ![from, to].some(end => p.x === end.x && Math.abs(p.y - end.y) < p.r + handoffGap));
    const columns = new Map();
    obstacles.forEach(p => {
      if (!columns.has(p.x)) columns.set(p.x, {x: p.x, r: 0, points: []});
      const column = columns.get(p.x);
      column.r = Math.max(column.r, p.r + handoffGap + .15); column.points.push(p);
    });
    const clear = curve => {
      const lowX = Math.min(...curve.map(p => p.x)), highX = Math.max(...curve.map(p => p.x));
      const lowY = Math.min(...curve.map(p => p.y)), highY = Math.max(...curve.map(p => p.y));
      const nearby = [];
      for (const column of columns.values()) {
        if (column.x + column.r < lowX || column.x - column.r > highX) continue;
        for (const p of column.points) if (p.y + p.r + handoffGap + .15 >= lowY && p.y - p.r - handoffGap - .15 <= highY) nearby.push(p);
      }
      if (!nearby.length && lowY >= 2.5 && highY <= height - 2.5) return true;
      const [a, b, c, d] = curve, dx = d.x - a.x;
      // 横向匀速的候选弧线先在节点所在列快速排除明显碰撞，再做精细曲线检查。
      if (dx && Math.abs(b.x - a.x - dx / 3) < 1e-6 && Math.abs(d.x - c.x - dx / 3) < 1e-6) {
        for (const p of nearby) {
          const t = (p.x - a.x) / dx, u = 1 - t;
          if (t >= 0 && t <= 1 && Math.abs(a.y * u ** 3 + 3 * b.y * u * u * t + 3 * c.y * u * t * t + d.y * t ** 3 - p.y) <= p.r + handoffGap) return false;
        }
      }
      return curveSegments(...curve).every(([a, b]) => a.y >= 2.5 && b.y >= 2.5 && a.y <= height - 2.5 && b.y <= height - 2.5 && !nearby.some(p => segmentHitsNode(a, b, p, handoffGap + .15)));
    };
    const dx = to.x - from.x, dy = to.y - from.y;
    const serialize = ([a, b, c, d]) => `M${a.x},${a.y} C${b.x},${b.y} ${c.x},${c.y} ${d.x},${d.y}`;
    const cubic = (ax, ay, bx, by) => [from, {x: from.x + dx * ax, y: from.y + dy * ay}, {x: from.x + dx * bx, y: from.y + dy * by}, to];
    const vertical = Math.abs(dy) > Math.abs(dx);
    const preferredCurve = vertical ? cubic(0, .45, 1, .55) : cubic(.4, 0, .6, 1);
    if (clear(preferredCurve)) return serialize(preferredCurve);
    const candidates = [];
    if (dy) {
      // 控制点始终在两个记录日之间；一条线向前推进，不靠回头或鼓包避让。
      const ratios = [0, .25, .5, .75, 1];
      for (const ax of ratios) for (const ay of ratios) for (const bx of ratios) for (const by of ratios) {
        const curve = cubic(ax, ay, bx, by), [, b, c] = curve;
        const length = Math.hypot(b.x - from.x, b.y - from.y) + Math.hypot(c.x - b.x, c.y - b.y) + Math.hypot(to.x - c.x, to.y - c.y);
        const departure = vertical ? Math.abs(b.x - from.x) + Math.abs(to.x - c.x) : Math.abs(b.y - from.y) + Math.abs(to.y - c.y);
        candidates.push({curve, cost: length + departure * .12});
      }
      for (const [ax, bx] of [[0, 1], [1, 0], [1 / 3, 2 / 3]]) for (let ay = 0; ay <= 1; ay += .125) for (let by = 0; by <= 1; by += .125) {
        const curve = cubic(ax, ay, bx, by), [, b, c] = curve;
        candidates.push({curve, cost: Math.hypot(b.x - from.x, b.y - from.y) + Math.hypot(c.x - b.x, c.y - b.y) + Math.hypot(to.x - c.x, to.y - c.y) + Math.abs(b.x - from.x) * .12 + Math.abs(to.x - c.x) * .12});
      }
    } else {
      // 同日关系只允许浅弧，把必要的绕行摊开到整条线，不制造高耸的拱形。
      const limit = Math.min(28, Math.abs(dx) * .18), offsets = [0];
      for (let n = 4; n <= limit; n += 4) offsets.push(-n, n);
      for (const [ax, bx] of [[1 / 3, 2 / 3], [0, 1], [0, .65], [.35, 1], [1, 0]]) for (const a of offsets) for (const b of offsets) candidates.push({curve: [from, {x: from.x + dx * ax, y: from.y + a}, {x: from.x + dx * bx, y: to.y + b}, to], cost: a * a - a * b + b * b + Math.abs(ax - 1 / 3) + Math.abs(bx - 2 / 3)});
    }
    for (const {curve} of candidates.sort((a, b) => a.cost - b.cost)) if (clear(curve)) return serialize(curve);
    if (dy && Math.abs(dy) <= 28) {
      const shallow = [], offsets = [-28, -24, -20, -16, -12, -8, -4, 0, 4, 8, 12, 16, 20, 24, 28];
      for (const [ax, bx] of [[1 / 3, 2 / 3], [0, 1], [0, .65], [.35, 1], [1, 0]]) for (const a of offsets) for (const b of offsets) {
        shallow.push({curve: [from, {x: from.x + dx * ax, y: from.y + a}, {x: from.x + dx * bx, y: to.y + b}, to], cost: a * a - a * b + b * b});
      }
      for (const {curve} of shallow.sort((a, b) => a.cost - b.cost)) if (clear(curve)) return serialize(curve);
    }
    const ports = point => {
      const available = lanes.filter(x => !others.some(p => segmentHitsNode(point, {x, y: point.y}, p)));
      // 极度压缩时，同列点的留白可能重叠；重叠区交给固定保护层裁掉。
      const choices = available.length ? available : lanes.filter(x => !others.some(p => p.x !== point.x && segmentHitsNode(point, {x, y: point.y}, p)));
      return [choices.filter(x => x < point.x).at(-1), choices.find(x => x > point.x)].filter(x => x !== undefined);
    };
    const preferred = (from.y + to.y) / 2;
    const guides = [];
    for (const left of ports(from)) for (const right of ports(to)) {
      if (left < Math.min(from.x, to.x) || left > Math.max(from.x, to.x) || right < Math.min(from.x, to.x) || right > Math.max(from.x, to.x)) continue;
      const lowX = Math.min(left, right), highX = Math.max(left, right);
      const blocked = points.filter(p => p.x + p.r + handoffGap >= lowX && p.x - p.r - handoffGap <= highX).map(p => [p.y - p.r - handoffGap, p.y + p.r + handoffGap]).sort((a, b) => a[0] - b[0]);
      const merged = [];
      blocked.forEach(interval => {
        if (merged.length && interval[0] <= merged.at(-1)[1]) merged.at(-1)[1] = Math.max(merged.at(-1)[1], interval[1]);
        else merged.push(interval.slice());
      });
      const rails = [preferred, 3, height - 3, ...merged.flatMap(([a, b]) => [a - .3, b + .3])];
      for (const y of rails) {
        if (y < 3 || y > height - 3 || merged.some(([a, b]) => y >= a && y <= b)) continue;
        const slack = Math.abs(dy) <= 28 ? 24 : 0;
        if (y < Math.min(from.y, to.y) - slack || y > Math.max(from.y, to.y) + slack) continue;
        const cost = Math.abs(left - from.x) + Math.abs(right - to.x) + Math.abs(right - left) + Math.abs(y - from.y) + Math.abs(y - to.y) + Math.abs(y - preferred) * .01;
        guides.push({cost, left, right, y});
      }
    }
    if (dy > 0) for (const entry of [12, 8, 20, 28, 4, 2, 1]) {
      const firstY = from.y + Math.min(entry, dy / 4), lastY = to.y - Math.min(entry, dy / 4);
      for (const guide of guides.sort((a, b) => a.cost - b.cost)) {
        if (guide.y < firstY || guide.y > lastY) continue;
        const starts = [...new Set([firstY, ...[128, 64, 32, 16, 8, 2].map(n => Math.max(firstY, guide.y - n))])];
        const ends = [...new Set([lastY, ...[128, 64, 32, 16, 8, 2].map(n => Math.min(lastY, guide.y + n))])];
        const windows = starts.flatMap(start => ends.map(end => ({start, end}))).filter(w => w.end > w.start).sort((a, b) => (b.end - b.start) - (a.end - a.start));
        for (const {start, end} of windows) {
          const curves = [...flowSweep(from, {x: guide.left, y: firstY}, 2, 0), ...flowSweep({x: guide.left, y: firstY}, {x: guide.left, y: start}), ...flowSweep({x: guide.left, y: start}, {x: guide.right, y: end}), ...flowSweep({x: guide.right, y: end}, {x: guide.right, y: lastY}), ...flowSweep({x: guide.right, y: lastY}, to, 0, 2)];
          if (curves.every(clear)) return curves.map((curve, i) => i ? serialize(curve).replace(/^M[^ ]+ /, '') : serialize(curve)).join(' ');
        }
      }
    }
    // 压缩后整列留白可能连成屏障；此时只允许整段弧线绕过，仍不拼接折角。
    const arcs = [], offsets = [0, -16, 16, -32, 32, -48, 48, -64, 64, -80, 80, -96, 96, -128, 128, -192, 192, -256, 256];
    for (const [ax, bx] of [[1 / 3, 2 / 3], [0, 1], [0, .65], [.35, 1], [1, 0]]) for (const a of offsets) for (const b of offsets) arcs.push({curve: [from, {x: from.x + dx * ax, y: from.y + a}, {x: from.x + dx * bx, y: to.y + b}, to], cost: a * a - a * b + b * b});
    for (const {curve} of arcs.sort((a, b) => a.cost - b.cost)) if (clear(curve)) return serialize(curve);
    const swap = p => ({x: p.y, y: p.x});
    for (const guide of guides.sort((a, b) => a.cost - b.cost)) {
      for (const ratio of [.5, .35, .65, .25, .75]) {
        const crest = {x: guide.y, y: from.x + dx * ratio};
        const curves = [...flowSweep(swap(from), crest), ...flowSweep(crest, swap(to))].map(curve => curve.map(swap));
        if (curves.every(clear)) return curves.map((curve, i) => i ? serialize(curve).replace(/^M[^ ]+ /, '') : serialize(curve)).join(' ');
      }
      const curves = [...flowSweep(swap(from), {x: guide.y, y: guide.left}, 2, 0), ...flowSweep({x: guide.y, y: guide.left}, {x: guide.y, y: guide.right}), ...flowSweep({x: guide.y, y: guide.right}, swap(to), 0, 2)].map(curve => curve.map(swap));
      if (curves.every(clear)) return curves.map((curve, i) => i ? serialize(curve).replace(/^M[^ ]+ /, '') : serialize(curve)).join(' ');
    }
    // 节点本身重叠的极限情况下，固定保护层仍保留每个实际节点的留白。
    return serialize(preferredCurve);
  }
  // 国办发明电〔2025〕7号：https://www.gov.cn/zhengce/content/202511/content_7047090.htm
  // 按年维护官方放假调休安排；未收录年份只标周末，不推算农历节日。
  const mainlandCalendar = {
    "2026": {
      holidays: [
        ["01-01", "01-03", "元旦"], ["02-15", "02-23", "春节"],
        ["04-04", "04-06", "清明节"], ["05-01", "05-05", "劳动节"],
        ["06-19", "06-21", "端午节"], ["09-25", "09-27", "中秋节"],
        ["10-01", "10-07", "国庆节"]
      ],
      workingWeekends: ["01-04", "02-14", "02-28", "05-09", "09-20", "10-10"]
    }
  };
  const JournalView = {
    restDayLabel(date) {
      const calendar = mainlandCalendar[date.slice(0, 4)], day = date.slice(5);
      if (calendar?.workingWeekends.includes(day)) return "";
      const holiday = calendar?.holidays.find(([start, end]) => day >= start && day <= end);
      if (holiday) return holiday[2];
      return [0, 6].includes(new Date(date + "T00:00:00Z").getUTCDay()) ? "周末" : "";
    },
    init(manifest, app) {
      this.app = app;
      this.days = manifest.journal || [];
      this.registry = manifest.chains || {tracks: [], chains: [], handoffs: []};
      this.chains = new Map(this.registry.chains.map(c => [c.id, c]));
      this.reports = new Map(manifest.daily.map(d => [d.date, d]));
      this.selected = null;
      this.selection = null;
      this.floatingNotes = new window.JournalFloatingNotes(cid => {
        if (this.selection?.kind === "chain") { this.focusChainEvent(cid); return; }
        if (this.selection?.kind === "day") {
          this.noteFocus = cid; this.noteFocusDate = this.selected;
          this.highlightAtlas();
        } else this.select(this.selected, false, cid);
        if (document.querySelector(".journal-scroller").clientWidth < 600) this.scrollAtlasDay(this.selected);
      });
      let preferences = {};
      try { preferences = JSON.parse(localStorage.getItem("journal-atlas-preferences") || "{}"); } catch (_) { /* 无可用设置时使用默认值。 */ }
      this.window = ["1m", "3m"].includes(preferences?.window) ? preferences.window : "all";
      this.density = this.densityFromPreferences(preferences);
      if (Number.isFinite(preferences?.density) && preferences?.densityVersion !== densityPreferences.version) this.savePreferences();
      this.chain = "";
      this.query = "";
      this.evidence = new Map();
      this.mode = matchMedia("(min-width: 860px)").matches ? "atlas" : "list";
      $("journal-title").textContent = $("tab-journal").textContent;
      $("journal-chain").innerHTML = '<option value="">全部链条</option>' + this.registry.tracks.map(t =>
        `<optgroup label="${esc(t.label)}">${this.registry.chains.filter(c => c.track === t.id).map(c => `<option value="${esc(c.id)}">${esc(c.label)}</option>`).join("")}</optgroup>`).join("");
      $("journal-window").addEventListener("change", e => { this.window = e.target.value; this.savePreferences(); this.render(); this.writeHash(); });
      $("journal-density").addEventListener("change", e => { this.density = Number(e.target.value); this.savePreferences(); this.render(); });
      document.querySelector(".journal-scroller").addEventListener("wheel", e => this.zoomAtlas(e), {passive: false});
      $("journal-chain").addEventListener("change", e => this.focusChain(e.target.value));
      $("journal-clear").addEventListener("click", () => this.clearSelection());
      $("journal-find").addEventListener("input", e => { this.query = e.target.value; this.render(); });
      document.querySelectorAll("[data-journal-view]").forEach(button => button.addEventListener("click", () => {
        this.mode = button.dataset.journalView; this.render(); this.writeHash();
      }));
      $("view-journal").addEventListener("click", e => {
        $("view-journal").classList.toggle("is-keyboard", e.detail === 0);
        const handoff = e.target.closest("[data-journal-handoff]");
        if (handoff) {
          const type = handoff.dataset.journalHandoff;
          const active = this.selection?.kind === "handoff" && this.selection.type === type;
          this.chain = ""; this.selected = null;
          this.selection = active ? null : {kind: "handoff", type};
          this.render(); this.writeHash();
          return;
        }
        const retry = e.target.closest("[data-journal-evidence]");
        if (retry) this.loadEvidence(retry.dataset.journalEvidence, true);
        const point = e.target.closest("[data-journal-point]");
        if (point) {
          this.select(point.dataset.date, false, point.dataset.journalPoint);
          return;
        }
        const day = e.target.closest("[data-journal-day]");
        if (day) { e.preventDefault(); this.select(day.dataset.journalDay, !day.closest("#journal-figure")); return; }
        const chain = e.target.closest("[data-journal-chain]");
        if (chain) { this.focusChain(chain.dataset.journalChain); return; }
        const row = e.target.closest("tr[data-date]");
        if (row && !e.target.closest("a,button")) this.select(row.dataset.date, true);
      });
      document.addEventListener("click", e => {
        if (!this.selection || !$("view-journal").classList.contains("is-active") || e.defaultPrevented || e.detail === 0) return;
        if (e.target.closest("a, button, input, select, textarea, label, summary, details, [role='button'], [contenteditable], .journal-controls, .journal-annotation, .journal-day-context, #journal-detail, tr[data-date]")) return;
        if (!window.getSelection()?.isCollapsed) return;
        this.clearSelection();
      });
      $("view-journal").addEventListener("keydown", e => {
        $("view-journal").classList.add("is-keyboard");
        if (e.key === "Escape") { this.clearSelection(); return; }
        if (e.target.closest("input, select, textarea, .journal-note-tools, .journal-floating-head")) return;
        if (e.target.closest("[data-journal-handoff]")) return;
        if (!e.target.closest("#journal-figure")) return;
        const day = e.target.closest("[data-journal-day]");
        if (day && ["Enter", " "].includes(e.key)) { e.preventDefault(); this.select(day.dataset.journalDay); return; }
        if (!["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown"].includes(e.key)) return;
        e.preventDefault();
        if (this.selection?.kind === "chain") {
          const events = this.atlas.active.get(this.chain) || [], current = events.findIndex(d => d.date === this.chainNoteDate);
          const step = ["ArrowUp", "ArrowLeft"].includes(e.key) ? -1 : 1;
          if (events.length) this.focusChainEvent(events[(Math.max(0, current) + step + events.length) % events.length].date);
          return;
        }
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
        this.resizeFrame = requestAnimationFrame(() => { this.renderAtlas(); this.revealPointNote(); });
      });
      this.resizeObserver.observe($("view-journal"));
    },
    densityFromPreferences(preferences) {
      const density = preferences?.density;
      if (!Number.isFinite(density) || density < densityRange.min || density > densityRange.max) return densityPreferences.standard;
      if (preferences?.densityVersion === densityPreferences.version) return density;
      return Math.max(densityRange.min, Math.min(densityRange.max, density * densityPreferences.standard / densityPreferences.legacyStandard));
    },
    savePreferences() {
      try { localStorage.setItem("journal-atlas-preferences", JSON.stringify({density: this.density, window: this.window, densityVersion: densityPreferences.version})); } catch (_) { /* 离线或禁用存储时仍可操作。 */ }
    },
    syncDensityControl() {
      const control = $("journal-density"), custom = $("journal-density-custom");
      const preset = Array.from(control.options).some(option => option !== custom && Number(option.value) === this.density);
      custom.hidden = preset;
      custom.value = preset ? "" : String(this.density);
      custom.textContent = `自定义（${Math.round(this.density / densityPreferences.standard * 100)}%）`;
      control.value = String(this.density);
    },
    zoomAtlas(event) {
      const svg = document.querySelector(".journal-atlas");
      if (!event.ctrlKey || !event.deltaY || this.mode !== "atlas" || !$("view-journal").classList.contains("is-active") || !svg || !this.atlas) return;
      event.preventDefault();
      const unit = event.deltaMode === 1 ? 16 : event.deltaMode === 2 ? window.innerHeight : 1;
      const delta = Math.max(-120, Math.min(120, event.deltaY * unit));
      const density = Math.max(densityRange.min, Math.min(densityRange.max, this.density * Math.exp(-delta * .0015)));
      if (density === this.density) return;
      if (!this.zoomFrame) {
        const dayOffset = (event.clientY - svg.getBoundingClientRect().top - this.atlas.top) / this.density;
        const clientY = event.clientY;
        this.zoomFrame = requestAnimationFrame(() => {
          this.zoomFrame = 0;
          const scroller = document.querySelector(".journal-scroller"), scrollLeft = scroller.scrollLeft;
          const focus = document.activeElement;
          const focusSelector = focus?.matches(".journal-atlas") ? ".journal-atlas" :
            focus?.matches(".journal-day-hit") ? `.journal-day-hit[data-journal-day="${CSS.escape(focus.dataset.journalDay)}"]` :
            focus?.matches(".journal-chain-label") ? `.journal-chain-label[data-journal-chain="${CSS.escape(focus.dataset.journalChain)}"]` : null;
          this.syncDensityControl();
          this.renderAtlas();
          scroller.scrollLeft = scrollLeft;
          document.querySelector(".journal-head-scroller").scrollLeft = scroller.scrollLeft;
          if (focusSelector) document.querySelector(focusSelector)?.focus({preventScroll: true});
          const updated = document.querySelector(".journal-atlas");
          if (this.mode === "atlas" && updated) {
            const top = updated.getBoundingClientRect().top + this.atlas.top + dayOffset * this.density - clientY;
            window.scrollBy({top, behavior: "instant"});
          }
          this.savePreferences();
        });
      }
      this.density = density;
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
      if (this.chain) requestAnimationFrame(() => this.mode === "atlas" && this.revealChainNote(this.chainNoteDate));
      if (key) requestAnimationFrame(() => {
        if (this.mode === "atlas") { this.scrollAtlasDay(key); this.revealPointNote(); }
        else $("journal-detail").scrollIntoView({block: "start"});
      });
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
      const sameDay = this.mode === "atlas" && this.selected === key && !this.chain && ["day", "point"].includes(this.selection?.kind);
      this.selected = key;
      this.chain = "";
      this.selection = cid ? {kind: "point", date: key, chain: cid} : {kind: "day", date: key};
      this.query = ""; $("journal-find").value = "";
      if (!this.visibleDays(true).some(d => d.date === key)) this.window = "all";
      if (scroll) this.mode = "atlas";
      if (sameDay && !scroll) { this.highlightAtlas(); this.renderDetail(); this.writeHash(); this.revealPointNote(); return; }
      this.render(); this.writeHash();
      this.revealPointNote();
      if (scroll) {
        this.scrollAtlasDay(key);
        const scroller = document.querySelector(".journal-scroller");
        if (cid) scroller.scrollLeft = Math.max(0, this.atlas.positions.get(cid) - scroller.clientWidth / 2);
      }
    },
    scrollAtlasDay(key) {
      const canvas = document.querySelector(".journal-canvas");
      if (!canvas || !this.atlas) return;
      const header = document.querySelector(".journal-atlas-header").offsetHeight;
      const target = Math.max(header + 170, window.innerHeight * .78);
      window.scrollBy({top: canvas.getBoundingClientRect().top + this.atlas.y(key) - target, behavior: "instant"});
    },
    focusChain(cid) {
      if (!cid) { this.clearSelection(); return; }
      this.chain = this.chains.has(cid) ? cid : "";
      this.selected = null;
      this.selection = this.chain ? {kind: "chain", chain: this.chain} : null;
      this.render(); this.writeHash();
      if (this.mode === "atlas") this.revealChainNote(this.chainNoteDate);
    },
    focusChainEvent(date) {
      if (!this.atlas?.active.get(this.chain)?.some(d => d.date === date)) return;
      this.chainNoteDate = date; this.selection = {kind: "chain", chain: this.chain, date};
      this.highlightAtlas(); this.writeHash(); this.revealChainNote(date);
    },
    revealChainNote(date) {
      this.revealFloatingNote(`.journal-chain-note[data-date="${CSS.escape(date)}"]`, date);
    },
    revealPointNote() {
      if (this.selection?.kind !== "point") return;
      this.revealFloatingNote(`.journal-floating-note[data-note-id="${CSS.escape(this.selection.chain)}"]`, this.selection.date);
    },
    revealFloatingNote(selector, date) {
      const card = document.querySelector(selector);
      if (!card || card.hidden || !this.floatingNotes.open) return;
      const top = document.querySelector(".journal-atlas-header").getBoundingClientRect().bottom + 16;
      const y = card.offsetTop + card.parentElement.getBoundingClientRect().top;
      const box = {top: y, bottom: y + card.offsetHeight};
      const pointY = card.parentElement.getBoundingClientRect().top + this.atlas.y(date);
      const first = Math.min(box.top, pointY - 20), last = Math.max(box.bottom, pointY + 20);
      if (first < top || last > innerHeight - 16) window.scrollBy({top: (last - first < innerHeight - top - 28 ? first : box.top) - top - 12, behavior: "instant"});
    },
    clearSelection() {
      this.chain = ""; this.selected = null; this.selection = null;
      this.render(); this.writeHash();
    },
    pointNote(day, cid) {
      const chain = this.chains.get(cid);
      return day.chain_notes?.[cid] || {note: "", outcome: chain?.fate || "landed", outcome_note: ["dropped", "parked"].includes(chain?.fate) ? chain.fate_note || "" : ""};
    },
    pointWeight(day, cid) {
      const value = day.chain_weights?.[cid]?.value;
      return Number.isFinite(value) && value >= 0 ? value : null;
    },
    pointRadius(day, cid) {
      const value = this.pointWeight(day, cid);
      return (3 + 2.25 * Math.log2(1 + (value ?? 0))) / 2;
    },
    weightLabel(day, cid) {
      const weight = day.chain_weights?.[cid], value = this.pointWeight(day, cid);
      if (value === null) return "归属提交量待核";
      if (!value) return "当日无已归属提交";
      const number = Number.isInteger(value) ? String(value) : value.toFixed(2).replace(/0+$/, "").replace(/\.$/, "");
      return `归属提交量 ${number}${weight.shared ? `（含 ${weight.shared} 条跨链提交的份额）` : ""}`;
    },
    pointEvidence(day, cid) {
      const evidence = day.chain_evidence?.[cid];
      return evidence && ["artifact", "discussion", "pending"].includes(evidence.status) ? evidence : {status: "pending", kinds: [], artifacts: [], discussions: []};
    },
    evidenceLabel(day, cid) {
      return {artifact: "有可查产物", discussion: "仅见交流", pending: "证据待核"}[this.pointEvidence(day, cid).status];
    },
    pointEvidenceHtml(day, cid, brief = false) {
      const e = this.pointEvidence(day, cid);
      const badge = `<span class="journal-evidence-status is-${e.status}"><i aria-hidden="true"></i>${this.evidenceLabel(day, cid)}</span>`;
      if (brief) return badge;
      const counts = [e.commit_count ? `${e.commit_count} 条提交` : "", e.document_count ? `${e.document_count} 份文档` : "", e.session_count ? `${e.session_count} 段交流` : ""].filter(Boolean).join("，");
      const refs = items => `<ul>${items.map(ref => {
        const kind = ref.kind === "session" ? "会话" : ref.kind === "commit" ? "提交" : "文档";
        const title = esc(ref.title);
        const link = /^https:\/\/github\.com\//.test(ref.url || "") ? `<a class="journal-source-link" href="${esc(ref.url)}" target="_blank" rel="noopener noreferrer"><span class="journal-link-kind">${kind}</span><span class="journal-source-title">${title}</span></a>` : title;
        return `<li>${link}<small>${esc(ref.label || "来源登记")}</small></li>`;
      }).join("")}</ul>`;
      return `<div class="journal-point-evidence"><div class="journal-evidence-heading">${badge}${e.kinds?.length ? `<span class="journal-evidence-types">${e.kinds.map(esc).join(" / ")}</span>` : ""}</div><details class="journal-point-sources"><summary>查看依据${counts ? `<small>${esc(counts)}</small>` : ""}</summary><section><h5>产物</h5>${e.artifacts?.length ? refs(e.artifacts) : `<p>${e.status === "pending" ? "产物来源尚待核对。" : "当前未关联文件或提交。"}</p>`}</section><section><h5>交流与决定</h5>${e.discussions?.length ? refs(e.discussions) : '<p>尚未关联原始会话。</p>'}</section>${e.commit_count > 2 || e.document_count > 2 || e.session_count > 2 ? `<p class="journal-point-source-note">这里列出部分入口，${this.selection?.kind === "point" ? "完整提交可点击日期后查看原始记录" : "完整提交见下方原始记录"}，文档和会话见来源登记。</p>` : ""}</details></div>`;
    },
    weightLegendHtml() {
      const samples = [1, 5, 20, 100].map(value => {
        const r = this.pointRadius({chain_weights: {sample: {value}}}, "sample");
        return `<span class="journal-weight-sample"><span class="journal-weight-mark"><svg width="24" height="24" viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="${23 - r}" r="${r}"/></svg></span><span>${value}</span></span>`;
      }).join("");
      return `<div class="journal-point-legends" role="group" aria-label="圆点图例"><div class="journal-weight-legend" role="group" aria-label="任务归属提交量的点径参照"><span class="journal-weight-title">归属提交量（份）</span><div class="journal-weight-scale">${samples}</div><span class="journal-weight-note">点径连续变化，采用对数刻度</span></div><div class="journal-evidence-legend" role="group" aria-label="工作点证据类型">${["artifact", "discussion", "pending"].map(status => this.pointEvidenceHtml({chain_evidence: {sample: {status}}}, "sample", true)).join("")}<span>相关汇报另列文字入口</span></div></div>`;
    },
    reportLinks(day) {
      return (day.reports_covering || (day.report ? [day.report] : [])).map(d => `<a href="#/daily/${esc(d)}">${esc(d)}</a>`).join(" ");
    },
    dayMetaHtml(day) {
      const links = this.reportLinks(day);
      return `<span>${esc(day.weekday)}</span><span>${links ? `相关汇报：${links}` : "未关联汇报"}</span><span>当天发布 ${day.reports_published?.length || 0} 篇</span>`;
    },
    chainButtons(day) {
      return day.chains.map(cid => `<button type="button" class="journal-chain-link" data-journal-chain="${esc(cid)}">${esc(this.chains.get(cid)?.short || cid)}${day.chain_confidence[cid] === "inferred" ? ' <small>待核</small>' : ""}</button>`).join(" ") || "未归类";
    },
    handoffDates(edge, from, to) {
      const target = edge.date ? to.find(d => d.date === edge.date)?.date : to[0]?.date;
      const source = edge.source_date ? from.find(d => d.date === edge.source_date)?.date : from.filter(d => d.date <= target).at(-1)?.date;
      return source && target && source <= target ? {source, target} : null;
    },
    chainReports(chain, days) {
      const dates = chain.report_coverage === "curated" ? (chain.closes_into?.daily || []) : [...days.flatMap(d => d.reports_covering || []), ...(chain.closes_into?.daily || [])];
      return [...new Set(dates)].filter(d => this.reports.has(d));
    },
    sourceLinks(refs) {
      return (refs || []).filter(ref => /^https:\/\/github\.com\//.test(ref.url || "")).map(ref => {
        const kind = this.sourceKind(ref.url);
        return `<a class="journal-source-link" data-source-kind="${kind}" href="${esc(ref.url)}" target="_blank" rel="noopener noreferrer"><span class="journal-link-kind">${this.sourceKindLabel(kind)}</span><span class="journal-source-title">${esc(ref.title)}</span></a>`;
      }).join(" ");
    },
    sourceKind(url) {
      return /\/commit\//.test(url) ? "commit" : /\/blob\//.test(url) ? "file" : "repository";
    },
    sourceKindLabel(kind) {
      return {commit: "提交", file: "文件", repository: "仓库"}[kind];
    },
    commitLink(url, sha, length = 8) {
      const short = esc(sha?.slice(0, length));
      return /^[a-f0-9]{7,40}$/.test(sha || "") && /^https:\/\/github\.com\//.test(url) ? `<a class="journal-source-link" data-source-kind="commit" href="${esc(url)}" target="_blank" rel="noopener noreferrer"><span class="journal-link-kind">提交</span><code class="journal-source-title">${short}</code></a>` : short;
    },
    prepareDayBody(root) {
      root.querySelectorAll("h1, h2, h3, h4, h5").forEach(heading => {
        const nested = document.createElement(`h${Math.min(6, Math.max(3, Number(heading.tagName.slice(1)) + 1))}`);
        for (const attribute of heading.attributes) nested.setAttribute(attribute.name, attribute.value);
        nested.append(...heading.childNodes);
        heading.replaceWith(nested);
      });
      root.querySelectorAll("li > strong:first-child").forEach(heading => {
        const next = heading.nextSibling;
        if (next?.nodeType === Node.TEXT_NODE && /^\s*[：:]/.test(next.textContent)) {
          heading.append("：");
          next.textContent = next.textContent.replace(/^\s*[：:]\s*/, "");
        }
      });
      root.querySelectorAll('a[href^="https://github.com/"]').forEach(link => {
        if (link.classList.contains("journal-source-link")) return;
        const kind = this.sourceKind(link.href), title = document.createElement("span"), label = document.createElement("span");
        title.className = "journal-source-title";
        title.append(...link.childNodes);
        label.className = "journal-link-kind";
        label.textContent = this.sourceKindLabel(kind);
        link.classList.add("journal-source-link");
        link.dataset.sourceKind = kind;
        link.append(label, title);
      });
    },
    render() {
      const focus = document.activeElement;
      const wasFocused = focus?.classList.contains("journal-atlas");
      const focusDay = focus?.getAttribute("data-journal-day");
      const focusChain = focus?.getAttribute("data-journal-chain");
      const headerFocused = focus?.classList.contains("journal-chain-label");
      const focusedNav = document.activeElement?.dataset.journalNav;
      this.visible = this.visibleDays();
      if (this.selected && !this.chain && !this.visible.some(d => d.date === this.selected)) { this.selected = null; this.selection = null; }
      $("journal-window").value = this.window;
      $("journal-chain").value = this.chain;
      this.syncDensityControl();
      document.querySelector(".journal-density-control").hidden = this.mode !== "atlas";
      $("journal-clear").hidden = !this.selection;
      const reports = new Set(this.visible.flatMap(d => d.reports_covering || []));
      $("journal-count").textContent = `${this.visible.length} 个记录日 / ${reports.size} 篇相关汇报`;
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
      if (this.mode !== "atlas" || !$("view-journal").classList.contains("is-active")) { this.floatingNotes.clear(); return; }
      this.floatingNotes.capture();
      const selectedDay = this.days.find(day => day.date === this.selected);
      const context = $("journal-day-context");
      context.hidden = !selectedDay;
      context.innerHTML = selectedDay ? `<label class="journal-selected-date"><span class="sr-only">选择工作日期</span><select aria-label="选择工作日期">${this.visibleDays(true).map(d => `<option value="${d.date}" ${d.date === selectedDay.date ? "selected" : ""}>${d.date}</option>`).join("")}</select></label>${this.dayMetaHtml(selectedDay)}` : "";
      context.onchange = e => { if (e.target.matches(".journal-selected-date select")) this.select(e.target.value, true); };
      const focusedHandoff = document.activeElement?.dataset.journalHandoff;
      const days = this.visibleDays(true);
      const scroller = document.querySelector(".journal-scroller");
      const head = document.querySelector(".journal-head-scroller");
      if (!days.length) { scroller.innerHTML = '<p class="journal-empty">暂无日志。</p>'; head.innerHTML = ""; return; }
      const previousScroll = scroller.scrollLeft;
      const num = d => Date.parse(d + "T00:00:00Z") / 86400000;
      const first = num(days[0].date), last = num(days.at(-1).date);
      const dateWidth = 86, padding = 18, gap = 12, top = 18;
      const factorFlow = ["fixed-history", "open5m", "old-factor-bank", "old-factor-calibration", "depth-match", "cancel-phase", "szse-model328", "grouped-calibration", "corrected-replay-344", "sse-v2"];
      const ordered = this.registry.tracks.flatMap(t => {
        const chains = this.registry.chains.filter(c => c.track === t.id);
        return t.id === "factor" ? chains.sort((a, b) => (factorFlow.includes(a.id) ? factorFlow.indexOf(a.id) : factorFlow.length) - (factorFlow.includes(b.id) ? factorFlow.indexOf(b.id) : factorFlow.length)) : chains;
      });
      const groups = this.registry.tracks.filter(t => ordered.some(c => c.track === t.id));
      const width = Math.max(scroller.clientWidth, dateWidth + 2 * padding + gap * Math.max(0, groups.length - 1) + ordered.length * 34);
      const colWidth = (width - dateWidth - 2 * padding - gap * Math.max(0, groups.length - 1)) / Math.max(1, ordered.length);
      const positions = new Map();
      ordered.forEach((c, i) => positions.set(c.id, dateWidth + padding + (i + .5) * colWidth + groups.findIndex(t => t.id === c.track) * gap));
      const y = d => top + (num(d) - first) * this.density;
      const height = top + (last - first) * this.density + 28, right = width - padding;
      const radius = (d, cid) => this.pointRadius(d, cid);
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
      const parts = [`<div class="journal-canvas" style="width:${width}px"><svg class="journal-atlas" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}" tabindex="0" role="group" aria-label="工作日期与任务链条" aria-describedby="journal-atlas-desc" data-days="${days.length}" data-density="${this.density}"><desc id="journal-atlas-desc">日期从上到下，${ordered.length} 条链各占一列，按六个轨道分组。底纹表示周末和中国大陆公共假期，调休补班日除外。点的大小表示该任务当天的归属提交量，使用对数压缩刻度。实心点表示有可查产物，空心点表示当前仅见交流，虚线轮廓表示证据待核；汇报另列文字入口，日期旁短刻度表示当天发布了汇报。叉号表示未采用。点击日期、列头链名或单个点查看说明；上下键换日，左右键换点，Esc 取消。清单与下方说明提供文字入口。</desc>`];
      for (let n = first; n <= last; n++) {
        const date = new Date(n * 86400000).toISOString().slice(0, 10);
        const restDay = this.restDayLabel(date);
        if (restDay) parts.push(`<rect class="journal-rest-day" data-date="${date}" data-rest-day="${esc(restDay)}" x="${dateWidth}" y="${y(date) - this.density / 2}" width="${right - dateWidth}" height="${this.density}"/>`);
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
      const points = ordered.flatMap(chain => active.get(chain.id).map(day => {
        const dropped = this.pointNote(day, chain.id).outcome === "dropped", r = radius(day, chain.id);
        const sealed = chain.fate !== "dropped" && (chain.status === "done" || chain.fate === "parked") && chain.end === day.date;
        return {chain: chain.id, date: day.date, x: positions.get(chain.id), y: y(day.date), r: dropped ? Math.max(3.4, r) + 1 : sealed ? Math.max(r, Math.sqrt(Math.PI) * r / 2 + .7) : r, square: dropped || sealed};
      }));
      const columns = ordered.map(chain => ({x: positions.get(chain.id), r: Math.max(0, ...points.filter(p => p.chain === chain.id).map(p => p.r))}));
      const lanes = [dateWidth + 4, ...columns.slice(1).map((column, i) => (columns[i].x + columns[i].r + column.x - column.r) / 2), width - 4].filter(x => points.every(p => Math.abs(x - p.x) > p.r + handoffGap));
      const pointByKey = new Map(points.map(p => [`${p.chain}:${p.date}`, p]));
      // 留白不随无关链条一起淡化，聚焦后的粗线也不能盖住点。
      parts.push(`<defs><mask id="journal-handoff-clearance" maskUnits="userSpaceOnUse" x="0" y="0" width="${width}" height="${height}" style="mask-type:luminance"><rect width="${width}" height="${height}" fill="white"/>${points.map(p => p.square ? `<rect x="${p.x - p.r - 3.2}" y="${p.y - p.r - 3.2}" width="${2 * (p.r + 3.2)}" height="${2 * (p.r + 3.2)}" fill="black"/>` : `<circle cx="${p.x}" cy="${p.y}" r="${p.r + 3.2}" fill="black"/>`).join("")}</mask></defs>`);
      this.registry.handoffs.forEach(edge => {
        const from = active.get(edge.from), to = active.get(edge.to);
        if (!from?.length || !to?.length) return;
        const dates = this.handoffDates(edge, from, to);
        if (!dates) return;
        const {source, target} = dates;
        const dash = edge.type === "派生" ? "4 3" : edge.type === "依赖解除" ? "1 3" : edge.type === "收口" ? "7 2 1 2" : (edge.confidence === "inferred" ? "2 5" : "");
        const path = routeHandoff(pointByKey.get(`${edge.from}:${source}`), pointByKey.get(`${edge.to}:${target}`), points, lanes, height);
        parts.push(`<g class="journal-unit journal-handoff" data-chains="${esc(edge.from)} ${esc(edge.to)}" data-type="${esc(edge.type)}" data-date="${target}" data-source-date="${source}" mask="url(#journal-handoff-clearance)"><path class="journal-halo" d="${path}"/><path class="journal-handoff-path" stroke-dasharray="${dash}" d="${path}"/></g>`);
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
            const r = radius(day, chain.id), cy = y(day.date), dropped = this.pointNote(day, chain.id).outcome === "dropped";
            parts.push(`<circle class="journal-dot-halo" cx="${cx}" cy="${cy}" r="${r + 1.8}"/>`);
            if (dropped) {
              const a = Math.max(3.4, r);
              parts.push(`<path class="journal-dot journal-cross" data-date="${day.date}" data-chain="${esc(chain.id)}" d="M${cx - a},${cy - a} L${cx + a},${cy + a} M${cx + a},${cy - a} L${cx - a},${cy + a}"/>`);
            } else parts.push(`<circle class="journal-dot is-${this.pointEvidence(day, chain.id).status}" data-evidence="${this.pointEvidence(day, chain.id).status}" data-date="${day.date}" data-chain="${esc(chain.id)}" data-weight="${this.pointWeight(day, chain.id) ?? ""}" cx="${cx}" cy="${cy}" r="${r}"/>`);
          });
          if (chain.fate !== "dropped" && (chain.status === "done" || chain.fate === "parked") && chain.end === dates.at(-1).date) {
            const finalDay = dates.at(-1), side = Math.sqrt(Math.PI) * radius(finalDay, chain.id);
            parts.push(`<rect class="journal-seal${chain.fate === "parked" ? " is-parked" : ""}" x="${cx - side / 2}" y="${y(finalDay.date) - side / 2}" width="${side}" height="${side}"/>`);
          }
        }
        parts.push("</g>");
      });
      const pointHitWidth = Math.min(28, colWidth);
      ordered.forEach(chain => active.get(chain.id).forEach(day => parts.push(`<rect class="journal-point-hit" data-journal-point="${esc(chain.id)}" data-date="${day.date}" x="${positions.get(chain.id) - pointHitWidth / 2}" y="${y(day.date) - this.density / 2}" width="${pointHitWidth}" height="${this.density}" role="button" tabindex="-1" aria-label="${day.date}，${esc(chain.label)}，${esc(this.pointNote(day, chain.id).note || day.headline)}，${esc(this.weightLabel(day, chain.id))}，${this.evidenceLabel(day, chain.id)}"/>`)));
      parts.push('<g class="journal-selection-overlay" aria-hidden="true"></g></svg><div class="journal-annotations"></div></div>');
      scroller.innerHTML = parts.join("");
      scroller.scrollLeft = previousScroll;
      head.scrollLeft = scroller.scrollLeft;
      scroller.onscroll = () => { head.scrollLeft = scroller.scrollLeft; this.floatingNotes.onScroll(); };
      head.onscroll = () => { if (head.scrollLeft !== scroller.scrollLeft) scroller.scrollLeft = head.scrollLeft; };
      document.querySelector("#journal-figure figcaption").innerHTML = '<p>日期从上往下，每条链代表一项持续的工作。浅色底纹表示周末和中国大陆公共假期，调休补班日不着底纹。点的大小表示该任务当天的归属提交量，点径采用对数压缩刻度。单任务提交计1份，明确的跨链提交等分；待核记录不计入。没有已归属提交时保留最小定位点，不表示当天没有做这项工作。准确数值见点卡，逐条依据见下方“任务归属明细”。实心点表示有可查产物，空心点表示当前仅见交流记录，虚线轮廓表示证据待核。文档落盘但无提交时仍为实心；有产物和交流时两组依据分别保留。相关汇报在日期与说明中另列文字入口；日期旁短刻度表示当天发布了汇报。超过 3 天的记录空档用虚线。实心方块表示这段记录结束，空心方块表示暂搁；叉号与点线只标注未采用的具体方案。</p><p>点击日期看当天各项工作，点击列头链名看整条链，点击单个点看该项记录。点击图例突出对应的交接线，再次点击恢复。点击空白处或按 Esc 取消选中。上下键换日，左右键切换当天的点。</p><div class="journal-handoff-legend" role="group" aria-label="任务关系线型">' + [["延续", "继续开展", ""], ["派生", "扩展研究", "4 3"], ["依赖解除", "提供输入", "1 3"], ["收口", "汇入报告", "7 2 1 2"]].map(([type, label, dash]) => `<button type="button" data-journal-handoff="${type}" aria-pressed="${this.selection?.kind === "handoff" && this.selection.type === type}"><svg aria-hidden="true" viewBox="0 0 34 8"><path d="M1 4 H33" stroke-dasharray="${dash}"/></svg>${label}</button>`).join("") + '<span>仅按记录顺序关联的连线会注明</span></div>';
      document.querySelector("#journal-figure figcaption").insertAdjacentHTML("afterbegin", this.weightLegendHtml());
      document.querySelector("#journal-figure figcaption p:nth-of-type(2)").textContent = "点击日期展开当天各项工作，点击列头链名展开整条链；点击圆点只查看该点的工作说明。整日或整链展开后，点击浮窗标题聚焦其中一项。拖动浮窗标题调整位置，双击恢复自动排布；标题上的方向键可微调位置。点击图例突出对应的交接线，再次点击恢复。点击空白处或按 Esc 取消选中。在图上用上下键换日、左右键切换当天任务。";
      this.atlas = {y, positions, days, height, width, top, dateWidth, right, radius, ordered, active};
      if (this.chain && !this.visible.length) document.querySelector("#journal-figure figcaption").insertAdjacentHTML("beforeend", '<p class="journal-window-empty" role="status">此时间窗内没有这条链的记录。下方链条卡展示它的全部历史；可将时间窗改为“全部”查看图谱。</p>');
      this.highlightAtlas();
      if (focusedHandoff) document.querySelector(`[data-journal-handoff="${CSS.escape(focusedHandoff)}"]`)?.focus({preventScroll: true});
    },
    highlightAtlas() {
      const sel = this.selection, a = this.atlas;
      if (!a) return;
      const handoffFocus = sel?.kind === "handoff";
      const day = this.days.find(d => d.date === sel?.date);
      const live = new Set(["chain", "point"].includes(sel?.kind) ? [sel.chain] : day?.chains || []);
      $("view-journal").classList.toggle("has-floating-notes", sel?.kind === "chain" || Boolean(day) && ["day", "point"].includes(sel?.kind));
      document.querySelectorAll(".journal-chain-label").forEach(label => {
        const lit = live.has(label.dataset.journalChain);
        label.classList.toggle("is-selected", lit);
        label.classList.toggle("is-dimmed", Boolean(sel) && !handoffFocus && !lit);
        label.setAttribute("aria-pressed", String(lit));
      });
      document.querySelectorAll(".journal-unit").forEach(g => {
        const lit = handoffFocus ? g.classList.contains("journal-handoff") && g.dataset.type === sel.type : g.dataset.chains.split(" ").some(id => live.has(id));
        g.classList.toggle("is-dimmed", Boolean(sel) && !lit);
        g.classList.toggle("is-focused", (sel?.kind === "chain" || handoffFocus) && lit);
        g.classList.toggle("is-handoff-context", handoffFocus && g.classList.contains("journal-chain-unit"));
      });
      document.querySelectorAll(".journal-day-hit").forEach(hit => hit.setAttribute("aria-pressed", String(hit.dataset.journalDay === sel?.date)));
      document.querySelectorAll(".journal-date-label").forEach(label => label.classList.toggle("is-selected", label.dataset.date === sel?.date));
      const svg = document.querySelector(".journal-atlas"), overlay = svg.querySelector(".journal-selection-overlay");
      const annotations = document.querySelector(".journal-annotations");
      overlay.replaceChildren();
      if (!sel || !["day", "point", "chain"].includes(sel.kind)) this.floatingNotes.clear();
      if (!sel) return;
      if (sel.kind === "chain") {
        const scroller = document.querySelector(".journal-scroller");
        const cx = a.positions.get(sel.chain), dates = a.active.get(sel.chain) || [];
        if (!dates.length) { this.floatingNotes.clear(); return; }
        const unit = [...svg.querySelectorAll(".journal-chain-unit")].find(g => g.dataset.chains === sel.chain);
        if (unit) svg.insertBefore(unit, svg.querySelector(".journal-point-hit"));
        const middle = (Math.max(0, document.querySelector(".journal-atlas-header").getBoundingClientRect().bottom) + innerHeight) / 2 - svg.getBoundingClientRect().top;
        const focused = dates.some(d => d.date === this.chainNoteDate) ? this.chainNoteDate : dates.reduce((best, d) => Math.abs(a.y(d.date) - middle) < Math.abs(a.y(best.date) - middle) ? d : best).date;
        this.chainNoteDate = focused;
        const lookup = new Map(dates.map(d => [d.date, d])), context = $("journal-day-context");
        context.hidden = false;
        context.innerHTML = `<strong>${esc(this.chains.get(sel.chain)?.short)}</strong><label class="journal-selected-date"><span class="sr-only">选择链条事件</span><select aria-label="选择链条事件">${dates.map(d => `<option value="${d.date}" ${d.date === focused ? "selected" : ""}>${d.date}</option>`).join("")}</select></label>`;
        context.onchange = e => { if (e.target.matches("select")) this.focusChainEvent(e.target.value); };
        let lastLabelY = -Infinity;
        overlay.innerHTML = dates.map((d, i) => {
          const cy = a.y(d.date), r = a.radius(d, sel.chain), active = d.date === focused;
          const numbered = active || cy - lastLabelY >= 18 && Math.abs(cy - a.y(focused)) >= 18;
          if (numbered) lastLabelY = cy;
          return `${active ? `<circle class="journal-selection-ring" data-date="${d.date}" data-chain="${esc(sel.chain)}" cx="${cx}" cy="${cy}" r="${r + 4}"/>` : ""}${numbered ? `<g class="journal-point-letter${active ? " is-focused" : ""}"><rect x="${cx - 39}" y="${cy - 7}" width="24" height="14" rx="2"/><text x="${cx - 27}" y="${cy + 4}" text-anchor="middle">${String(i + 1).padStart(2, "0")}</text></g>` : ""}`;
        }).join("");
        this.floatingNotes.render({mode: "chain", group: `chain:${sel.chain}`, chain: sel.chain, atlas: a, ids: dates.map(d => d.date), focused, day: dates[0], dayFor: id => lookup.get(id), anchor: id => ({x: cx, y: a.y(id), radius: a.radius(lookup.get(id), sel.chain)}), svg, annotations, canvas: annotations.parentElement, scroller, context, points: a.ordered.flatMap(c => a.active.get(c.id).map(d => ({x: a.positions.get(c.id), y: a.y(d.date)}))), name: id => `${id.slice(5)} ${lookup.get(id).weekday}`, note: id => this.pointNote(lookup.get(id), sel.chain), weight: id => this.pointWeight(lookup.get(id), sel.chain), evidence: (id, brief) => this.pointEvidenceHtml(lookup.get(id), sel.chain, brief), reports: id => this.reportLinks(lookup.get(id)), onReveal: () => this.revealChainNote(this.chainNoteDate)});
        return;
      }
      if (!day) return;
      const ids = (sel.kind === "point" ? day.chains.filter(cid => cid === sel.chain) : [...day.chains]).sort((x, z) => a.positions.get(x) - a.positions.get(z));
      if (!ids.length) { this.floatingNotes.clear(); return; }
      const cy = a.y(day.date);
      const focused = sel.kind === "point" ? sel.chain : this.noteFocusDate === day.date && ids.includes(this.noteFocus) ? this.noteFocus : ids.reduce((best, cid) => this.pointWeight(day, cid) > this.pointWeight(day, best) ? cid : best, ids[0]);
      this.noteFocus = focused; this.noteFocusDate = day.date;
      const paths = sel.kind === "day" ? [`<path class="journal-selection-line" d="M${a.dateWidth},${cy} H${a.right}"/>`] : [];
      ids.forEach((cid, i) => {
        const cx = a.positions.get(cid), radius = a.radius(day, cid), active = cid === focused;
        if (this.pointNote(day, cid).outcome !== "dropped") paths.push(`<circle class="journal-active-point is-${this.pointEvidence(day, cid).status}" data-evidence="${this.pointEvidence(day, cid).status}" cx="${cx}" cy="${cy}" r="${radius}"/>`);
        if (active) paths.push(`<circle class="journal-selection-ring" data-date="${day.date}" data-chain="${esc(cid)}" cx="${cx}" cy="${cy}" r="${radius + 4}"/>`);
        if (sel.kind === "day") paths.push(`<g class="journal-point-letter${active ? " is-focused" : ""}"><rect x="${cx - 8}" y="${cy + 10}" width="16" height="17" rx="2"/><text x="${cx}" y="${cy + 23}" text-anchor="middle">${String.fromCharCode(65 + i)}</text></g>`);
      });
      overlay.innerHTML = paths.join("");
      this.floatingNotes.render({mode: sel.kind, group: `${sel.kind}:${day.date}${sel.kind === "point" ? ":" + sel.chain : ""}`, atlas: a, ids, focused, day, svg, annotations, canvas: annotations.parentElement, scroller: document.querySelector(".journal-scroller"), context: $("journal-day-context"), points: a.ordered.flatMap(c => a.active.get(c.id).map(d => ({x: a.positions.get(c.id), y: a.y(d.date)}))), name: cid => this.chains.get(cid)?.short || cid, note: cid => this.pointNote(day, cid), weight: cid => this.pointWeight(day, cid), evidence: (cid, brief) => this.pointEvidenceHtml(day, cid, brief), reports: this.reportLinks(day), onReveal: () => this.scrollAtlasDay(day.date)});
    },
    annotationHtml(day, cid, width, extra = "") {
      const note = this.pointNote(day, cid), dropped = note.outcome === "dropped";
      return `<article class="journal-annotation ${extra}${dropped ? " is-dropped" : ""}" data-annotation-chain="${esc(cid)}" data-date="${day.date}" style="width:${width}px"><p><time>${day.date.slice(5)}</time> ${esc(this.chains.get(cid)?.short)}</p><strong>${esc(note.note || "注解待补")}</strong>${this.pointEvidenceHtml(day, cid, true)}<small>${esc(this.weightLabel(day, cid))}</small>${dropped ? '<span class="journal-fate-badge">本条方案未采用</span>' : ""}</article>`;
    },
    renderList() {
      $("journal-list").innerHTML = this.visible.length ? `<table><caption class="sr-only">按真实工作日期排列的日志</caption><thead><tr><th scope="col">日期</th><th scope="col">这天做了什么</th><th scope="col">链条</th><th scope="col">提交</th><th scope="col">汇报</th></tr></thead><tbody>${this.visible.map(d => `<tr class="${d.report ? "has-report" : ""}" data-date="${d.date}" ${d.date === this.selected ? 'aria-current="date"' : ""}><td><a href="#/journal/${d.date}" data-journal-day="${d.date}">${d.date}</a><small>${esc(d.weekday)}</small></td><td><a href="#/journal/${d.date}" data-journal-day="${d.date}">${esc(d.headline)}</a>${d.headline_source === "commit" ? '<small>待写</small>' : ""}</td><td>${this.chainButtons(d)}</td><td class="journal-number">${d.total_commits}</td><td>${this.reportLinks(d) || "—"}</td></tr>`).join("")}</tbody></table>` : '<p class="journal-empty">没有匹配的日期。请调整时间窗、链条或查找词。</p>';
    },
    flowHtml(ids) {
      const kinds = {"延续": "继续开展", "派生": "扩展研究", "依赖解除": "提供输入", "收口": "汇入报告"};
      return ids.map(cid => {
        const links = this.registry.handoffs.filter(h => h.from === cid || h.to === cid).map(h => {
          const incoming = h.to === cid, other = incoming ? h.from : h.to;
          return `<li>${incoming ? "此前：" : "后续："}${this.chainButton(other)} <small>${esc(kinds[h.type] || h.type)}${h.confidence === "inferred" ? "；按记录顺序关联" : ""}</small>${h.note ? `<p>${esc(h.note)}</p>` : ""}${h.source_refs?.length ? `<p>原始依据：${this.sourceLinks(h.source_refs)}</p>` : ""}</li>`;
        });
        return `<section class="journal-flow-item"><h4>${esc(this.chains.get(cid)?.label)}</h4><ul>${links.join("") || "<li>未登记前后关系</li>"}</ul></section>`;
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
      if (this.selection?.kind === "point") {
        const cid = this.selection.chain, note = this.pointNote(day, cid);
        $("journal-detail").innerHTML = `<article class="journal-day-card journal-point-card" data-selected-date="${day.date}" data-selected-point="${esc(cid)}"><header class="journal-day-header"><div class="journal-day-meta"><button type="button" class="journal-chain-link" data-journal-day="${day.date}" aria-label="查看 ${day.date} 当天全部工作"><time>${day.date}</time></button><span>${esc(day.weekday)}</span><span>${esc(this.weightLabel(day, cid))}</span></div><h2>${this.chainButton(cid)}</h2></header><p>${esc(note.note || "注解待补")}</p>${note.outcome === "dropped" ? '<span class="journal-fate-badge">本条方案未采用</span>' : ""}${note.outcome_note ? `<p>${esc(note.outcome_note)}</p>` : ""}${this.pointEvidenceHtml(day, cid)}${this.reportLinks(day) ? `<p>相关汇报：${this.reportLinks(day)}</p>` : ""}</article>`;
        return;
      }
      const all = this.visibleDays(true), index = all.indexOf(day);
      const lineage = day.chains.map(cid => {
        const dates = this.days.filter(d => d.chains.includes(cid)), i = dates.indexOf(day);
        return `<p>${this.chainButton(cid)} 的相邻记录</p><div class="journal-chain-neighbors">${this.navButton(dates[i - 1], "上一天")}${this.navButton(dates[i + 1], "下一天")}</div>`;
      }).join("");
      const pointNotes = day.chains.map(cid => {
        const note = this.pointNote(day, cid);
        return `<li><div class="journal-task-chain">${this.chainButton(cid)}</div><div class="journal-task-note">${esc(note.note || "注解待补")}${note.outcome === "dropped" ? ' <span class="journal-fate-badge">未采用</span>' : ""}${note.outcome_note ? `<p>${esc(note.outcome_note)}</p>` : ""}${this.pointEvidenceHtml(day, cid)}</div><small class="journal-task-weight">${esc(this.weightLabel(day, cid))}</small></li>`;
      }).join("");
      $("journal-detail").innerHTML = `<nav class="journal-day-nav" aria-label="相邻工作日">${this.navButton(all[index - 1], "前一天")}${this.navButton(all[index + 1], "后一天")}</nav><article class="journal-day-card" data-selected-date="${day.date}">
        <header class="journal-day-header"><div class="journal-day-top"><div class="journal-day-meta"><time>${day.date}</time>${this.dayMetaHtml(day)}<span>${day.total_commits} 次提交</span></div>${day.report ? `<a class="journal-report-link" href="#/daily/${day.report}">阅读每日汇报</a>` : ""}</div><h2 class="${day.headline_source === "commit" ? "journal-draft" : ""}">${esc(day.headline)}${day.headline_source === "commit" ? " <small>待写</small>" : ""}</h2></header>
        <section class="journal-day-overview"><h3>当天工作</h3><ul id="journal-highlights">${day.highlights.map(h => `<li>${esc(h)}</li>`).join("") || '<li>当天没有可展示的提交或计划。</li>'}</ul></section>
        <section class="journal-day-tasks"><h3>各项记录 <small>${day.chains.length} 条任务链</small></h3><div class="journal-task-head" aria-hidden="true"><span>任务链</span><span>当天进展</span><span>提交归属</span></div><ul class="journal-task-list">${pointNotes || '<li>未归类</li>'}</ul></section>
        <details class="journal-relations"><summary>相关工作 <small>整条任务线与相邻记录</small></summary><div class="journal-flow-grid">${this.flowHtml(day.chains) || '<p>未归类</p>'}</div><div class="journal-lineage">${lineage}</div></details>
        <div id="journal-body" class="markdown-body journal-body"></div>
        <section class="journal-raw-records"><h3>原始记录</h3><details class="journal-evidence" data-evidence-date="${day.date}"><summary>提交、计划与汇报 <small>${day.total_commits} 次提交</small></summary><div id="journal-evidence-content"><p>正在读取证据…</p></div></details></section>
      </article>`;
      document.querySelector(".journal-evidence").addEventListener("toggle", e => {
        if (e.target.open) this.loadEvidence(day.date);
      });
      if (day.has_body) this.app.loadFragment(`journal/${day.date}.html`, `journal-body-${day.date}`).then(html => {
        if (this.selected === day.date && this.selection?.kind === "day") { $("journal-body").innerHTML = html; this.prepareDayBody($("journal-body")); this.app.enhanceContent($("journal-body")); }
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
        return `<li class="journal-commit-record"><div class="journal-commit-heading">${this.commitLink(url, item.sha, 7)}<span>${esc(item.subject)}</span></div></li>`;
      }).join("")}</ul></details>`).join("");
      const report = d => `<li><a href="#/daily/${esc(d)}">${esc(d)} ${esc(this.reports.get(d)?.title || "每日汇报")}</a><p>${esc(this.reports.get(d)?.summary)}</p></li>`;
      const reverts = (ev.repos || []).reduce((sum, repo) => sum + (repo.revert_count || 0), 0);
      return this.attributionHtml(ev) + (reverts ? `<p>本日回滚 ${reverts} 次（提交回滚记录）</p>` : "") + repos + `<h4>计划</h4><ul>${(ev.plans || []).map(p => `<li>${esc(p.title)}<small>${esc(p.repo)} / ${esc(p.file)}</small></li>`).join("") || "<li>无计划文件</li>"}</ul><h4>覆盖这天工作的汇报</h4><ul>${(ev.reports_covering || []).filter(d => this.reports.has(d)).map(report).join("") || "<li>无</li>"}</ul><h4>这天发布的汇报</h4><ul>${(ev.reports_published || []).filter(d => this.reports.has(d)).map(report).join("") || "<li>无</li>"}</ul>`;
    },
    attributionHtml(ev) {
      const payload = ev.attribution, day = this.days.find(d => d.date === ev.date);
      if (!payload || !day?.attribution_summary) return '<p>尚未建立逐条提交归属，点保留最小定位尺寸。</p>';
      const items = payload.items, status = day.attribution_summary.statuses;
      const label = {pending: "待核", maintenance: "维护", mirror: "历史导入", excluded: "范围外"};
      const row = (item, cid = "") => {
        const repo = ev.repos.find(r => r.repo === item.repo), url = String(repo?.commit_url || "").replace("{sha}", item.sha);
        const link = this.commitLink(url, item.sha);
        const share = item.shares[cid], paths = Array.isArray(item.paths) ? item.paths : item.paths?.[cid] || [];
        const portion = share ? `，计 ${share.numerator}/${share.denominator} 份` : "";
        const basis = item.basis ? `；${item.basis}` : "";
        return `<li class="journal-commit-record"><div class="journal-commit-heading">${link}<span>${esc(item.subject)}</span></div><small>${esc(item.repo)}${portion}${esc(basis)}</small><p>${esc(item.reason)}</p>${paths.length ? `<small>依据文件：${paths.map(esc).join("；")}</small>` : ""}</li>`;
      };
      const groups = Object.keys(day.chain_weights).filter(cid => day.chain_weights[cid].value > 0).map(cid => {
        const involved = items.filter(item => item.shares[cid]);
        return `<details class="journal-attribution-group" data-attribution-chain="${esc(cid)}"><summary>${esc(this.chains.get(cid)?.short || cid)}：${esc(this.weightLabel(day, cid))}${day.chains.includes(cid) ? "" : "（当日未设图点）"}</summary><ul>${involved.map(item => row(item, cid)).join("")}</ul></details>`;
      }).join("");
      const reserved = Object.entries(label).filter(([key]) => status[key]).map(([key, name]) => `<details class="journal-attribution-group"><summary>${name} ${status[key]} 条（未计入点大小）</summary><ul>${items.filter(item => item.status === key).map(item => row(item)).join("")}</ul></details>`).join("");
      return `<section class="journal-attribution"><h4>任务归属明细</h4><p>完整清单共 ${items.length} 条提交。单任务计 1 份；明确的跨链提交等分，合计仍为 1 份。待核 ${status.pending || 0} 条，保留原始链接供回查。提交量包含实现、修复、尝试、验收和记录，不折算工时或成果价值。</p>${groups}${reserved}</section>`;
    },
    renderChainCard() {
      const chain = this.chains.get(this.chain);
      const days = this.days.filter(d => d.chains.includes(chain.id));
      const reports = this.chainReports(chain, days);
      const track = this.registry.tracks.find(t => t.id === chain.track);
      const windowNote = !this.visible.length ? '<p class="journal-window-empty" role="status">此时间窗内没有这条链的记录。下面展示这条链的全部历史。</p>' : "";
      $("journal-detail").innerHTML = `<article class="journal-day-card journal-chain-card">${windowNote}<p>${esc(track?.label)}　${days.length} 个记录日　首条 ${chain.start} / 末条 ${chain.end}</p><h2>${esc(chain.label)}</h2><p>${esc(chain.purpose)}</p><h3>与其他工作的关系</h3>${this.flowHtml([chain.id])}<h3>原始依据</h3><p>${this.sourceLinks(chain.source_refs) || "尚未登记"}</p><h3>相关汇报与成果</h3><ul>${reports.map(d => `<li><a href="#/daily/${d}">${d} ${esc(this.reports.get(d).title)}</a></li>`).join("") || "<li>尚无关联汇报</li>"}${chain.closes_into?.showcase ? `<li><a href="#/showcase/${esc(chain.closes_into.showcase)}">正式成果：${esc(this.app.getStage(chain.closes_into.showcase).label)}</a></li>` : ""}</ul><h3>这条链上的每一天</h3><div class="journal-chain-days">${days.map(d => `<button type="button" data-journal-day="${d.date}"><time>${d.date}</time><span>${esc(d.headline)}</span>${d.chain_confidence[chain.id] === "inferred" ? `<small>${d.date_notes?.[chain.id] ? '日期待核' : '归属待核'}</small>` : ""}</button>`).join("")}</div></article>`;
      const fate = {landed: chain.status === "active" ? "仍在更新" : "记录说明", folded: "后续去向", parked: "暂搁", dropped: "未采用"};
      document.querySelector(".journal-chain-card h2").insertAdjacentHTML("afterend", `<p>${fate[chain.fate] || fate.landed}${chain.fate_note ? `：${esc(chain.fate_note)}` : ""}</p>`);
      document.querySelectorAll(".journal-chain-days button").forEach((button, i) => {
        const note = this.pointNote(days[i], chain.id);
        button.querySelector("span").innerHTML = esc(note.note || days[i].headline) + (note.outcome === "dropped" ? ' <span class="journal-fate-badge">未采用</span>' : "");
      });
    },
  };
  window.JournalView = JournalView;
})();
