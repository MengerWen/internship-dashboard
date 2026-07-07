(function () {
  const SearchView = {
    initialized: false,

    init() {
      const dialog = document.getElementById("search-dialog");
      const open = document.getElementById("search-open");
      const close = document.getElementById("search-close");
      if (document.body.dataset.offline === "true") return;
      open.addEventListener("click", async () => {
        dialog.showModal();
        if (!this.initialized) await this.mount();
      });
      close.addEventListener("click", () => dialog.close());
      dialog.addEventListener("click", (event) => {
        if (event.target === dialog) dialog.close();
      });
    },

    async mount() {
      const root = document.getElementById("search-root");
      root.innerHTML = "<p class=\"meta-chip\">正在加载搜索索引...</p>";
      try {
        await this.loadCss("pagefind/pagefind-ui.css");
        await this.loadScript("pagefind/pagefind-ui.js");
        root.innerHTML = "";
        /* global PagefindUI */
        new PagefindUI({
          element: "#search-root",
          showSubResults: true,
          translations: {
            placeholder: "搜索撤单、快照、因子...",
            zero_results: "没有找到匹配内容",
          },
        });
        this.initialized = true;
      } catch (error) {
        root.innerHTML = `<p class="meta-chip">搜索索引不可用。请确认已执行 Pagefind 构建。</p>`;
      }
    },

    loadScript(src) {
      return new Promise((resolve, reject) => {
        const script = document.createElement("script");
        script.src = src;
        script.onload = resolve;
        script.onerror = reject;
        document.head.appendChild(script);
      });
    },

    loadCss(href) {
      return new Promise((resolve, reject) => {
        const link = document.createElement("link");
        link.rel = "stylesheet";
        link.href = href;
        link.onload = resolve;
        link.onerror = reject;
        document.head.appendChild(link);
      });
    },
  };

  window.SearchView = SearchView;
})();
