(function () {
  const ShowcaseView = {
    manifest: null,
    app: null,
    sectionsEl: null,
    stepperEl: null,
    activeIndex: 0,
    observer: null,

    async init(manifest, app) {
      this.manifest = manifest;
      this.app = app;
      this.sectionsEl = document.getElementById("showcase-sections");
      this.stepperEl = document.getElementById("showcase-stepper");
      this.renderShell();
      await this.loadSections();
      this.bind();
      this.observe();
    },

    renderShell() {
      this.stepperEl.innerHTML = "";
      this.sectionsEl.innerHTML = "";
      this.manifest.showcase.forEach((item, index) => {
        const stage = this.app.getStage(item.id);
        const button = document.createElement("button");
        button.type = "button";
        button.className = "stage-node";
        button.dataset.stage = item.id;
        button.dataset.status = item.status;
        button.style.setProperty("--stage-color", stage.color);
        button.innerHTML = `
          <span class="stage-dot" aria-hidden="true"></span>
          <span>
            <span class="stage-label">${item.label}</span>
            <span class="stage-status">${this.statusText(item.status)}</span>
          </span>
        `;
        button.addEventListener("click", () => this.goTo(index, true));
        this.stepperEl.appendChild(button);

        const section = document.createElement("section");
        section.className = "showcase-section";
        section.dataset.stage = item.id;
        section.dataset.index = String(index);
        section.style.setProperty("--stage-color", stage.color);
        section.innerHTML = `
          <header class="section-kicker">
            <div class="section-index">${String(index + 1).padStart(2, "0")} / ${this.manifest.showcase.length}</div>
            <h2 class="section-title">${item.title}</h2>
            <span class="status-pill">${this.statusText(item.status)}</span>
            <div class="details-tools">
              <button class="small-button expand-all" type="button">全部展开</button>
              <button class="small-button collapse-all" type="button">全部收起</button>
            </div>
          </header>
          <div class="section-body markdown-body" tabindex="0" aria-label="${item.title}"></div>
        `;
        this.sectionsEl.appendChild(section);
      });
    },

    async loadSections() {
      await Promise.all(
        this.manifest.showcase.map(async (item) => {
          const body = this.sectionsEl.querySelector(`[data-stage="${item.id}"] .section-body`);
          body.innerHTML = await this.app.loadFragment(item.path, `showcase-${item.id}`);
        }),
      );
    },

    bind() {
      document.getElementById("showcase-prev").addEventListener("click", () => this.goRelative(-1, true));
      document.getElementById("showcase-next").addEventListener("click", () => this.goRelative(1, true));
      this.sectionsEl.addEventListener("click", (event) => {
        const target = event.target;
        if (!(target instanceof HTMLElement)) return;
        const section = target.closest(".showcase-section");
        if (!section) return;
        if (target.classList.contains("expand-all")) {
          section.querySelectorAll("details").forEach((node) => node.open = true);
        }
        if (target.classList.contains("collapse-all")) {
          section.querySelectorAll("details").forEach((node) => node.open = false);
        }
      });
      document.addEventListener("keydown", (event) => {
        if (!document.getElementById("view-showcase").classList.contains("is-active")) return;
        if (["ArrowDown", "PageDown"].includes(event.key)) {
          event.preventDefault();
          this.keyboardMove(1);
        }
        if (["ArrowUp", "PageUp"].includes(event.key)) {
          event.preventDefault();
          this.keyboardMove(-1);
        }
      });
    },

    observe() {
      this.observer = new IntersectionObserver((entries) => {
        const visible = entries
          .filter((entry) => entry.isIntersecting)
          .sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
        if (!visible) return;
        this.setActive(Number(visible.target.dataset.index));
      }, {root: this.sectionsEl, threshold: [0.55, 0.75]});
      this.sectionsEl.querySelectorAll(".showcase-section").forEach((section) => this.observer.observe(section));
    },

    show(stageId) {
      const index = this.manifest.showcase.findIndex((item) => item.id === stageId);
      this.goTo(index >= 0 ? index : 0, false);
    },

    goRelative(delta, updateHash) {
      this.goTo(this.activeIndex + delta, updateHash);
    },

    goTo(index, updateHash) {
      const clamped = Math.max(0, Math.min(this.manifest.showcase.length - 1, index));
      const item = this.manifest.showcase[clamped];
      const section = this.sectionsEl.querySelector(`[data-stage="${item.id}"]`);
      section.scrollIntoView({behavior: this.prefersReducedMotion() ? "auto" : "smooth", block: "start"});
      this.setActive(clamped);
      if (updateHash) window.history.pushState(null, "", `#/showcase/${item.id}`);
    },

    keyboardMove(delta) {
      const section = this.sectionsEl.querySelectorAll(".showcase-section")[this.activeIndex];
      const body = section.querySelector(".section-body");
      const atTop = body.scrollTop <= 1;
      const atBottom = body.scrollTop + body.clientHeight >= body.scrollHeight - 1;
      if (delta > 0 && !atBottom) {
        body.scrollBy({top: body.clientHeight * 0.82, behavior: "smooth"});
        return;
      }
      if (delta < 0 && !atTop) {
        body.scrollBy({top: -body.clientHeight * 0.82, behavior: "smooth"});
        return;
      }
      this.goRelative(delta, true);
    },

    setActive(index) {
      this.activeIndex = Math.max(0, Math.min(this.manifest.showcase.length - 1, index));
      const active = this.manifest.showcase[this.activeIndex];
      this.stepperEl.querySelectorAll(".stage-node").forEach((node) => {
        node.classList.toggle("is-active", node.dataset.stage === active.id);
      });
      document.getElementById("showcase-prev").disabled = this.activeIndex === 0;
      document.getElementById("showcase-next").disabled = this.activeIndex === this.manifest.showcase.length - 1;
      if (document.getElementById("view-showcase").classList.contains("is-active")) {
        window.history.replaceState(null, "", `#/showcase/${active.id}`);
      }
    },

    statusText(status) {
      return {done: "已完成", active: "进行中", planned: "规划中"}[status] || status;
    },

    prefersReducedMotion() {
      return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    },
  };

  window.ShowcaseView = ShowcaseView;
})();
