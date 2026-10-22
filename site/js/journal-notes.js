(function () {
  "use strict";
  const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));
  const esc = value => String(value ?? "").replace(/[&<>"']/g, c => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}[c]));
  const overlap = (a, b, gap = 0) => a.x < b.x + b.w + gap && a.x + a.w + gap > b.x && a.y < b.y + b.h + gap && a.y + a.h + gap > b.y;

  function attachment(rect, x, y, sideways = false) {
    if (sideways) return {x: x < rect.x ? rect.x : rect.x + rect.w, y: clamp(y, rect.y + 16, rect.y + rect.h - 16), edge: x < rect.x ? "left" : "right"};
    const portX = clamp(x, rect.x + 16, rect.x + rect.w - 16);
    if (y >= rect.y + rect.h) return {x: portX, y: rect.y + rect.h, edge: "bottom"};
    if (y <= rect.y) return {x: portX, y: rect.y, edge: "top"};
    return {x: x < rect.x ? rect.x : rect.x + rect.w, y: clamp(y, rect.y + 16, rect.y + rect.h - 16), edge: x < rect.x ? "left" : "right"};
  }

  function placeCards(cards, {bounds, anchorY, points = [], manual = new Map()}) {
    const placed = [], lifts = [38, 106, 152, 64, 166, 94];
    for (const [index, card] of cards.entries()) {
      const rect = {...card}, saved = manual.get(card.id);
      if (saved) {
        rect.x = clamp(saved.x, bounds.left, bounds.right - rect.w);
        rect.y = clamp(saved.y, bounds.top, Math.max(bounds.top, bounds.bottom - rect.h));
      } else {
        let best = null, bestCost = Infinity;
        const preferred = lifts[index % lifts.length];
        for (const direction of [-1, 1]) for (let lift = 28; lift <= 460; lift += 24) for (let side = -224; side <= 224; side += 28) {
          const x = clamp(card.anchorX - rect.w * .45 + side, bounds.left, bounds.right - rect.w);
          const y = direction < 0 ? anchorY - rect.h - lift : anchorY + lift;
          const candidate = {...rect, x, y};
          if (y < bounds.top || y + rect.h > bounds.bottom || placed.some(other => overlap(candidate, other, 14))) continue;
          const port = attachment(candidate, card.anchorX, anchorY);
          const distance = Math.hypot(port.x - card.anchorX, port.y - anchorY);
          const covered = points.reduce((n, p) => n + Number(p.x > x && p.x < x + rect.w && p.y > y && p.y < y + rect.h), 0);
          const cost = distance * 1.1 + Math.abs(port.x - card.anchorX) * .6 + covered * 7 + Math.abs(lift - preferred) * 1.6;
          if (cost < bestCost) { best = candidate; bestCost = cost; }
        }
        if (!best) {
          // 极短时间窗仍保留原日期坐标，只在图底增加容纳说明的留白。
          best = {...rect, x: clamp(card.anchorX - rect.w / 2, bounds.left, bounds.right - rect.w), y: Math.max(bounds.top, anchorY + 28)};
          while (placed.some(other => overlap(best, other, 14))) best.y += 24;
        }
        rect.x = best.x; rect.y = best.y;
      }
      placed.push(rect);
    }
    return {cards: placed, height: Math.max(bounds.bottom, ...placed.map(rect => rect.y + rect.h + 10))};
  }

  function segmentHits(a, b, rect) {
    const margin = rect.margin ?? 5, l = rect.x - margin, r = rect.x + rect.w + margin, t = rect.y - margin, bottom = rect.y + rect.h + margin;
    if (Math.abs(a.x - b.x) < .1) return a.x > l + .1 && a.x < r - .1 && Math.max(a.y, b.y) > t + .1 && Math.min(a.y, b.y) < bottom - .1;
    if (Math.abs(a.y - b.y) < .1) return a.y > t + .1 && a.y < bottom - .1 && Math.max(a.x, b.x) > l + .1 && Math.min(a.x, b.x) < r - .1;
    return false;
  }

  function placeChainCards(cards, {bounds, points = [], manual = new Map()}) {
    const placed = [];
    for (const [index, card] of cards.entries()) {
      const saved = manual.get(card.id);
      if (saved) {
        placed.push({...card, x: clamp(saved.x, bounds.left, bounds.right - card.w), y: clamp(saved.y, bounds.top, Math.max(bounds.top, bounds.bottom - card.h))});
        continue;
      }
      let best, bestCost = Infinity;
      const preferredSide = index % 2 ? -1 : 1, rhythm = [0, 24, 8, 40][index % 4];
      for (const side of [preferredSide, -preferredSide]) for (let gap = 44; gap <= bounds.right - bounds.left; gap += 28) {
        const x = side > 0 ? card.anchorX + gap : card.anchorX - gap - card.w;
        if (x < bounds.left || x + card.w > bounds.right) continue;
        for (let shift = 0; shift <= 600; shift += 20) for (const direction of shift ? [-1, 1] : [1]) {
          const y = clamp(card.anchorY - card.h * .42 + shift * direction, bounds.top, Math.max(bounds.top, bounds.bottom - card.h));
          const candidate = {...card, x, y};
          if (placed.some(other => overlap(candidate, other, 16))) continue;
          const covered = points.reduce((n, p) => n + Number(p.x > x && p.x < x + card.w && p.y > y && p.y < y + card.h), 0);
          const cost = Math.abs(y + card.h * .42 - card.anchorY) * 3.8 + gap * .35 + Math.abs(gap - 44 - rhythm) * .8 + (side === preferredSide ? 0 : 20) + covered * 5;
          if (cost < bestCost) { best = candidate; bestCost = cost; }
        }
      }
      if (!best) {
        const right = bounds.right - card.anchorX >= card.anchorX - bounds.left;
        best = {...card, x: clamp(right ? card.anchorX + 44 : card.anchorX - card.w - 44, bounds.left, bounds.right - card.w), y: Math.max(bounds.top, card.anchorY - card.h * .42)};
        while (placed.some(other => overlap(best, other, 16))) best.y += 20;
      }
      placed.push(best);
    }
    return {cards: placed, height: Math.max(bounds.bottom, ...placed.map(r => r.y + r.h + 10))};
  }

  function routeLeader(start, end, obstacles, {left = 0, right, top = 0, bottom, used = []}) {
    const xs = [...new Set([start.x, end.x, left, right, ...obstacles.flatMap(r => [r.x - (r.margin ?? 5) - 1, r.x + r.w + (r.margin ?? 5) + 1])])].filter(x => x >= left && x <= right).sort((a, b) => a - b);
    const ys = [...new Set([start.y, end.y, top, bottom, ...obstacles.flatMap(r => [r.y - (r.margin ?? 5) - 1, r.y + r.h + (r.margin ?? 5) + 1])])].filter(y => y >= top && y <= bottom).sort((a, b) => a - b);
    const nodes = [], ids = new Map();
    ys.forEach((y, yi) => xs.forEach((x, xi) => {
      if (obstacles.some(r => x > r.x - (r.margin ?? 5) && x < r.x + r.w + (r.margin ?? 5) && y > r.y - (r.margin ?? 5) && y < r.y + r.h + (r.margin ?? 5))) return;
      ids.set(`${xi}:${yi}`, nodes.length); nodes.push({x, y, xi, yi, edges: []});
    }));
    nodes.forEach(node => {
      for (const [dx, dy] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) {
        const id = ids.get(`${node.xi + dx}:${node.yi + dy}`);
        if (id !== undefined && !obstacles.some(r => segmentHits(node, nodes[id], r))) node.edges.push(id);
      }
    });
    const source = nodes.findIndex(n => n.x === start.x && n.y === start.y), goal = nodes.findIndex(n => n.x === end.x && n.y === end.y);
    if (source < 0 || goal < 0) return null;
    // 小顶堆避免拖动时反复排序整张可见性图。
    const heap = [];
    const push = item => {
      heap.push(item); let i = heap.length - 1;
      while (i) { const p = (i - 1) >> 1; if (heap[p].cost <= item.cost) break; heap[i] = heap[p]; i = p; } heap[i] = item;
    };
    const pop = () => {
      const first = heap[0], last = heap.pop(); if (!heap.length) return first;
      let i = 0;
      while (i * 2 + 1 < heap.length) {
        let child = i * 2 + 1; if (child + 1 < heap.length && heap[child + 1].cost < heap[child].cost) child++;
        if (heap[child].cost >= last.cost) break; heap[i] = heap[child]; i = child;
      }
      heap[i] = last; return first;
    };
    const distance = new Map([[`${source}:0`, 0]]), previous = new Map();
    push({id: source, dir: 0, cost: 0, key: `${source}:0`}); let result;
    while (heap.length) {
      const current = pop(); if (current.cost > distance.get(current.key)) continue;
      if (current.id === goal) { result = current.key; break; }
      const a = nodes[current.id];
      for (const id of a.edges) {
        const b = nodes[id], dir = Math.abs(a.x - b.x) < .1 ? 1 : 2, key = `${id}:${dir}`;
        let crossings = 0;
        for (const path of used) for (let i = 1; i < path.length; i++) {
          const c = path[i - 1], d = path[i];
          if (dir === 1 && Math.abs(c.y - d.y) < .1 && Math.min(c.x, d.x) < a.x && Math.max(c.x, d.x) > a.x && Math.min(a.y, b.y) < c.y && Math.max(a.y, b.y) > c.y) crossings++;
          if (dir === 2 && Math.abs(c.x - d.x) < .1 && Math.min(c.y, d.y) < a.y && Math.max(c.y, d.y) > a.y && Math.min(a.x, b.x) < c.x && Math.max(a.x, b.x) > c.x) crossings++;
        }
        const cost = current.cost + Math.abs(a.x - b.x) + Math.abs(a.y - b.y) + (current.dir && current.dir !== dir ? 18 : 0) + crossings * 24;
        if (cost >= (distance.get(key) ?? Infinity)) continue;
        distance.set(key, cost); previous.set(key, current.key); push({id, dir, cost, key});
      }
    }
    if (!result) return null;
    const path = [];
    while (result) { const node = nodes[Number(result.split(":")[0])]; path.push({x: node.x, y: node.y}); result = previous.get(result); }
    path.reverse();
    return path.filter((p, i) => !i || i === path.length - 1 || !(Math.abs(path[i - 1].x - p.x) < .1 && Math.abs(p.x - path[i + 1].x) < .1 || Math.abs(path[i - 1].y - p.y) < .1 && Math.abs(p.y - path[i + 1].y) < .1));
  }

  function roundedPath(points) {
    if (!points?.length) return "";
    let d = `M${points[0].x},${points[0].y}`;
    for (let i = 1; i < points.length - 1; i++) {
      const a = points[i - 1], b = points[i], c = points[i + 1], l1 = Math.hypot(b.x - a.x, b.y - a.y), l2 = Math.hypot(c.x - b.x, c.y - b.y);
      if (!l1 || !l2) continue;
      const radius = Math.min(6, l1 / 2, l2 / 2);
      d += ` L${b.x + (a.x - b.x) * radius / l1},${b.y + (a.y - b.y) * radius / l1} Q${b.x},${b.y} ${b.x + (c.x - b.x) * radius / l2},${b.y + (c.y - b.y) * radius / l2}`;
    }
    return d + ` L${points.at(-1).x},${points.at(-1).y}`;
  }

  class FloatingNotes {
    constructor(onFocus) {
      this.onFocus = onFocus; this.manual = new Map(); this.previous = new Map(); this.open = true; this.frame = 0;
    }
    anchor(id) {
      const c = this.config;
      return c.anchor ? c.anchor(id) : {x: c.atlas.positions.get(id), y: c.atlas.y(c.day.date), radius: c.atlas.radius(c.day, id)};
    }
    capture() {
      if (!this.layer?.isConnected) return;
      this.previous = new Map([...this.layer.children].filter(n => !n.hidden).map(n => [n.dataset.noteId, {x: n.offsetLeft, y: n.offsetTop}]));
    }
    clear() {
      cancelAnimationFrame(this.frame); this.frame = 0; this.previous.clear();
      if (this.layer?.isConnected) this.layer.replaceChildren();
      if (this.leaders?.isConnected) this.leaders.replaceChildren();
      this.layer?.classList.remove("journal-floating-notes"); this.date = null; this.open = true; this.manual.clear();
      document.querySelector(".journal-note-tools")?.remove();
      this.config = null;
    }
    render(config) {
      const oldFocus = document.activeElement?.closest(".journal-floating-note")?.dataset.noteId;
      this.capture(); cancelAnimationFrame(this.frame); this.frame = 0;
      const signature = `${config.atlas.width}:${config.atlas.height}:${config.atlas.y(config.day.date)}`;
      const group = config.group || config.day.date;
      if (this.date !== group) { this.open = true; this.previous.clear(); this.manual.clear(); }
      else if (signature !== this.signature) { this.manual.clear(); this.previous.clear(); }
      this.date = group; this.signature = signature; this.config = config; this.layer = config.annotations;
      this.narrow = config.scroller.clientWidth < 600;
      if (this.narrow || config.mode === "chain") {
        const x = this.anchor(config.focused).x, {scroller, atlas} = config;
        if (x < scroller.scrollLeft + 24 || x > scroller.scrollLeft + scroller.clientWidth - 24) scroller.scrollLeft = clamp(x - scroller.clientWidth / 2, 0, atlas.width - scroller.clientWidth);
        document.querySelector(".journal-head-scroller").scrollLeft = scroller.scrollLeft;
      }
      this.layer.classList.add("journal-floating-notes");
      this.layer.innerHTML = config.ids.map((cid, index) => {
        const note = config.note(cid), amount = config.weight(cid), focused = cid === config.focused;
        const day = config.dayFor ? config.dayFor(cid) : config.day, chain = config.chain || cid;
        const shared = day.chain_weights?.[chain]?.shared || 0, label = config.mode === "chain" ? String(index + 1).padStart(2, "0") : String.fromCharCode(65 + index);
        const reports = typeof config.reports === "function" ? config.reports(cid) : config.reports;
        return `<article class="journal-annotation journal-floating-note${config.mode === "chain" ? " journal-chain-note" : ""}${focused ? " is-focused" : ""}" data-note-id="${esc(cid)}" data-annotation-chain="${esc(chain)}" data-date="${day.date}" aria-label="${esc(config.name(cid))}的工作说明" ${this.narrow && !focused ? "hidden" : ""}>
          <button type="button" class="journal-floating-head" data-note="${esc(cid)}" aria-pressed="${focused}" aria-label="${esc(config.name(cid))}，点击聚焦，拖动调整位置，方向键移动"><span class="journal-note-letter">${label}</span><strong>${esc(config.name(cid))}</strong><span class="journal-note-grip" aria-hidden="true">⠿</span></button>
          <p class="journal-note-copy">${esc(note.note || "注解待补")}</p>
          ${config.evidence ? config.evidence(cid, !focused) : ""}
          <div class="journal-note-meta"><span>归属提交量 <b>${amount === null ? "待核" : esc(amount)}</b></span><time>${day.date.slice(5)}</time></div>
          ${note.outcome === "dropped" ? '<span class="journal-fate-badge">本条方案未采用</span>' : ""}
          <div class="journal-note-extra">${reports ? `相关汇报：${reports}` : "未关联汇报"}${shared ? `<br>含 ${shared} 条跨链提交的份额` : ""}${amount === 0 ? "<br>当日无已归属提交；当天有工作记录" : ""}${note.outcome_note ? `<br>${esc(note.outcome_note)}` : ""}</div>
        </article>`;
      }).join("");
      this.leaders = config.canvas.querySelector(".journal-note-leaders");
      if (!this.leaders) { this.leaders = document.createElementNS("http://www.w3.org/2000/svg", "svg"); this.leaders.classList.add("journal-note-leaders"); this.leaders.setAttribute("aria-hidden", "true"); config.canvas.insertBefore(this.leaders, this.layer); }
      this.tools(); this.layout(true);
      for (const card of this.layer.children) this.wire(card);
      if (oldFocus) this.layer.querySelector(`[data-note="${CSS.escape(oldFocus)}"]`)?.focus({preventScroll: true});
    }
    tools() {
      const {context, ids, focused, mode} = this.config;
      context.querySelector(".journal-note-tools")?.remove();
      const controls = document.createElement("div"); controls.className = "journal-note-tools";
      controls.innerHTML = `<button type="button" data-note-action="toggle" aria-pressed="${this.open}">${this.open ? "收起说明" : "展开说明"}</button><button type="button" data-note-action="arrange" ${this.open ? "" : "disabled"}>重新排布</button>${ids.length > 1 && (this.narrow || mode === "chain") ? `<button type="button" data-note-action="prev" aria-label="${mode === "chain" ? "上一个事件" : "上一项工作"}">上一项</button><span aria-live="polite">${ids.indexOf(focused) + 1} / ${ids.length}</span><button type="button" data-note-action="next" aria-label="${mode === "chain" ? "下一个事件" : "下一项工作"}">下一项</button>` : '<span class="journal-note-hint">点击聚焦 · 拖动浮窗</span>'}`;
      controls.onclick = event => {
        document.getElementById("view-journal").classList.toggle("is-keyboard", event.detail === 0);
        const action = event.target.closest("[data-note-action]")?.dataset.noteAction;
        if (action === "toggle") { this.open = !this.open; this.previous.clear(); this.tools(); this.layout(true); }
        if (action === "arrange") { this.manual.clear(); this.previous.clear(); this.layout(true); }
        if (action === "prev" || action === "next") this.onFocus(ids[(ids.indexOf(focused) + (action === "prev" ? -1 : 1) + ids.length) % ids.length]);
        if (action) this.config.context.querySelector(`[data-note-action="${action}"]`)?.focus({preventScroll: true});
        if (this.open && ["toggle", "arrange"].includes(action)) this.config.onReveal();
      };
      context.append(controls);
    }
    layout(animate = false) {
      if (!this.config || !this.layer.isConnected) return;
      this.layer.hidden = false;
      const c = this.config, a = c.atlas, y = a.y(c.day.date), viewport = c.scroller.clientWidth;
      const left = this.narrow ? c.scroller.scrollLeft + 10 : Math.max(a.dateWidth + 10, c.scroller.scrollLeft + 10), right = Math.min(a.width - 10, c.scroller.scrollLeft + viewport - 10);
      const cards = [...this.layer.children].filter(n => !n.hidden).map((node, index) => {
        const cid = node.dataset.noteId, width = this.narrow ? Math.min(270, right - left) : Math.min(right - left, (c.mode === "chain" ? 204 : 178) + (c.note(cid).note?.length || 0) % 4 * 9 + (cid === c.focused ? 20 : 0));
        node.style.width = width + "px";
        const anchor = this.anchor(cid);
        return {id: cid, node, w: node.offsetWidth, h: node.offsetHeight, anchorX: anchor.x, anchorY: anchor.y, radius: anchor.radius, index};
      });
      const result = (c.mode === "chain" && !this.narrow ? placeChainCards : placeCards)(cards, {bounds: {left, right, top: 10, bottom: a.height}, anchorY: c.mode === "chain" ? this.anchor(c.focused).y : y, points: c.points, manual: this.manual});
      this.layer.hidden = !this.open; this.leaders.hidden = !this.open;
      this.rects = result.cards;
      const expanded = this.open ? result.height : a.height;
      c.svg.setAttribute("height", expanded); c.svg.setAttribute("viewBox", `0 0 ${a.width} ${expanded}`);
      this.leaders.setAttribute("width", a.width); this.leaders.setAttribute("height", expanded); this.leaders.setAttribute("viewBox", `0 0 ${a.width} ${expanded}`);
      const canAnimate = animate && this.open && !document.querySelector("#view-journal.is-keyboard") && !matchMedia("(prefers-reduced-motion: reduce)").matches;
      for (const rect of this.rects) {
        const {node} = rect, previous = this.previous.get(rect.id);
        node.getAnimations().forEach(animation => animation.cancel()); node.style.left = rect.x + "px"; node.style.top = rect.y + "px";
        node.style.transformOrigin = rect.anchorY < rect.y ? "50% 0%" : "50% 100%";
        if (canAnimate) node.animate([{transform: `translate(${previous ? previous.x - rect.x : rect.anchorX - rect.x - rect.w / 2}px,${previous ? previous.y - rect.y : rect.anchorY - rect.y - rect.h * .7}px) scale(${previous ? 1 : .94})`, opacity: previous ? 1 : 0}, {transform: "translate(0,0) scale(1)", opacity: 1}], {duration: 280, delay: previous ? 0 : Math.min(rect.index * 24, 120), easing: "cubic-bezier(.23,1,.32,1)"});
      }
      this.drawLeaders();
      this.layer.dataset.motion = canAnimate ? "moving" : "idle";
      if (canAnimate) this.followMotion();
    }
    followMotion() {
      cancelAnimationFrame(this.frame);
      const frame = () => {
        this.frame = 0; if (!this.config || !this.layer.isConnected || !this.open) return;
        const moving = [...this.layer.children].some(node => node.getAnimations().some(a => a.playState === "running"));
        this.drawLeaders(moving);
        this.layer.dataset.motion = moving ? "moving" : "idle";
        if (moving) this.frame = requestAnimationFrame(frame);
      };
      this.frame = requestAnimationFrame(frame);
    }
    drawLeaders(moving = false) {
      if (!this.open || !this.rects || !this.config) return;
      const c = this.config, a = c.atlas, y = a.y(c.day.date), box = c.canvas.getBoundingClientRect();
      const rects = moving ? this.rects.map(r => { const b = r.node.getBoundingClientRect(); return {...r, x: b.left - box.left, y: b.top - box.top, w: b.width, h: b.height}; }) : this.rects;
      const used = [], paths = [];
      for (const r of [...rects].sort((x, z) => Number(z.id === c.focused) - Number(x.id === c.focused))) {
        const anchorX = r.anchorX, anchorY = r.anchorY, port = attachment(r, anchorX, anchorY, c.mode === "chain" && !this.narrow), direction = port.y < anchorY ? -1 : 1;
        if (c.mode === "chain" && this.narrow && ["top", "bottom"].includes(port.edge)) {
          const clearance = Math.max(...c.ids.map(id => this.anchor(id).radius)) + 16;
          const options = [clamp(anchorX + clearance, r.x + 16, r.x + r.w - 16), clamp(anchorX - clearance, r.x + 16, r.x + r.w - 16)];
          port.x = options.sort((x, z) => Math.abs(z - anchorX) - Math.abs(x - anchorX))[0];
        }
        const start = c.mode === "chain" ? {x: anchorX + (port.x < anchorX ? -1 : 1) * (r.radius + 3), y: anchorY} : {x: anchorX, y: anchorY + direction * (r.radius + 3)};
        const end = {x: port.x + (port.edge === "left" ? -7 : port.edge === "right" ? 7 : 0), y: port.y + (port.edge === "top" ? -7 : port.edge === "bottom" ? 7 : 0)};
        const others = c.ids.filter(cid => cid !== r.id).map(cid => {
          const p = this.anchor(cid), radius = p.radius + 3;
          // 紧凑密度下圆周可能重叠，仍为各事件中心保留独立通道。
          const gap = c.mode === "chain" ? Math.min(...c.ids.filter(id => id !== cid).map(id => Math.abs(this.anchor(id).y - p.y))) : Infinity;
          const halfHeight = Math.min(radius, Math.max(1, gap / 2 - 1));
          return {x: p.x - radius, y: p.y - halfHeight, w: radius * 2, h: halfHeight * 2, margin: 0};
        });
        // 动画期间窗口会经过彼此；最终位置再计算完整避障路径。
        const area = c.mode === "chain" ? {left: Math.max(1, Math.min(start.x, end.x) - 32), right: Math.min(a.width - 1, Math.max(start.x, end.x) + 32), top: Math.max(1, Math.min(start.y, end.y) - 32), bottom: Math.min(Number(c.svg.getAttribute("height")) - 1, Math.max(start.y, end.y) + 32), used} : {left: 1, right: a.width - 1, top: 1, bottom: Number(c.svg.getAttribute("height")) - 1, used};
        const obstacles = [...rects, ...others].filter(o => c.mode !== "chain" || overlap(o, {x: area.left, y: area.top, w: area.right - area.left, h: area.bottom - area.top}, 8));
        let route = moving ? [start, end] : routeLeader(start, end, obstacles, area);
        if (!route && c.mode === "chain") route = routeLeader(start, end, [...rects, ...others], {left: 1, right: a.width - 1, top: 1, bottom: Number(c.svg.getAttribute("height")) - 1, used});
        if (!route) continue;
        route.push(port); used.push(route);
        const path = roundedPath(route), active = r.id === c.focused;
        paths.push(`<g class="journal-note-route${active ? " is-focused" : ""}" data-note-route="${esc(r.id)}" data-route-points="${esc(JSON.stringify(route))}"><path class="journal-note-route-halo" d="${path}"/><path class="journal-note-route-line" d="${path}"/><circle cx="${port.x}" cy="${port.y}" r="${active ? 2.7 : 2}"/></g>`);
      }
      // 当前引线最后绘制，避免被其他线盖住。
      this.leaders.innerHTML = paths.reverse().join("");
    }
    wire(card) {
      const head = card.querySelector(".journal-floating-head"), cid = card.dataset.noteId;
      card.querySelectorAll(".journal-point-sources").forEach(details => details.addEventListener("toggle", () => {
        if (!card.isConnected || !this.config) return;
        this.capture(); this.layout();
        if (!details.open) return;
        const top = document.querySelector(".journal-atlas-header").getBoundingClientRect().bottom + 12;
        const box = card.getBoundingClientRect();
        if (box.top < top) window.scrollBy({top: box.top - top, behavior: "instant"});
        else if (box.bottom > innerHeight - 16) window.scrollBy({top: Math.min(box.bottom - innerHeight + 16, box.top - top), behavior: "instant"});
      }));
      let drag = null, moved = false;
      head.onclick = event => { if (moved) { moved = false; return; } document.getElementById("view-journal").classList.toggle("is-keyboard", event.detail === 0); if (this.config.focused !== cid) this.onFocus(cid); };
      head.onpointerdown = event => {
        if (event.button !== 0) return;
        head.setPointerCapture(event.pointerId); card.getAnimations().forEach(a => a.cancel());
        drag = {x: event.clientX, y: event.clientY, left: card.offsetLeft, top: card.offsetTop}; moved = false;
      };
      head.onpointermove = event => {
        if (!drag) return;
        const dx = event.clientX - drag.x, dy = event.clientY - drag.y;
        if (!moved && Math.hypot(dx, dy) < 4) return;
        moved = true; card.classList.add("is-dragging");
        const c = this.config, rect = this.rects.find(r => r.id === cid);
        rect.x = clamp(drag.left + dx, c.scroller.scrollLeft + 8, Math.min(c.atlas.width - 8, c.scroller.scrollLeft + c.scroller.clientWidth - 8) - rect.w);
        rect.y = clamp(drag.top + dy, 8, Number(c.svg.getAttribute("height")) - rect.h - 8);
        card.style.left = rect.x + "px"; card.style.top = rect.y + "px";
        if (!this.frame) this.frame = requestAnimationFrame(() => { this.frame = 0; this.drawLeaders(); });
      };
      const finish = () => {
        if (!drag) return; drag = null; card.classList.remove("is-dragging");
        if (moved) { this.manual.set(cid, {x: card.offsetLeft, y: card.offsetTop}); this.capture(); this.drawLeaders(); }
      };
      head.onpointerup = finish; head.onpointercancel = finish;
      head.ondblclick = () => { this.manual.delete(cid); this.capture(); this.layout(true); };
      head.onkeydown = event => {
        const delta = {ArrowLeft: [-12, 0], ArrowRight: [12, 0], ArrowUp: [0, -12], ArrowDown: [0, 12]}[event.key];
        if (!delta) return; event.preventDefault(); event.stopPropagation();
        this.manual.set(cid, {x: card.offsetLeft + delta[0], y: card.offsetTop + delta[1]}); this.layout(); this.capture();
      };
    }
    onScroll() { if (!this.config) return; this.capture(); this.layout(); }
  }
  if (typeof module !== "undefined" && module.exports) module.exports = {attachment, placeCards, placeChainCards, segmentHits, routeLeader, roundedPath};
  if (typeof window !== "undefined") window.JournalFloatingNotes = FloatingNotes;
})();
