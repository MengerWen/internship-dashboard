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
      this.selected = this.days.at(-1)?.date;
      this.window = "all";
      this.chain = "";
      this.query = "";
      this.evidence = new Map();
      this.mode = matchMedia("(min-width: 860px)").matches ? "atlas" : "list";
      $("journal-title").textContent = $("tab-journal").textContent;
      $("journal-chain").innerHTML = '<option value="">全部链条</option>' + this.registry.tracks.map(t =>
        `<optgroup label="${esc(t.label)}">${this.registry.chains.filter(c => c.track === t.id).map(c => `<option value="${esc(c.id)}">${esc(c.label)}</option>`).join("")}</optgroup>`).join("");
      $("journal-window").addEventListener("change", e => { this.window = e.target.value; this.render(); this.writeHash(); });
      $("journal-chain").addEventListener("change", e => this.focusChain(e.target.value));
      $("journal-clear").addEventListener("click", () => this.focusChain(""));
      $("journal-find").addEventListener("input", e => { this.query = e.target.value; this.render(); });
      document.querySelectorAll("[data-journal-view]").forEach(button => button.addEventListener("click", () => {
        this.mode = button.dataset.journalView; this.render(); this.writeHash();
      }));
      $("view-journal").addEventListener("click", e => {
        $("view-journal").classList.toggle("is-keyboard", e.detail === 0);
        const retry = e.target.closest("[data-journal-evidence]");
        if (retry) this.loadEvidence(retry.dataset.journalEvidence, true);
        const day = e.target.closest("[data-journal-day]");
        if (day) { e.preventDefault(); this.select(day.dataset.journalDay, true); }
        const chain = e.target.closest("[data-journal-chain]");
        if (chain) this.focusChain(chain.dataset.journalChain);
        const row = e.target.closest("tr[data-date]");
        if (row && !e.target.closest("a,button")) this.select(row.dataset.date, true);
      });
      $("journal-figure").addEventListener("mousemove", e => this.readout(e));
      $("journal-figure").addEventListener("mouseleave", () => this.hideReadout());
      $("journal-figure").addEventListener("keydown", e => {
        $("view-journal").classList.add("is-keyboard");
        if (e.key === "Escape") { this.focusChain(""); return; }
        if (!["ArrowLeft", "ArrowRight"].includes(e.key)) return;
        e.preventDefault();
        const dates = this.visibleDays(true), index = dates.findIndex(d => d.date === this.selected);
        const next = dates[index + (e.key === "ArrowLeft" ? -1 : 1)];
        if (next) this.select(next.date);
      });
    },
    show(key) {
      const params = new URLSearchParams(location.hash.split("?")[1] || "");
      this.mode = ["atlas", "list"].includes(params.get("view")) ? params.get("view") : (matchMedia("(min-width: 860px)").matches ? "atlas" : "list");
      this.chain = this.chains.has(params.get("chain")) ? params.get("chain") : "";
      this.window = ["1m", "3m"].includes(params.get("window")) ? params.get("window") : "all";
      if (this.days.some(d => d.date === key)) {
        this.selected = key;
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
      params.set("view", this.mode);
      if (this.window !== "all") params.set("window", this.window);
      history.replaceState(null, "", `#/journal${this.selected ? "/" + this.selected : ""}${params.size ? "?" + params : ""}`);
    },
    select(key, scroll = false) {
      this.selected = key;
      this.chain = "";
      this.query = ""; $("journal-find").value = "";
      if (!this.visibleDays(true).some(d => d.date === key)) this.window = "all";
      if (scroll) this.mode = "atlas";
      this.render(); this.writeHash();
      if (scroll) {
        $("journal-detail").scrollIntoView({block: "start"});
        const scroller = document.querySelector(".journal-scroller");
        const pixel = this.atlas.x(key) / 1240 * scroller.scrollWidth;
        scroller.scrollLeft = Math.max(0, pixel - scroller.clientWidth / 2);
      }
    },
    focusChain(cid) {
      this.chain = cid;
      this.render(); this.writeHash();
    },
    reportLinks(day) {
      return (day.reports_covering || (day.report ? [day.report] : [])).map(d => `<a href="#/daily/${esc(d)}">${esc(d)}</a>`).join(" ");
    },
    chainButtons(day) {
      return day.chains.map(cid => `<button type="button" class="journal-chain-link" data-journal-chain="${esc(cid)}">${esc(this.chains.get(cid)?.short || cid)}${day.chain_confidence[cid] === "inferred" ? ' <small>待核</small>' : ""}</button>`).join(" ") || "未归类";
    },
    render() {
      const wasFocused = document.activeElement?.classList.contains("journal-atlas");
      const focusedNav = document.activeElement?.dataset.journalNav;
      this.visible = this.visibleDays();
      if (!this.visible.some(d => d.date === this.selected)) this.selected = this.visible[0]?.date;
      $("journal-window").value = this.window;
      $("journal-chain").value = this.chain;
      $("journal-clear").hidden = !this.chain;
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
      if (focusedNav) {
        const buttons = [...document.querySelectorAll("[data-journal-nav]")];
        const next = buttons.find(b => b.dataset.journalNav === focusedNav && !b.disabled) || buttons.find(b => !b.disabled);
        next?.focus({preventScroll: true});
      }
    },
    renderAtlas() {
      const days = this.visibleDays(true);
      const scroller = document.querySelector(".journal-scroller");
      if (!days.length) { scroller.innerHTML = '<p class="journal-empty">暂无日志。</p>'; return; }
      const num = d => Date.parse(d + "T00:00:00Z") / 86400000;
      const first = num(days[0].date), last = num(days.at(-1).date);
      const x = d => 148 + (num(d) - first) / Math.max(1, last - first) * 1060;
      const positions = new Map();
      let y = 42;
      const rows = this.registry.tracks.map(track => {
        const chains = this.registry.chains.filter(c => c.track === track.id);
        const height = 36 + 9 * chains.length;
        chains.forEach((c, i) => positions.set(c.id, y + height / 2 + (chains.length <= 1 ? 0 : (i / (chains.length - 1) - .5) * (height - 22))));
        const row = {track, y, height, chains}; y += height;
        return row;
      });
      const bottom = y, height = y + 76;
      const active = new Map(this.registry.chains.map(c => [c.id, days.filter(d => d.chains.includes(c.id))]));
      const parts = [`<svg class="journal-atlas" viewBox="0 0 1240 ${height}" tabindex="0" role="group" aria-labelledby="journal-atlas-title journal-atlas-desc" data-days="${days.length}"><title id="journal-atlas-title">工作日期与任务链条</title><desc id="journal-atlas-desc">横轴为真实日期，纵轴为六条轨道。实心点有汇报，空心点无汇报，点的大小表示提交数。左右方向键换日，Esc 取消聚焦。全部信息也可在清单和日卡中阅读。</desc>`];
      for (let n = first; n <= last; n++) {
        const date = new Date(n * 86400000).toISOString().slice(0, 10);
        const weekday = new Date(n * 86400000).getUTCDay();
        if ([0, 6].includes(weekday)) parts.push(`<rect class="journal-weekend" x="${x(date) - 3}" y="32" width="${Math.max(6, 1060 / Math.max(1, last - first))}" height="${bottom - 32}"/>`);
        if (date.endsWith("-01")) parts.push(`<path class="journal-month-rule" d="M${x(date)},30 V${bottom + 24}"/><text class="journal-axis-label" x="${x(date) + 5}" y="19">${Number(date.slice(5, 7))}月</text>`);
      }
      if (this.selected) parts.push(`<rect class="journal-selection-band" x="${x(this.selected) - 4}" y="30" width="8" height="${bottom - 6}"/><path class="journal-selection-line" d="M${x(this.selected)},30 V${bottom + 24}"/>`);
      rows.forEach(({track, y, height: bh, chains}) => {
        parts.push(`<path class="journal-rule" d="M0,${y + bh} H1224"/><text class="journal-track-label" x="0" y="${y + bh / 2 - 3}">${esc(track.label)}</text><text class="journal-axis-label" x="0" y="${y + bh / 2 + 15}">${chains.length} 条链</text>`);
      });
      this.registry.handoffs.forEach(edge => {
        const from = active.get(edge.from), to = active.get(edge.to);
        if (!from?.length || !to?.length) return;
        // 交接发生在后继首次出现时；前驱可并行继续，不能一律从其最终日期连回去。
        const target = to.find(d => !edge.date || d.date >= edge.date)?.date || to.at(-1).date;
        const source = from.filter(d => d.date <= target).at(-1)?.date || from[0].date;
        const x1 = x(source), x2 = x(target), y1 = positions.get(edge.from), y2 = positions.get(edge.to);
        const dash = edge.type === "派生" ? "4 3" : edge.type === "依赖解除" ? "1 3" : edge.type === "收口" ? "7 2 1 2" : (edge.confidence === "inferred" ? "2 5" : "");
        parts.push(`<g class="journal-unit journal-handoff" data-chains="${esc(edge.from)} ${esc(edge.to)}" data-type="${esc(edge.type)}" data-date="${target}"><path class="journal-handoff-path${edge.confidence === "inferred" ? " is-inferred" : ""}" stroke-dasharray="${dash}" d="M${x1},${y1} C${x1 + 30},${y1} ${x2 - 30},${y2} ${x2},${y2}"/><title>${esc(this.chains.get(edge.from).short)} → ${esc(this.chains.get(edge.to).short)}：${esc(edge.type)}${edge.confidence === "inferred" ? "（推断）" : ""}</title></g>`);
      });
      rows.forEach(({chains}) => {
        let previousLabel = -Infinity;
        chains.forEach(chain => {
          const dates = active.get(chain.id), cy = positions.get(chain.id);
          if (!dates.length) return;
          parts.push(`<g class="journal-unit" data-chains="${esc(chain.id)}" data-journal-chain="${esc(chain.id)}" data-chain-y="${cy}"><title>${esc(chain.label)}</title>`);
          dates.forEach((d, i) => {
            if (i) {
              const prev = dates[i - 1];
              parts.push(`<path class="${num(d.date) - num(prev.date) <= 1 ? "journal-chain-line" : "journal-pause"}" d="M${x(prev.date)},${cy} H${x(d.date)}"/>`);
            }
            const radius = Math.min(7, Math.max(2.1, 2.1 + .46 * Math.sqrt(d.total_commits)));
            parts.push(`<circle class="journal-dot${d.report ? " has-report" : ""}" data-date="${d.date}" cx="${x(d.date)}" cy="${cy}" r="${radius}"/>`);
          });
          if (chain.status === "done" && chain.end === dates.at(-1).date) parts.push(`<rect class="journal-seal" x="${x(dates.at(-1).date) - 3.5}" y="${cy - 3.5}" width="7" height="7"/>`);
          if (dates.length >= 3) {
            const lx = x(dates[0].date), shift = lx - previousLabel < 76 ? 10 : 0;
            parts.push(`<text class="journal-chain-label" x="${lx + 3}" y="${cy - 9 - shift}">${esc(chain.short)}</text>`);
            previousLabel = lx;
          }
          parts.push("</g>");
        });
      });
      parts.push(`<text class="journal-track-label" x="0" y="${bottom + 23}">每日汇报 ${new Set(days.flatMap(d => d.reports_covering || [])).size} 篇</text>`);
      days.filter(d => d.report).forEach(d => parts.push(`<path class="journal-report-tick" d="M${x(d.date)},${bottom + 10} v18"/>`));
      parts.push(`<text class="journal-axis-label" x="148" y="${bottom + 53}">${days[0].date}</text><text class="journal-axis-label" text-anchor="end" x="1208" y="${bottom + 53}">${days.at(-1).date}</text>`);
      // 每天整列命中；折线邻域由指针到线段的距离判定，避免列遮挡链条入口。
      days.forEach(d => parts.push(`<rect class="journal-day-hit" data-journal-day="${d.date}" x="${x(d.date) - 3.5}" y="30" width="7" height="${bottom - 6}"/>`));
      parts.push(`<path class="journal-hover-line" hidden d="M0,30 V${bottom + 24}"/></svg>`);
      scroller.innerHTML = parts.join("");
      const labels = [];
      scroller.querySelectorAll(".journal-chain-label").forEach(label => {
        let box = label.getBBox();
        label.setAttribute("x", Math.min(Number(label.getAttribute("x")), 1220 - box.width));
        for (let attempt = 0; attempt < 12; attempt++) {
          box = label.getBBox();
          if (!labels.some(b => box.x < b.x + b.width + 4 && box.x + box.width + 4 > b.x && box.y < b.y + b.height + 2 && box.y + box.height + 2 > b.y)) break;
          label.setAttribute("y", Number(label.getAttribute("y")) - 10);
        }
        labels.push(label.getBBox());
      });
      document.querySelector("#journal-figure figcaption").innerHTML = '<p>横轴按真实日期展开；实心点有汇报，空心点无汇报；虚线跨过没有记录的空档，方块表示收口。</p><div class="journal-handoff-legend" aria-label="交接线型">' + [["延续", ""], ["派生", "4 3"], ["依赖解除", "1 3"], ["收口", "7 2 1 2"]].map(([label, dash]) => `<span><svg aria-hidden="true" viewBox="0 0 34 8"><path d="M1 4 H33" stroke-dasharray="${dash}"/></svg>${label}</span>`).join("") + '<span>推断关系在脉络中标明</span></div>';
      this.atlas = {x, positions, days, height};
      if (this.chain && !this.visible.length) document.querySelector("#journal-figure figcaption").insertAdjacentHTML("beforeend", '<p class="journal-window-empty" role="status">此时间窗内没有这条链的记录。下方链条卡展示它的全部历史；可将时间窗改为“全部”查看图谱。</p>');
      this.highlightAtlas();
    },
    hideReadout() {
      document.querySelector(".journal-readout").hidden = true;
      document.querySelector(".journal-hover-line")?.setAttribute("hidden", "");
    },
    readout(event) {
      const hit = event.target.closest(".journal-day-hit, .journal-dot");
      const key = hit?.dataset.journalDay || hit?.dataset.date;
      if (!key) { this.hideReadout(); return; }
      const day = this.days.find(d => d.date === key);
      const figure = $("journal-figure"), tooltip = figure.querySelector(".journal-readout");
      tooltip.innerHTML = `<strong>${day.date} ${esc(day.weekday)}</strong><p>${esc(day.headline)}</p><p>${day.chains.map(c => esc(this.chains.get(c)?.short)).join(" / ") || "未归类"}</p><small>${day.total_commits} 次提交　${day.report ? "有每日汇报" : "无每日汇报"}</small>`;
      tooltip.hidden = false;
      const box = figure.getBoundingClientRect();
      let left = event.clientX - box.left + 14;
      if (left + tooltip.offsetWidth > box.width) left = event.clientX - box.left - tooltip.offsetWidth - 14;
      tooltip.style.left = Math.max(0, left) + "px";
      tooltip.style.top = Math.max(0, event.clientY - box.top - tooltip.offsetHeight - 12) + "px";
      const guide = figure.querySelector(".journal-hover-line");
      guide.removeAttribute("hidden"); guide.setAttribute("transform", `translate(${this.atlas.x(key)},0)`);
    },
    highlightAtlas() {
      const related = new Set(this.chain ? [this.chain] : []);
      if (this.chain) this.registry.handoffs.forEach(h => {
        if (h.from === this.chain) related.add(h.to);
        if (h.to === this.chain) related.add(h.from);
      });
      document.querySelectorAll(".journal-unit").forEach(g => {
        const lit = g.dataset.chains.split(" ").some(id => related.has(id));
        g.classList.toggle("is-dimmed", Boolean(this.chain) && !lit);
        g.classList.toggle("is-focused", Boolean(this.chain) && lit);
      });
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
      this.hideReadout();
      if (this.chain) { this.renderChainCard(); return; }
      const day = this.days.find(d => d.date === this.selected);
      if (!day || !this.visible.length) { $("journal-detail").innerHTML = ""; return; }
      const all = this.visibleDays(true), index = all.indexOf(day);
      const lineage = day.chains.map(cid => {
        const dates = this.days.filter(d => d.chains.includes(cid)), i = dates.indexOf(day);
        return `<p>${this.chainButton(cid)} 的相邻记录</p><div class="journal-chain-neighbors">${this.navButton(dates[i - 1], "上一天")}${this.navButton(dates[i + 1], "下一天")}</div>`;
      }).join("");
      $("journal-detail").innerHTML = `<nav class="journal-day-nav" aria-label="相邻工作日">${this.navButton(all[index - 1], "前一天")}${this.navButton(all[index + 1], "后一天")}</nav><article class="journal-day-card" data-selected-date="${day.date}"><div class="journal-day-top"><p><time>${day.date}</time>　${esc(day.weekday)}　${day.total_commits} 次提交</p>${day.report ? `<a href="#/daily/${day.report}">每日汇报 ↗</a>` : ""}</div><h2 class="${day.headline_source === "commit" ? "journal-draft" : ""}">${esc(day.headline)}${day.headline_source === "commit" ? " <small>待写</small>" : ""}</h2><p>${this.chainButtons(day)}</p><div class="journal-card-columns"><div><section><h3>做了什么</h3><ul id="journal-highlights">${day.highlights.map(h => `<li>${esc(h)}</li>`).join("") || '<li>当天没有可展示的提交或计划。</li>'}</ul></section><section><h3>脉络</h3>${this.flowHtml(day.chains) || '<p>未归类</p>'}${lineage}</section><div id="journal-body" class="markdown-body"></div></div><section><h3>根据</h3><details class="journal-evidence" data-evidence-date="${day.date}"><summary>提交、计划与汇报 <small>${day.total_commits} 次提交</small></summary><div id="journal-evidence-content"><p>正在读取证据…</p></div></details></section></div></article>`;
      document.querySelector(".journal-evidence").addEventListener("toggle", e => {
        if (e.target.open) this.loadEvidence(day.date);
      });
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
        if (!day.highlights.length) {
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
      return repos + `<h4>计划</h4><ul>${(ev.plans || []).map(p => `<li>${esc(p.title)}<small>${esc(p.repo)} / ${esc(p.file)}</small></li>`).join("") || "<li>无计划文件</li>"}</ul><h4>覆盖这天工作的汇报</h4><ul>${(ev.reports_covering || []).filter(d => this.reports.has(d)).map(report).join("") || "<li>无</li>"}</ul><h4>这天发布的汇报</h4><ul>${(ev.reports_published || []).filter(d => this.reports.has(d)).map(report).join("") || "<li>无</li>"}</ul>`;
    },
    renderChainCard() {
      const chain = this.chains.get(this.chain);
      const days = this.days.filter(d => d.chains.includes(chain.id));
      const reports = [...new Set([...days.flatMap(d => d.reports_covering || []), ...(chain.closes_into?.daily || [])])].filter(d => this.reports.has(d));
      const track = this.registry.tracks.find(t => t.id === chain.track);
      const windowNote = !this.visible.length ? '<p class="journal-window-empty" role="status">此时间窗内没有这条链的记录。下面展示这条链的全部历史。</p>' : "";
      $("journal-detail").innerHTML = `<article class="journal-day-card journal-chain-card">${windowNote}<p>${esc(track?.label)}　${days.length} 天　${chain.start} 至 ${chain.end}</p><h2>${esc(chain.label)}</h2><p>${esc(chain.purpose)}</p><h3>承接与交接</h3>${this.flowHtml([chain.id])}<h3>落成的汇报与成果</h3><ul>${reports.map(d => `<li><a href="#/daily/${d}">${d} ${esc(this.reports.get(d).title)}</a></li>`).join("") || "<li>尚无关联汇报</li>"}${chain.closes_into?.showcase ? `<li><a href="#/showcase/${esc(chain.closes_into.showcase)}">正式成果：${esc(this.app.getStage(chain.closes_into.showcase).label)}</a></li>` : ""}</ul><h3>这条链上的每一天</h3><div class="journal-chain-days">${days.map(d => `<button type="button" data-journal-day="${d.date}"><time>${d.date}</time><span>${esc(d.headline)}</span>${d.chain_confidence[chain.id] === "inferred" ? '<small>归属待核</small>' : ""}</button>`).join("")}</div></article>`;
    },
  };
  window.JournalView = JournalView;
})();
