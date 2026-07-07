(function () {
  function escapeHtml(text) {
    return String(text ?? "").replace(/[&<>"']/g, (char) => ({
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      "\"": "&quot;",
      "'": "&#39;",
    }[char]));
  }

  const DailyView = {
    manifest: null,
    app: null,
    currentIndex: 0,
    currentMode: "doc",
    currentScene: 0,
    timelineEl: null,
    contentEl: null,
    showEl: null,
    tocEl: null,
    mainlineEl: null,
    noticeTimer: null,

    async init(manifest, app) {
      this.manifest = manifest;
      this.app = app;
      this.timelineEl = document.getElementById("daily-timeline");
      this.contentEl = document.getElementById("daily-content");
      this.showEl = document.getElementById("daily-show-content");
      this.tocEl = document.getElementById("daily-toc");
      this.mainlineEl = document.querySelector(".daily-mainline");
      this.renderTimeline();
      this.bind();
    },

    renderTimeline() {
      this.timelineEl.innerHTML = "";
      let month = "";
      this.manifest.daily.forEach((item) => {
        const itemMonth = item.date.slice(0, 7);
        if (itemMonth !== month) {
          month = itemMonth;
          const monthEl = document.createElement("div");
          monthEl.className = "timeline-month";
          monthEl.textContent = month;
          this.timelineEl.appendChild(monthEl);
        }
        const stage = this.app.getStage(item.stage);
        const button = document.createElement("button");
        const summary = item.summary || "无摘要";
        const published = this.formatTime(item.published_at);
        button.type = "button";
        button.className = "timeline-item";
        button.dataset.date = item.date;
        button.title = `${summary}\n发布于 ${published}`;
        button.style.setProperty("--stage-color", stage.color);
        button.innerHTML = `
          <span class="timeline-dot" aria-hidden="true"></span>
          <span>
            <span class="timeline-date">${item.date}</span>
            <span class="timeline-title">${escapeHtml(item.title)}${item.has_show ? '<span class="show-badge" title="当天有展示版">◆</span>' : ""}</span>
            <span class="timeline-summary">${escapeHtml(summary)}<br><span>发布于 ${escapeHtml(published)}</span></span>
          </span>
        `;
        button.addEventListener("click", () => {
          window.location.hash = `#/daily/${item.date}`;
        });
        this.timelineEl.appendChild(button);
      });
    },

    bind() {
      document.getElementById("daily-prev").addEventListener("click", () => this.goRelative(1));
      document.getElementById("daily-next").addEventListener("click", () => this.goRelative(-1));
      document.getElementById("daily-doc-tab").addEventListener("click", () => this.switchMode("doc", true));
      document.getElementById("daily-show-tab").addEventListener("click", () => this.switchMode("show", true));
      const fullscreen = document.getElementById("daily-show-fullscreen");
      fullscreen.addEventListener("click", () => this.toggleShowFullscreen());
      document.addEventListener("fullscreenchange", () => {
        const isFullscreen = document.fullscreenElement === this.showEl;
        fullscreen.classList.toggle("is-active", isFullscreen);
        fullscreen.setAttribute("aria-label", isFullscreen ? "缩小展示栏" : "放大展示栏");
        fullscreen.title = isFullscreen ? "退出全屏展示" : "放大/缩小展示栏";
      });
      document.addEventListener("keydown", (event) => {
        if (!document.getElementById("view-daily").classList.contains("is-active")) return;
        if (this.currentMode !== "show") return;
        const item = this.manifest.daily[this.currentIndex];
        if (!item || item.show_type !== "md") return;
        if (event.key === "ArrowRight") {
          event.preventDefault();
          this.goScene(1);
        }
        if (event.key === "ArrowLeft") {
          event.preventDefault();
          this.goScene(-1);
        }
      });
    },

    async show(date, subview) {
      if (!this.manifest.daily.length) {
        this.contentEl.innerHTML = "<p>暂无日报。</p>";
        return;
      }
      const index = this.manifest.daily.findIndex((item) => item.date === date);
      this.currentIndex = index >= 0 ? index : 0;
      const item = this.manifest.daily[this.currentIndex];
      this.contentEl.innerHTML = await this.app.loadFragment(item.path, `daily-${item.date}`);
      this.showEl.innerHTML = "";
      this.currentScene = 0;
      this.renderMeta(item);
      this.renderToc();
      this.updateTimeline(item.date);
      this.updateNav();
      const requestedMode = subview === "show" ? "show" : "doc";
      if (requestedMode === "show" && !item.has_show) {
        this.notice("当天未撰写展示版,已回到文档。");
        this.switchMode("doc", false);
      } else {
        await this.switchMode(requestedMode, false);
      }
      const suffix = this.currentMode === "show" ? "/show" : "";
      if (date !== item.date || subview !== (this.currentMode === "show" ? "show" : undefined)) {
        window.history.replaceState(null, "", `#/daily/${item.date}${suffix}`);
      }
    },

    renderMeta(item) {
      const stage = this.app.getStage(item.stage);
      const meta = document.getElementById("daily-meta");
      meta.style.setProperty("--stage-color", stage.color);
      meta.innerHTML = `
        <span class="meta-chip">${item.date}</span>
        <span class="meta-chip stage">${escapeHtml(stage.label)}</span>
        <span class="meta-chip">${escapeHtml(item.summary || "无摘要")}</span>
        <span class="meta-time">${escapeHtml(this.timeMeta(item))}</span>
        ${this.renderDownloads(item)}
      `;
    },

    renderDownloads(item) {
      const links = [
        item.download_md_path ? {
          href: item.download_md_path,
          filename: `${item.date}.md`,
          label: ".md",
          title: "Download Markdown",
        } : null,
        item.download_html_path ? {
          href: item.download_html_path,
          filename: `${item.date}.html`,
          label: ".html",
          title: "Download HTML",
        } : null,
      ].filter(Boolean);
      if (!links.length) return "";
      return `
        <span class="daily-downloads" aria-label="&#19979;&#36733;&#24403;&#21069;&#26085;&#25253;">
          <span class="daily-download-label">&#19979;&#36733;</span>
          ${links.map((link) => `
            <a class="daily-download-link" href="${escapeHtml(link.href)}" download="${escapeHtml(link.filename)}" title="${escapeHtml(link.title)}">
              <span aria-hidden="true">↓</span><span>${escapeHtml(link.label)}</span>
            </a>
          `).join("")}
        </span>
      `;
    },

    timeMeta(item) {
      const published = this.formatTime(item.published_at);
      const updated = this.formatTime(item.updated_at);
      if (!updated || updated.slice(0, 16) === published.slice(0, 16)) {
        return `发布于 ${published}`;
      }
      return `发布于 ${published} · 最后更新 ${updated}`;
    },

    formatTime(value) {
      if (!value) return "";
      const date = new Date(value);
      if (Number.isNaN(date.getTime())) return value.replace("T", " ").slice(0, 19);
      const parts = new Intl.DateTimeFormat("zh-CN", {
        timeZone: "Asia/Shanghai",
        year: "numeric",
        month: "2-digit",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
        hour12: false,
      }).formatToParts(date);
      const map = Object.fromEntries(parts.map((part) => [part.type, part.value]));
      return `${map.year}-${map.month}-${map.day} ${map.hour}:${map.minute}:${map.second}`;
    },

    renderToc() {
      const headings = [...this.contentEl.querySelectorAll("h2, h3, h4")];
      if (!headings.length) {
        this.tocEl.innerHTML = "<span class=\"meta-chip\">无目录</span>";
        return;
      }
      this.tocEl.innerHTML = "";
      headings.forEach((heading, index) => {
        if (!heading.id) heading.id = `section-${index + 1}`;
        const level = heading.tagName.replace("H", "");
        const link = document.createElement("a");
        link.setAttribute("href", `#${heading.id}`);
        link.dataset.level = level;
        link.textContent = heading.textContent;
        link.addEventListener("click", (event) => {
          event.preventDefault();
          heading.scrollIntoView({behavior: "smooth", block: "start"});
        });
        this.tocEl.appendChild(link);
      });
      this.observeHeadings(headings);
    },

    observeHeadings(headings) {
      if (this.headingObserver) this.headingObserver.disconnect();
      this.headingObserver = new IntersectionObserver((entries) => {
        const visible = entries
          .filter((entry) => entry.isIntersecting)
          .sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top)[0];
        if (!visible) return;
        this.tocEl.querySelectorAll("a").forEach((link) => {
          link.classList.toggle("is-active", link.getAttribute("href") === `#${visible.target.id}`);
        });
      }, {rootMargin: "-20% 0px -65% 0px", threshold: [0, 1]});
      headings.forEach((heading) => this.headingObserver.observe(heading));
    },

    updateTimeline(date) {
      this.timelineEl.querySelectorAll(".timeline-item").forEach((node) => {
        node.classList.toggle("is-active", node.dataset.date === date);
      });
    },

    updateNav() {
      const prev = document.getElementById("daily-prev");
      const next = document.getElementById("daily-next");
      prev.disabled = this.currentIndex >= this.manifest.daily.length - 1;
      next.disabled = this.currentIndex <= 0;
    },

    async switchMode(mode, updateHash) {
      const item = this.manifest.daily[this.currentIndex];
      if (!item) return;
      if (mode === "show" && !item.has_show) {
        this.notice("当天未撰写展示版");
        return;
      }
      this.currentMode = mode;
      const docTab = document.getElementById("daily-doc-tab");
      const showTab = document.getElementById("daily-show-tab");
      docTab.classList.toggle("is-active", mode === "doc");
      docTab.setAttribute("aria-selected", String(mode === "doc"));
      showTab.classList.toggle("is-active", mode === "show");
      showTab.setAttribute("aria-selected", String(mode === "show"));
      showTab.disabled = !item.has_show;
      showTab.title = item.has_show ? "查看当天展示版" : "当天未撰写展示版";
      document.getElementById("daily-show-fullscreen").disabled = !item.has_show || mode !== "show";
      this.contentEl.hidden = mode !== "doc";
      this.showEl.hidden = mode !== "show";
      this.tocEl.hidden = mode !== "doc";
      this.mainlineEl.classList.toggle("is-show-mode", mode === "show");
      if (mode === "show") {
        await this.renderShow(item);
      }
      if (updateHash) {
        window.location.hash = `#/daily/${item.date}${mode === "show" ? "/show" : ""}`;
      }
    },

    async renderShow(item) {
      if (item.show_type === "html") {
        const inline = document.getElementById(`daily-show-html-${item.date}`);
        const html = inline
          ? JSON.parse(inline.textContent)
          : await this.app.loadFragment(item.show_path, `daily-show-${item.date}`);
        this.showEl.innerHTML = `<iframe class="daily-show-frame" sandbox="allow-scripts" title="${escapeHtml(item.title)} 展示版"></iframe>`;
        this.showEl.querySelector("iframe").srcdoc = html;
        return;
      }
      const html = await this.app.loadFragment(item.show_path, `daily-show-${item.date}`);
      this.showEl.innerHTML = `
        <div class="daily-show-player">
          <div class="daily-show-scenes">${html}</div>
          <div class="daily-show-controls">
            <button id="daily-show-prev" class="icon-button" type="button" aria-label="上一幕">←</button>
            <div id="daily-show-dots" class="daily-show-dots" aria-label="幕导航"></div>
            <button id="daily-show-next" class="icon-button" type="button" aria-label="下一幕">→</button>
          </div>
        </div>
      `;
      const scenes = [...this.showEl.querySelectorAll(".daily-show-scene")];
      const dots = this.showEl.querySelector("#daily-show-dots");
      dots.innerHTML = scenes.map((_, index) => (
        `<button class="scene-dot" type="button" aria-label="第 ${index + 1} 幕" data-scene="${index}"></button>`
      )).join("");
      dots.querySelectorAll(".scene-dot").forEach((dot) => {
        dot.addEventListener("click", () => this.setScene(Number(dot.dataset.scene)));
      });
      this.showEl.querySelector("#daily-show-prev").addEventListener("click", () => this.goScene(-1));
      this.showEl.querySelector("#daily-show-next").addEventListener("click", () => this.goScene(1));
      this.setScene(this.currentScene);
    },

    setScene(index) {
      const scenes = [...this.showEl.querySelectorAll(".daily-show-scene")];
      if (!scenes.length) return;
      this.currentScene = Math.max(0, Math.min(scenes.length - 1, index));
      scenes.forEach((scene, sceneIndex) => {
        scene.classList.toggle("is-active", sceneIndex === this.currentScene);
      });
      this.showEl.querySelectorAll(".scene-dot").forEach((dot) => {
        dot.classList.toggle("is-active", Number(dot.dataset.scene) === this.currentScene);
      });
      const prev = this.showEl.querySelector("#daily-show-prev");
      const next = this.showEl.querySelector("#daily-show-next");
      if (prev) prev.disabled = this.currentScene === 0;
      if (next) next.disabled = this.currentScene === scenes.length - 1;
    },

    goScene(delta) {
      this.setScene(this.currentScene + delta);
    },

    notice(text) {
      const notice = document.getElementById("daily-notice");
      notice.textContent = text;
      notice.hidden = false;
      clearTimeout(this.noticeTimer);
      this.noticeTimer = setTimeout(() => {
        notice.hidden = true;
      }, 2200);
    },

    goRelative(delta) {
      const target = this.manifest.daily[this.currentIndex + delta];
      if (target) window.location.hash = `#/daily/${target.date}`;
    },

    async toggleShowFullscreen() {
      if (this.currentMode !== "show") {
        this.notice("请先切到展示栏。");
        return;
      }
      if (!document.fullscreenElement) {
        await this.showEl.requestFullscreen();
        return;
      }
      await document.exitFullscreen();
    },
  };

  window.DailyView = DailyView;
})();
