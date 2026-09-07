(function () {
  "use strict";
  const M = window.ReportTagModel;
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({"&":"&amp;", "<":"&lt;", ">":"&gt;", '"':"&quot;", "'":"&#39;"}[c]));
  const uid = () => crypto.randomUUID?.() || `tag_${Date.now()}_${Math.random().toString(36).slice(2)}`;
  const $ = (id) => document.getElementById(id);
  const UI = {
    selected: [], query: "", mode: "single", collapsed: false,
    checked: new Set(), undoStack: [], revision: 0, dirty: false, saving: false,
    canEdit: false, ready: false, conflict: false, pending: null, managerTab: "assign",

    async init(daily) {
      this.daily = daily;
      this.data = M.validate(daily.manifest.report_tags || {schemaVersion: 1, tags: [], assignments: {}});
      this.offline = document.body.dataset.offline === "true" || location.protocol === "file:";
      this.storageKey = `report-tags-v1:${location.pathname}:${this.offline ? "offline" : "online"}`;
      this.mount();
      this.readURL();
      if (this.offline) {
        this.ready = this.canEdit = true;
        const saved = this.readLocal();
        if (saved?.data) { try { this.data = M.validate(saved.data); } catch { /* Keep bundled snapshot. */ } }
        this.status = "离线副本 · 修改仅保存在此浏览器";
      } else {
        await this.refresh(true);
      }
      this.render();
      window.addEventListener("beforeunload", (event) => {
        if (!this.dirty) return;
        event.preventDefault(); event.returnValue = "";
      });
      window.addEventListener("online", () => { if (this.dirty && !this.conflict) this.save(); else this.refresh(); });
      window.addEventListener("focus", () => this.refresh());
      document.addEventListener("visibilitychange", () => { if (!document.hidden) this.refresh(); });
    },

    mount() {
      $("report-tag-toolbar").innerHTML = `
        <div class="tag-strip"><button id="reports-all" class="tag-all" type="button" aria-controls="daily-timeline">汇报一览</button>
        <div id="report-tag-buttons" class="tag-scroll" aria-label="按标签筛选"></div>
        <button id="tags-edit" class="tag-edit" type="button" title="管理标签与汇报归属" aria-label="管理标签与汇报归属"><svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true"><path d="m15 5 4 4M4 20l4-1L20 7a2.8 2.8 0 0 0-4-4L4 15z"/></svg></button></div>
        <div class="tag-search"><input id="report-list-search" type="search" placeholder="搜索标题、摘要或日期" aria-label="搜索汇报列表"><button id="tag-share" type="button" title="复制当前主题链接" aria-label="复制当前主题链接">↗</button></div>
        <div class="tag-filter-options"><label>筛选 <select id="tag-filter-mode" aria-label="标签筛选方式"><option value="single">单标签</option><option value="any">任意标签</option><option value="all">全部标签</option></select></label><button id="tags-reset" type="button">重置</button></div>
        <p id="report-filter-status" class="tag-hint" role="status"></p><p id="report-current-outside" class="tag-hint" hidden>当前文章不在筛选结果中</p>
        <div class="tag-sync-line"><span id="tag-sync-status" role="status"></span><button id="tag-retry-inline" type="button" hidden>重试</button></div>`;
      $("reports-all").onclick = () => {
        const isAll = !this.selected.length && !this.query;
        this.collapsed = isAll && !this.collapsed;
        this.selected = []; this.query = ""; this.applyFilter();
      };
      $("report-list-search").oninput = (e) => { this.query = e.target.value; this.collapsed = false; this.applyFilter(); };
      $("tag-filter-mode").onchange = (e) => {
        this.mode = e.target.value;
        if (this.mode === "single") this.selected = this.selected.slice(0, 1);
        this.collapsed = false; this.applyFilter();
      };
      $("tags-reset").onclick = () => { this.selected = []; this.query = ""; this.collapsed = false; this.applyFilter(); };
      $("tags-edit").onclick = () => this.openManager();
      $("tag-share").onclick = () => this.share();
      $("tag-retry-inline").onclick = () => this.dirty ? this.save() : this.refresh(true);
      $("tag-manager").innerHTML = `
        <div class="tag-manager-head"><div><span class="tag-eyebrow">REPORT COLLECTION</span><h2 id="tag-manager-title">整理汇报</h2></div><button id="tag-manager-close" type="button" aria-label="关闭标签管理">×</button></div>
        <nav class="tag-manager-tabs" aria-label="管理内容"><button type="button" data-manager-tab="assign">汇报归类</button><button type="button" data-manager-tab="tags">标签管理</button><button type="button" data-manager-tab="suggest">归类建议</button></nav>
        <p id="tag-manager-message" role="status" class="tag-manager-message"></p>
        <section id="tag-panel-assign">
          <div class="tag-manager-search"><input id="tag-manager-search" type="search" placeholder="搜索标题、摘要或日期" aria-label="搜索待归类汇报"><select id="tag-manager-filter" aria-label="筛选待归类汇报"></select></div>
          <div class="tag-bulk"><label><input id="tag-select-all" type="checkbox">全选当前筛选结果</label><span id="tag-selected-count"></span><select id="tag-bulk-target" aria-label="批量操作标签"></select><button id="tag-bulk-add" type="button">添加标签</button><button id="tag-bulk-remove" type="button">移除标签</button></div>
          <div id="tag-assignment-list" class="tag-assignment-list"></div>
        </section>
        <section id="tag-panel-tags" hidden>
          <form id="tag-create-form" class="tag-create"><input id="tag-new-name" maxlength="40" required placeholder="新标签名称" aria-label="新标签名称"><input id="tag-new-color" type="color" value="#477d75" aria-label="新标签颜色"><button type="submit">新增标签</button></form>
          <p class="tag-hint">用 ↑ ↓ 调整顺序。关键词用逗号分隔，用于标题与摘要的归类建议。</p><div id="tag-definition-list"></div>
        </section>
        <section id="tag-panel-suggest" hidden><p class="tag-hint">根据标题、摘要与标签关键词匹配生成，仅在采纳后添加标签。可在“标签管理”中调整关键词。</p><div class="tag-suggest-tools"><label><input id="suggest-select-all" type="checkbox">全选建议</label><button id="suggest-accept" type="button">采纳所选建议</button></div><div id="tag-suggestion-list"></div></section>
        <footer class="tag-manager-footer"><span id="tag-save-status" role="status"></span><div><button id="tag-undo" type="button">撤销上次修改</button><button id="tag-save-retry" type="button" hidden>重试保存</button><button id="tag-reload" type="button" hidden>放弃草稿并载入最新</button><button id="tag-export" type="button">导出标签</button><button id="tag-import" type="button">导入标签</button></div><input id="tag-import-file" type="file" accept=".json,application/json" hidden></footer>`;
      $("tag-manager-close").onclick = () => $("tag-manager").close();
      document.querySelectorAll("[data-manager-tab]").forEach((b) => b.onclick = () => { this.managerTab = b.dataset.managerTab; this.renderManager(); });
      $("tag-manager-search").oninput = () => { this.checked.clear(); this.renderAssignments(); };
      $("tag-manager-filter").onchange = () => { this.checked.clear(); this.renderAssignments(); };
      $("tag-select-all").onchange = (e) => { this.checked = new Set(e.target.checked ? this.managerItems().map(M.key) : []); this.renderAssignments(); };
      $("tag-bulk-add").onclick = () => this.bulk("add");
      $("tag-bulk-remove").onclick = () => this.bulk("remove");
      $("tag-create-form").onsubmit = (e) => {
        e.preventDefault(); const next = M.clone(this.data);
        next.tags.push({id: uid(), name: $("tag-new-name").value.trim(), color: $("tag-new-color").value, keywords: []});
        if (this.change(next, "已新增标签")) $("tag-new-name").value = "";
      };
      $("tag-undo").onclick = () => {
        const previous = this.undoStack.pop();
        if (previous) this.change(previous, "已撤销上次修改", false);
      };
      $("tag-save-retry").onclick = () => this.save();
      $("tag-reload").onclick = async () => {
        if (!confirm("放弃本地未保存修改并载入线上最新版本？如需保留，请先导出标签。")) return;
        this.dirty = this.conflict = false; this.pending = null; this.undoStack = [];
        this.writeLocal(); await this.refresh(true);
      };
      $("tag-export").onclick = () => this.exportData();
      $("tag-import").onclick = () => $("tag-import-file").click();
      $("tag-import-file").onchange = (e) => this.importData(e.target.files[0]);
      $("suggest-select-all").onchange = (e) => {
        $("tag-suggestion-list").querySelectorAll("input[type=checkbox]").forEach((box) => box.checked = e.target.checked);
        this.updateSuggestionCount();
      };
      $("suggest-accept").onclick = () => {
        let next = this.data; let count = 0;
        $("tag-suggestion-list").querySelectorAll("input:checked").forEach((box) => { next = M.assign(next, [box.dataset.report], [box.dataset.tag], "add"); count++; });
        if (count) this.change(next, `已采纳 ${count} 条建议`);
      };
    },

    readLocal() { try { return JSON.parse(localStorage.getItem(this.storageKey)); } catch { return null; } },
    writeLocal() {
      try {
        localStorage.setItem(this.storageKey, JSON.stringify({data: this.data, revision: this.revision, dirty: this.dirty, pending: this.pending}));
        this.localError = false;
      } catch { this.localError = true; }
    },
    async request(options = {}) {
      const response = await fetch("api/report-tags", {cache: "no-store", credentials: "same-origin", signal: AbortSignal.timeout(10000), ...options});
      if (!response.headers.get("content-type")?.includes("application/json")) throw new Error("未能连接标签服务，请检查登录状态后重试");
      const result = await response.json();
      if (!response.ok) { const error = new Error(result.error || "标签服务暂时不可用"); error.status = response.status; throw error; }
      return result;
    },
    async refresh(initial = false) {
      if (this.offline || this.saving || (this.dirty && !initial) || this.refreshing || (!initial && this.ready && $("tag-manager").open)) return;
      this.refreshing = true;
      try {
        const response = await this.request();
        if (!initial && (this.dirty || this.saving || $("tag-manager").open)) return;
        const data = M.validate(response.data);
        this.loadFailed = false;
        this.canEdit = response.canEdit === true; this.ready = true;
        const draft = initial ? this.readLocal() : null;
        if (draft?.dirty && this.canEdit) {
          this.data = M.validate(draft.data); this.revision = draft.revision; this.dirty = true; this.pending = draft.pending;
          this.conflict = response.revision !== this.revision && response.mutationId !== this.pending?.mutationId;
          this.status = this.conflict ? "线上已有新修改；草稿已保留，请导出后载入最新" : "已恢复未保存草稿，请重试保存";
        } else {
          this.data = data; this.revision = response.revision; this.conflict = false;
          this.status = this.canEdit ? "已同步" : "浏览模式";
          this.writeLocal();
        }
      } catch (error) {
        this.loadFailed = true;
        this.status = error.message;
        if (!this.ready) {
          const cached = this.readLocal();
          if (cached?.data) { try { this.data = M.validate(cached.data); } catch { /* Invalid cache ignored. */ } }
          this.status += " · 当前显示缓存或随站快照";
        }
      } finally { this.refreshing = false; this.render(); }
    },
    change(next, message, recordUndo = true) {
      if (!this.canEdit || this.conflict) { this.message(this.conflict ? "请先处理版本冲突，草稿可导出保留" : "当前无法编辑，请连接标签服务后重试"); return false; }
      try { next = M.validate(next); }
      catch (error) { this.message(error.message); return false; }
      if (JSON.stringify(next) === JSON.stringify(this.data)) { this.message("没有需要修改的归属"); return true; }
      if (recordUndo) { this.undoStack.push(M.clone(this.data)); if (this.undoStack.length > 30) this.undoStack.shift(); }
      this.data = next; this.dirty = !this.offline;
      this.selected = this.selected.filter((id) => id === "_untagged" || next.tags.some((t) => t.id === id));
      this.status = this.offline ? "已保存到此浏览器 · 可导出备份" : "等待保存";
      this.writeLocal(); this.render(); this.writeURL(); this.message(message);
      if (!this.offline) { clearTimeout(this.saveTimer); this.saveTimer = setTimeout(() => this.save(), 300); }
      return true;
    },
    async save() {
      if (this.offline || this.saving || !this.dirty || this.conflict || !this.canEdit) return;
      this.saving = true; this.status = "保存中…"; this.renderStatus();
      try {
        while (this.dirty) {
          // Retain the exact request after an uncertain failure, even if later edits have queued.
          if (!this.pending) this.pending = {revision: this.revision, mutationId: uid(), data: M.clone(this.data)};
          this.writeLocal();
          const response = await this.request({method: "PUT", headers: {"Content-Type": "application/json"}, body: JSON.stringify(this.pending)});
          this.revision = response.revision;
          this.dirty = JSON.stringify(this.data) !== JSON.stringify(this.pending.data);
          this.pending = null; this.writeLocal();
        }
        this.status = "已保存";
      } catch (error) {
        this.conflict = error.status === 409;
        this.status = this.conflict ? "线上已有新修改；草稿已保留，请导出后载入最新" : `保存失败：${error.message}`;
        this.writeLocal();
      } finally { this.saving = false; this.renderStatus(); }
    },
    message(text) { $("tag-manager-message").textContent = text; },
    renderStatus() {
      const text = `${this.status || "连接标签服务…"}${this.localError ? " · 浏览器备份失败，请导出保留" : ""}`;
      $("tag-sync-status").textContent = text;
      $("tag-save-status").textContent = text;
      $("tag-retry-inline").hidden = this.offline || this.saving || this.conflict || (this.ready && !this.dirty && !this.loadFailed);
      $("tag-save-retry").hidden = !this.dirty || this.saving || this.conflict;
      $("tag-reload").hidden = !this.conflict;
      $("tag-undo").disabled = !this.canEdit || !this.undoStack.length || this.conflict;
      $("tag-import").disabled = !this.canEdit || this.conflict;
    },

    readURL() {
      const params = new URLSearchParams(location.hash.split("?")[1] || "");
      this.selected = [...new Set((params.get("tags") || "").split(",").filter((s) => s === "_untagged" || M.safeId(s)))];
      this.mode = ["any", "all"].includes(params.get("match")) ? params.get("match") : "single";
      if (this.mode === "single") this.selected = this.selected.slice(0, 1);
      this.query = params.get("q") || ""; this.collapsed = params.get("list") === "hidden";
    },
    suffix() {
      const params = new URLSearchParams();
      if (this.selected.length) params.set("tags", this.selected.join(","));
      if (this.mode !== "single") params.set("match", this.mode);
      if (this.query) params.set("q", this.query);
      if (this.collapsed) params.set("list", "hidden");
      return params.size ? `?${params}` : "";
    },
    route(date, mode = "doc") { return `#/daily/${date}${mode === "show" ? "/show" : ""}${this.suffix()}`; },
    writeURL() {
      if (location.hash.startsWith("#/daily")) history.replaceState(null, "", `${location.hash.split("?")[0]}${this.suffix()}`);
    },
    applyFilter() { this.writeURL(); this.render(); },
    selectTag(id) {
      if (this.mode === "single") this.selected = this.selected.includes(id) ? [] : [id];
      else this.selected = this.selected.includes(id) ? this.selected.filter((t) => t !== id) : [...this.selected, id];
      this.collapsed = false; this.applyFilter();
    },
    items() { return M.filter(this.daily.manifest.daily, this.data, {tags: this.selected, mode: this.mode, query: this.query}); },
    chips(item) {
      const ids = this.data.assignments[M.key(item)] || [];
      return this.data.tags.filter((t) => ids.includes(t.id)).map((t) => `<span class="report-chip" style="--tag-color:${t.color}">${esc(t.name)}</span>`).join("");
    },
    render() {
      if (!this.daily) return;
      const items = this.daily.manifest.daily;
      const counts = new Map(this.data.tags.map((t) => [t.id, 0])); let untagged = 0;
      for (const item of items) {
        const tags = this.data.assignments[M.key(item)] || [];
        if (!tags.length) untagged++;
        tags.forEach((id) => counts.set(id, (counts.get(id) || 0) + 1));
      }
      const scroll = $("report-tag-buttons").scrollLeft;
      const focusedTag = document.activeElement?.dataset.tagFilter;
      $("report-tag-buttons").innerHTML = [...this.data.tags.map((t) => ({...t, count: counts.get(t.id)})), {id:"_untagged", name:"未标记", color:"#68716f", count:untagged}].map((t) =>
        `<button type="button" class="tag-filter${this.selected.includes(t.id) ? " is-active" : ""}" data-tag-filter="${t.id}" aria-pressed="${this.selected.includes(t.id)}" title="${esc(t.name)} · ${t.count} 篇" style="--tag-color:${t.color}">${esc(t.name)}<span>${t.count}</span></button>`).join("");
      $("report-tag-buttons").scrollLeft = scroll;
      $("report-tag-buttons").querySelectorAll("button").forEach((b) => b.onclick = () => this.selectTag(b.dataset.tagFilter));
      if (focusedTag) $("report-tag-buttons").querySelector(`[data-tag-filter="${focusedTag}"]`)?.focus({preventScroll: true});
      const all = !this.selected.length && !this.query && !this.collapsed;
      $("reports-all").classList.toggle("is-active", all);
      $("reports-all").setAttribute("aria-pressed", String(all));
      $("reports-all").setAttribute("aria-expanded", String(!this.collapsed));
      $("report-list-search").value = this.query;
      $("tag-filter-mode").value = this.mode;
      const unknown = this.selected.filter((id) => id !== "_untagged" && !counts.has(id));
      $("report-filter-status").textContent = this.collapsed ? "列表已收起" : unknown.length ? "链接中的标签已删除，可重置筛选" : `显示 ${this.items().length} / ${items.length} 篇`;
      this.daily.renderTimeline();
      this.daily.updateNav();
      const current = items[this.daily.currentIndex];
      if (current) { this.daily.updateTimeline(current.date); this.renderCurrent(current); }
      if ($("tag-manager").open) this.renderManager();
      this.renderStatus();
    },
    renderCurrent(item) {
      $("daily-report-tags").innerHTML = `${this.chips(item) || '<span class="tag-hint">未标记</span>'}<button id="tag-edit-current" type="button">编辑标签</button>`;
      $("tag-edit-current").onclick = () => this.openManager(M.key(item));
      $("tag-edit-current").disabled = !this.canEdit;
      $("report-current-outside").hidden = this.items().some((i) => M.key(i) === M.key(item));
    },
    async share() {
      const item = this.daily.manifest.daily[this.daily.currentIndex];
      const url = `${location.href.split("#")[0]}${this.route(item?.date || "")}`;
      try { await navigator.clipboard.writeText(url); this.daily.notice("已复制当前主题链接"); }
      catch { prompt("复制当前主题链接", url); }
    },

    openManager(report) {
      this.managerTab = "assign"; this.checked.clear();
      $("tag-manager-search").value = report ? this.daily.manifest.daily.find((i) => M.key(i) === report)?.date || "" : "";
      $("tag-manager-filter").value = "";
      if (report) this.checked.add(report);
      this.message(this.canEdit ? "修改会自动保存；批量添加标签会保留原有标签。" : "当前为浏览模式，可导出标签；连接服务后可编辑。");
      $("tag-manager").showModal(); this.renderManager();
    },
    options(selected = "", all = false) {
      return `${all ? '<option value="">全部汇报</option><option value="_untagged">未标记</option>' : ''}${this.data.tags.map((t) => `<option value="${t.id}"${selected === t.id ? " selected" : ""}>${esc(t.name)}</option>`).join("")}`;
    },
    renderManager() {
      document.querySelectorAll("[data-manager-tab]").forEach((b) => { const active = b.dataset.managerTab === this.managerTab; b.classList.toggle("is-active", active); b.setAttribute("aria-pressed", String(active)); });
      ["assign", "tags", "suggest"].forEach((tab) => $("tag-panel-" + tab).hidden = tab !== this.managerTab);
      const managerFilter = $("tag-manager-filter").value, bulk = $("tag-bulk-target").value;
      $("tag-manager-filter").innerHTML = this.options(managerFilter, true);
      if (managerFilter === "_untagged") $("tag-manager-filter").value = managerFilter;
      $("tag-bulk-target").innerHTML = this.options(bulk);
      if (this.managerTab === "assign") this.renderAssignments();
      if (this.managerTab === "tags") this.renderDefinitions();
      if (this.managerTab === "suggest") this.renderSuggestions();
      $("tag-create-form").querySelectorAll("input,button").forEach((el) => el.disabled = !this.canEdit || this.conflict);
      this.renderStatus();
    },
    managerItems() {
      const tag = $("tag-manager-filter").value;
      return M.filter(this.daily.manifest.daily, this.data, {query: $("tag-manager-search").value, tags: tag ? [tag] : []});
    },
    renderAssignments() {
      const items = this.managerItems(), visible = new Set(items.map(M.key));
      this.checked = new Set([...this.checked].filter((id) => visible.has(id)));
      $("tag-selected-count").textContent = `已选 ${this.checked.size} / ${items.length} 篇`;
      $("tag-select-all").checked = !!items.length && this.checked.size === items.length;
      $("tag-select-all").indeterminate = this.checked.size > 0 && this.checked.size < items.length;
      $("tag-select-all").disabled = !items.length || !this.canEdit;
      $("tag-bulk-add").disabled = $("tag-bulk-remove").disabled = !this.checked.size || !this.data.tags.length || !this.canEdit || this.conflict;
      $("tag-assignment-list").innerHTML = items.length ? items.map((item) => `<div class="tag-report-row"><label class="tag-report-select"><input type="checkbox" data-report-check="${M.key(item)}" ${this.checked.has(M.key(item)) ? "checked" : ""} ${!this.canEdit ? "disabled" : ""}><span><span class="tag-report-date">${esc(item.date)}</span><strong>${esc(item.title)}</strong></span></label><div class="tag-row-chips">${this.chips(item) || '<span class="tag-hint">未标记</span>'}</div><details><summary>查看摘要</summary><p>${esc(item.summary || "无摘要")}</p></details><div class="tag-row-actions"><select data-quick-target="${M.key(item)}" aria-label="为 ${esc(item.date)} 选择标签">${this.options()}</select><button type="button" data-quick-add="${M.key(item)}" ${!this.canEdit || !this.data.tags.length ? "disabled" : ""}>添加</button><button type="button" data-quick-remove="${M.key(item)}" ${!this.canEdit || !this.data.tags.length ? "disabled" : ""}>移除</button></div></div>`).join("") : '<p class="tag-empty">没有匹配的汇报</p>';
      $("tag-assignment-list").querySelectorAll("[data-report-check]").forEach((box) => box.onchange = () => {
        if (box.checked) this.checked.add(box.dataset.reportCheck); else this.checked.delete(box.dataset.reportCheck);
        // Keep the active checkbox and scroll position stable while selecting several rows.
        $("tag-selected-count").textContent = `已选 ${this.checked.size} / ${items.length} 篇`;
        $("tag-select-all").checked = this.checked.size === items.length;
        $("tag-select-all").indeterminate = this.checked.size > 0 && this.checked.size < items.length;
        $("tag-bulk-add").disabled = $("tag-bulk-remove").disabled = !this.checked.size || !this.data.tags.length || !this.canEdit || this.conflict;
      });
      ["add", "remove"].forEach((action) => $("tag-assignment-list").querySelectorAll(`[data-quick-${action}]`).forEach((b) => b.onclick = () => {
        const id = b.getAttribute(`data-quick-${action}`), tag = b.parentElement.querySelector("select").value;
        this.change(M.assign(this.data, [id], [tag], action), "已更新当前汇报标签");
      }));
    },
    bulk(action) {
      const target = $("tag-bulk-target").value;
      if (!target || !this.checked.size) return;
      this.change(M.assign(this.data, [...this.checked], [target], action), `已为 ${this.checked.size} 篇汇报${action === "add" ? "添加" : "移除"}标签`);
    },
    renderDefinitions() {
      $("tag-definition-list").innerHTML = this.data.tags.map((tag, index) => {
        const count = Object.values(this.data.assignments).filter((tags) => tags.includes(tag.id)).length;
        return `<form class="tag-definition" data-definition="${tag.id}"><div class="tag-definition-main"><input name="name" value="${esc(tag.name)}" maxlength="40" aria-label="标签名称 ${esc(tag.name)}" required><input name="color" type="color" value="${tag.color}" aria-label="标签颜色 ${esc(tag.name)}"><span class="tag-hint">${count} 篇</span><button type="button" data-move="-1" aria-label="上移 ${esc(tag.name)}" ${!index ? "disabled" : ""}>↑</button><button type="button" data-move="1" aria-label="下移 ${esc(tag.name)}" ${index === this.data.tags.length - 1 ? "disabled" : ""}>↓</button></div><label class="tag-keywords">建议关键词<input name="keywords" value="${esc(tag.keywords.join(", "))}" placeholder="用逗号分隔" aria-label="建议关键词 ${esc(tag.name)}"></label><div class="tag-definition-actions"><button type="submit">保存修改</button><select name="merge" aria-label="${esc(tag.name)} 的合并目标"><option value="">选择合并目标</option>${this.data.tags.filter((t) => t.id !== tag.id).map((t) => `<option value="${t.id}">${esc(t.name)}</option>`).join("")}</select><button type="button" data-merge>合并到</button><button type="button" data-delete class="tag-danger">删除</button></div></form>`;
      }).join("") || '<p class="tag-empty">还没有标签，可以在上方新增。</p>';
      $("tag-definition-list").querySelectorAll("form").forEach((form) => {
        const id = form.dataset.definition;
        if (!this.canEdit || this.conflict) form.querySelectorAll("input,button,select").forEach((el) => el.disabled = true);
        form.onsubmit = (e) => {
          e.preventDefault(); const next = M.clone(this.data), tag = next.tags.find((t) => t.id === id);
          tag.name = form.elements.name.value.trim(); tag.color = form.elements.color.value;
          tag.keywords = form.elements.keywords.value.split(/[,，\n]/).map((s) => s.trim()).filter(Boolean);
          this.change(next, "已保存标签名称、颜色与关键词");
        };
        form.querySelectorAll("[data-move]").forEach((b) => b.onclick = () => {
          const next = M.clone(this.data), index = next.tags.findIndex((t) => t.id === id), target = index + Number(b.dataset.move);
          if (target < 0 || target >= next.tags.length) return;
          [next.tags[index], next.tags[target]] = [next.tags[target], next.tags[index]];
          this.change(next, "已调整标签顺序");
        });
        form.querySelector("[data-delete]").onclick = () => {
          const tag = this.data.tags.find((t) => t.id === id), count = Object.values(this.data.assignments).filter((ts) => ts.includes(id)).length;
          if (confirm(`删除“${tag.name}”并解除 ${count} 篇汇报的该标签？汇报正文会保留，操作可撤销。`)) this.change(M.remove(this.data, id), "已删除标签，可撤销");
        };
        form.querySelector("[data-merge]").onclick = () => {
          const target = form.elements.merge.value;
          if (!target) return this.message("请先选择合并目标");
          const from = this.data.tags.find((t) => t.id === id), to = this.data.tags.find((t) => t.id === target);
          if (confirm(`把“${from.name}”的全部归属并入“${to.name}”，然后移除“${from.name}”？操作可撤销。`)) this.change(M.remove(this.data, id, target), "已合并标签，可撤销");
        };
      });
    },
    renderSuggestions() {
      const rows = this.daily.manifest.daily.flatMap((item) => M.suggest(item, this.data).map((s) => ({item, ...s})));
      $("tag-suggestion-list").innerHTML = rows.map(({item, id, hits}) => `<label class="tag-suggestion"><input type="checkbox" data-report="${M.key(item)}" data-tag="${id}" ${!this.canEdit ? "disabled" : ""}><span><span class="tag-report-date">${item.date}</span><strong>${esc(item.title)}</strong><span class="tag-suggestion-reason">建议：${esc(this.data.tags.find((t) => t.id === id).name)} · 匹配“${esc(hits.join("、"))}”</span></span></label>`).join("") || '<p class="tag-empty">暂无新建议。可在标签管理中补充关键词。</p>';
      $("suggest-select-all").checked = false;
      $("suggest-select-all").disabled = !rows.length || !this.canEdit || this.conflict;
      $("tag-suggestion-list").querySelectorAll("input").forEach((box) => box.onchange = () => this.updateSuggestionCount());
      this.updateSuggestionCount();
    },
    updateSuggestionCount() {
      const boxes = [...$("tag-suggestion-list").querySelectorAll("input")], count = boxes.filter((b) => b.checked).length;
      $("suggest-accept").textContent = `采纳所选建议${count ? `（${count}）` : ""}`;
      $("suggest-accept").disabled = !count || !this.canEdit || this.conflict;
      $("suggest-select-all").checked = !!boxes.length && count === boxes.length;
      $("suggest-select-all").indeterminate = count > 0 && count < boxes.length;
    },
    exportData() {
      const blob = new Blob([JSON.stringify({...this.data, exportedAt: new Date().toISOString(), revision: this.revision, unsaved: this.dirty}, null, 2)], {type: "application/json"});
      const url = URL.createObjectURL(blob), link = document.createElement("a");
      link.href = url; link.download = `report-tags-${new Date().toISOString().slice(0, 10)}${this.dirty ? "-draft" : ""}.json`; link.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
      this.message(this.dirty ? "已导出未保存草稿；可在载入最新后合并导入" : "已导出标签与汇报归属，可用于备份或离线构建");
    },
    async importData(file) {
      $("tag-import-file").value = "";
      if (!file) return;
      try {
        if (file.size > 512 * 1024) throw new Error("文件超过 512 KB");
        const incoming = M.validate(JSON.parse(await file.text()));
        if (!confirm(`导入 ${incoming.tags.length} 个标签、${Object.keys(incoming.assignments).length} 篇汇报归属？将与现有数据合并，保留当前标签名称与其他归属；操作可撤销。`)) return;
        this.change(M.mergeImport(this.data, incoming), "已合并导入标签，可撤销");
      } catch (error) { this.message(`导入失败：${error.message}`); }
    },
  };
  window.ReportTagsUI = UI;
})();
