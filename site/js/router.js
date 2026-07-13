(function () {
  const stageColors = [
    "var(--stage-0)",
    "var(--stage-1)",
    "var(--stage-2)",
    "var(--stage-3)",
    "var(--stage-4)",
    "var(--stage-5)",
  ];

  const App = {
    manifest: null,
    stageIndex: new Map(),
    ready: false,

    async init() {
      this.manifest = await this.loadManifest();
      this.manifest.stages.forEach((stage, index) => {
        stage.color = stageColors[index % stageColors.length];
        this.stageIndex.set(stage.id, {...stage, index});
      });
      document.title = this.manifest.site_title || document.title;
      const siteTitle = document.getElementById("site-title");
      if (siteTitle) siteTitle.textContent = this.manifest.site_title || siteTitle.textContent;

      await window.ShowcaseView.init(this.manifest, this);
      await window.DailyView.init(this.manifest, this);
      window.SearchView.init();
      window.addEventListener("hashchange", () => this.route());
      this.ready = true;
      this.route();
    },

    async loadManifest() {
      const inline = document.getElementById("inline-manifest");
      if (inline) return JSON.parse(inline.textContent);
      const response = await fetch("manifest.json", {cache: "no-store"});
      if (!response.ok) throw new Error("manifest.json 加载失败");
      return response.json();
    },

    async loadFragment(path, templateId) {
      const inline = document.getElementById(templateId);
      if (inline) return inline.innerHTML;
      const response = await fetch(path, {cache: "no-store"});
      if (!response.ok) throw new Error(`${path} 加载失败`);
      return response.text();
    },

    getStage(stageId) {
      return this.stageIndex.get(stageId) || {
        id: stageId,
        label: stageId || "未分类",
        color: "var(--muted)",
        index: -1,
      };
    },

    enhanceContent(root) {
      return window.ContentEnhancer?.enhance(root) || Promise.resolve();
    },

    prepareIsolatedHtml(html) {
      const cleaned = String(html).replace(/<script\b[^>]*\bsrc=["'][^"']*mathjax[^"']*["'][^>]*>\s*<\/script>/gi, "");
      const inject = `
        <script>
          window.MathJax = {
            tex: {
              inlineMath: [['$', '$'], ['\\\\(', '\\\\)']],
              displayMath: [['$$', '$$'], ['\\\\[', '\\\\]']],
              processEscapes: true
            },
            svg: {fontCache: 'global'},
            startup: {typeset: false}
          };
        <\/script>
        <script defer src="vendor/mathjax/tex-svg.js"><\/script>
        <script defer src="vendor/mermaid/mermaid.min.js"><\/script>
        <script defer src="js/content-enhance.js"><\/script>
        <script>
          document.addEventListener('DOMContentLoaded', () => {
            window.ContentEnhancer?.enhance(document);
          });
        <\/script>
      `;
      if (/<\/head>/i.test(cleaned)) {
        return cleaned.replace(/<\/head>/i, () => `${inject}</head>`);
      }
      return `${inject}${cleaned}`;
    },

    parseHash() {
      const clean = window.location.hash.replace(/^#\/?/, "");
      const [view, key, subview] = clean.split("/");
      if (view === "daily") return {view: "daily", key, subview};
      if (view === "showcase") return {view: "showcase", key};
      return {view: "showcase", key: null};
    },

    route() {
      if (!this.ready) return;
      if (!window.location.hash) {
        window.location.replace("#/showcase");
        return;
      }
      const {view, key, subview} = this.parseHash();
      document.querySelectorAll(".view").forEach((node) => node.classList.remove("is-active"));
      document.querySelectorAll(".tab").forEach((node) => node.classList.remove("is-active"));

      if (view === "daily") {
        document.getElementById("view-daily").classList.add("is-active");
        document.getElementById("tab-daily").classList.add("is-active");
        window.DailyView.show(key, subview);
      } else {
        document.getElementById("view-showcase").classList.add("is-active");
        document.getElementById("tab-showcase").classList.add("is-active");
        window.ShowcaseView.show(key);
      }
    },
  };

  window.DashboardApp = App;
  document.addEventListener("DOMContentLoaded", () => {
    App.init().catch((error) => {
      document.body.innerHTML = `<main class="markdown-body" style="padding:96px 24px"><h1>构建数据加载失败</h1><pre>${error.message}</pre></main>`;
    });
  });
})();
