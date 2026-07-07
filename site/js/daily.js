(function () {
  const DailyView = {
    manifest: null,
    app: null,
    currentIndex: 0,
    timelineEl: null,
    contentEl: null,
    tocEl: null,

    async init(manifest, app) {
      this.manifest = manifest;
      this.app = app;
      this.timelineEl = document.getElementById("daily-timeline");
      this.contentEl = document.getElementById("daily-content");
      this.tocEl = document.getElementById("daily-toc");
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
        button.type = "button";
        button.className = "timeline-item";
        button.dataset.date = item.date;
        button.style.setProperty("--stage-color", stage.color);
        button.innerHTML = `
          <span class="timeline-dot" aria-hidden="true"></span>
          <span>
            <span class="timeline-date">${item.date}</span>
            <span class="timeline-title">${item.title}</span>
            <span class="timeline-summary">${item.summary || "无摘要"}</span>
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
    },

    async show(date) {
      if (!this.manifest.daily.length) {
        this.contentEl.innerHTML = "<p>暂无日报。</p>";
        return;
      }
      const index = this.manifest.daily.findIndex((item) => item.date === date);
      this.currentIndex = index >= 0 ? index : 0;
      const item = this.manifest.daily[this.currentIndex];
      this.contentEl.innerHTML = await this.app.loadFragment(item.path, `daily-${item.date}`);
      this.renderMeta(item);
      this.renderToc();
      this.updateTimeline(item.date);
      this.updateNav();
      if (date !== item.date) window.history.replaceState(null, "", `#/daily/${item.date}`);
    },

    renderMeta(item) {
      const stage = this.app.getStage(item.stage);
      const meta = document.getElementById("daily-meta");
      meta.style.setProperty("--stage-color", stage.color);
      meta.innerHTML = `
        <span class="meta-chip">${item.date}</span>
        <span class="meta-chip stage">${stage.label}</span>
        <span class="meta-chip">${item.summary || "无摘要"}</span>
      `;
    },

    renderToc() {
      const headings = [...this.contentEl.querySelectorAll("h2, h3, h4")];
      if (!headings.length) {
        this.tocEl.innerHTML = "<span class=\"meta-chip\">无目录</span>";
        return;
      }
      this.tocEl.innerHTML = headings.map((heading, index) => {
        if (!heading.id) heading.id = `section-${index + 1}`;
        const level = heading.tagName.replace("H", "");
        return `<a href="#${heading.id}" data-level="${level}">${heading.textContent}</a>`;
      }).join("");
      this.tocEl.querySelectorAll("a").forEach((link) => {
        link.addEventListener("click", (event) => {
          event.preventDefault();
          const target = this.contentEl.querySelector(link.getAttribute("href"));
          target.scrollIntoView({behavior: "smooth", block: "start"});
        });
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

    goRelative(delta) {
      const target = this.manifest.daily[this.currentIndex + delta];
      if (target) window.location.hash = `#/daily/${target.date}`;
    },
  };

  window.DailyView = DailyView;
})();
