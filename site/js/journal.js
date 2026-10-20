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
      this.mode = "list";
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
        const day = e.target.closest("[data-journal-day]");
        if (day) { e.preventDefault(); this.select(day.dataset.journalDay, true); }
        const chain = e.target.closest("[data-journal-chain]");
        if (chain) this.focusChain(chain.dataset.journalChain);
      });
    },
    show(key) {
      const params = new URLSearchParams(location.hash.split("?")[1] || "");
      this.mode = params.get("view") === "atlas" ? "atlas" : "list";
      this.chain = this.chains.has(params.get("chain")) ? params.get("chain") : "";
      this.window = ["1m", "3m"].includes(params.get("window")) ? params.get("window") : "all";
      if (this.days.some(d => d.date === key)) this.selected = key;
      this.render();
      if (key) requestAnimationFrame(() => $("journal-detail").scrollIntoView({block: "start"}));
    },
    visibleDays() {
      const end = this.days.at(-1)?.date;
      if (!end) return [];
      const start = new Date(`${end}T00:00:00Z`);
      if (this.window !== "all") start.setUTCMonth(start.getUTCMonth() - (this.window === "1m" ? 1 : 3));
      const cutoff = this.window === "all" ? "0000" : start.toISOString().slice(0, 10);
      const q = this.query.trim().toLocaleLowerCase();
      return this.days.filter(d => d.date >= cutoff && (!this.chain || d.chains.includes(this.chain)) &&
        (!q || [d.date, d.headline, ...d.chains.map(cid => this.chains.get(cid)?.label || cid)].join(" ").toLocaleLowerCase().includes(q)));
    },
    writeHash() {
      const params = new URLSearchParams();
      if (this.chain) params.set("chain", this.chain);
      if (this.mode === "list") params.set("view", "list");
      if (this.window !== "all") params.set("window", this.window);
      history.replaceState(null, "", `#/journal${this.selected ? "/" + this.selected : ""}${params.size ? "?" + params : ""}`);
    },
    select(key, scroll = false) {
      this.selected = key;
      this.chain = "";
      this.render(); this.writeHash();
      if (scroll) $("journal-detail").scrollIntoView({block: "start"});
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
      this.visible = this.visibleDays();
      if (!this.visible.some(d => d.date === this.selected)) this.selected = this.visible[0]?.date;
      $("journal-window").value = this.window;
      $("journal-chain").value = this.chain;
      $("journal-clear").hidden = !this.chain;
      const reports = new Set(this.visible.flatMap(d => d.reports_covering || []));
      $("journal-count").textContent = `${this.visible.length} 天 / ${reports.size} 篇汇报`;
      document.querySelectorAll("[data-journal-view]").forEach(b => b.setAttribute("aria-pressed", String(b.dataset.journalView === this.mode)));
      this.renderList();
      this.renderDetail();
    },
    renderList() {
      $("journal-list").innerHTML = this.visible.length ? `<table><caption class="sr-only">按真实工作日期排列的日志</caption><thead><tr><th scope="col">日期</th><th scope="col">这天做了什么</th><th scope="col">链条</th><th scope="col">提交</th><th scope="col">汇报</th></tr></thead><tbody>${this.visible.map(d => `<tr class="${d.report ? "has-report" : ""}" data-date="${d.date}" ${d.date === this.selected ? 'aria-current="date"' : ""}><td><a href="#/journal/${d.date}" data-journal-day="${d.date}">${d.date}</a><small>${esc(d.weekday)}</small></td><td><a href="#/journal/${d.date}" data-journal-day="${d.date}">${esc(d.headline)}</a>${d.headline_source === "commit" ? '<small>待写</small>' : ""}</td><td>${this.chainButtons(d)}</td><td class="journal-number">${d.total_commits}</td><td>${this.reportLinks(d) || "—"}</td></tr>`).join("")}</tbody></table>` : '<p class="journal-empty">没有匹配的日期。请调整时间窗、链条或查找词。</p>';
    },
    renderDetail() {
      const day = this.days.find(d => d.date === this.selected);
      $("journal-detail").innerHTML = day ? `<article class="journal-day-card"><p>${day.date}　${esc(day.weekday)}　${day.total_commits} 次提交</p><h2>${esc(day.headline)}</h2><p>${this.chainButtons(day)}</p><p>${this.reportLinks(day)}</p>${day.highlights.map(h => `<p>${esc(h)}</p>`).join("")}</article>` : "";
    },
  };
  window.JournalView = JournalView;
})();
