(function () {
  const LONG_PRESS_MS = 600;

  function injectStyles(doc) {
    if (doc.getElementById("content-enhance-styles")) return;
    const style = doc.createElement("style");
    style.id = "content-enhance-styles";
    style.textContent = `
      .enhanced-table-scroll {
        max-width: 100%;
        overflow-x: auto;
        overflow-y: hidden;
        margin: 18px 0;
        border: 1px solid var(--line, #344255);
        border-radius: var(--radius, 8px);
        background: rgb(11 17 32 / 0.18);
      }
      .enhanced-table-scroll table {
        width: max-content;
        min-width: 100%;
        margin: 0;
        border: 0;
      }
      .enhanced-table-scroll th:first-child,
      .enhanced-table-scroll td:first-child {
        border-left: 0;
      }
      .enhanced-table-scroll th:last-child,
      .enhanced-table-scroll td:last-child {
        border-right: 0;
      }
      .enhanced-table-scroll tr:first-child > th,
      .enhanced-table-scroll tr:first-child > td {
        border-top: 0;
      }
      .enhanced-table-scroll tr:last-child > th,
      .enhanced-table-scroll tr:last-child > td {
        border-bottom: 0;
      }
      .markdown-body img,
      .section-body img,
      .daily-content img,
      .daily-show-content img,
      .content-enhanced-image {
        display: block;
        max-width: 100%;
        max-height: min(68vh, 560px);
        width: auto;
        height: auto;
        object-fit: contain;
        margin: 16px auto;
        cursor: zoom-in;
      }
      .mermaid {
        max-width: 100%;
        margin: 20px 0;
        padding: 18px;
        overflow-x: auto;
        border: 1px solid var(--line, #344255);
        border-radius: var(--radius, 8px);
        background: rgb(10 15 28 / 0.48);
        text-align: center;
      }
      .mermaid svg {
        display: block;
        max-width: none;
        height: auto;
        margin: 0 auto;
      }
      .mermaid.mermaid-error {
        color: #fca5a5;
        font-family: ui-monospace, "Cascadia Code", Consolas, monospace;
        font-size: 0.88rem;
        line-height: 1.6;
        text-align: left;
        white-space: pre-wrap;
      }
      .mermaid.mermaid-error::before {
        display: block;
        margin-bottom: 8px;
        font-family: "Microsoft YaHei", sans-serif;
        font-weight: 700;
        content: "Mermaid 图表语法错误，已保留源码";
      }
      .image-longpress-overlay {
        position: fixed;
        inset: 0;
        z-index: 2147483647;
        display: grid;
        place-items: center;
        padding: 24px;
        border: 0;
        background: rgb(3 7 18 / 0.92);
        cursor: zoom-out;
      }
      .image-longpress-overlay img {
        display: block;
        max-width: 96vw;
        max-height: 94vh;
        width: auto;
        height: auto;
        object-fit: contain;
        margin: 0;
        border-radius: 6px;
        box-shadow: 0 24px 80px rgb(0 0 0 / 0.55);
      }
    `;
    doc.head.appendChild(style);
  }

  function typesetMath(root) {
    const win = root.ownerDocument?.defaultView || window;
    const mathJax = win.MathJax;
    if (!mathJax) return Promise.resolve();
    const target = root.nodeType === Node.DOCUMENT_NODE ? root.body : root;
    const run = () => {
      if (typeof mathJax.typesetPromise === "function") {
        return mathJax.typesetPromise([target]).catch(() => {});
      }
      if (typeof mathJax.typeset === "function") {
        mathJax.typeset([target]);
      }
      return Promise.resolve();
    };
    return mathJax.startup?.promise ? mathJax.startup.promise.then(run) : run();
  }

  async function typesetMermaid(root) {
    const win = root.ownerDocument?.defaultView || window;
    const mermaid = win.mermaid;
    if (!mermaid) return;
    const target = root.nodeType === 9 ? root.documentElement : root;
    const selector = ".mermaid:not([data-processed='true']):not([data-mermaid-error='true'])";
    const nodes = Array.from(target.querySelectorAll(selector));
    if (target.matches?.(selector)) nodes.unshift(target);
    if (!nodes.length) return;

    if (!win.__dashboardMermaidInitialized) {
      mermaid.initialize({
        startOnLoad: false,
        securityLevel: "strict",
        theme: "dark",
        flowchart: {htmlLabels: true, useMaxWidth: false},
      });
      win.__dashboardMermaidInitialized = true;
    }

    for (const node of nodes) {
      const source = node.textContent;
      try {
        await mermaid.run({nodes: [node]});
      } catch (error) {
        node.removeAttribute("data-processed");
        node.dataset.mermaidError = "true";
        node.classList.add("mermaid-error");
        node.textContent = source;
        console.warn("Mermaid render failed", error);
      }
    }
  }

  function wrapTables(root) {
    root.querySelectorAll("table").forEach((table) => {
      if (table.closest(".enhanced-table-scroll")) return;
      const wrapper = table.ownerDocument.createElement("div");
      wrapper.className = "enhanced-table-scroll";
      table.parentNode.insertBefore(wrapper, table);
      wrapper.appendChild(table);
    });
  }

  function openImageOverlay(img) {
    const doc = img.ownerDocument;
    doc.querySelector(".image-longpress-overlay")?.remove();
    const overlay = doc.createElement("button");
    overlay.type = "button";
    overlay.className = "image-longpress-overlay";
    overlay.setAttribute("aria-label", "Close image preview");
    const clone = doc.createElement("img");
    clone.src = img.currentSrc || img.src;
    clone.alt = img.alt || "";
    overlay.appendChild(clone);
    overlay.addEventListener("click", () => overlay.remove());
    doc.addEventListener("keydown", function closeOnEscape(event) {
      if (event.key === "Escape") {
        overlay.remove();
        doc.removeEventListener("keydown", closeOnEscape);
      }
    });
    doc.body.appendChild(overlay);
  }

  function prepareImages(root) {
    root.querySelectorAll("img").forEach((img) => {
      if (img.dataset.longpressReady === "true") return;
      img.dataset.longpressReady = "true";
      img.classList.add("content-enhanced-image");
      let timer = null;
      let opened = false;

      const cancel = () => {
        if (timer) {
          clearTimeout(timer);
          timer = null;
        }
      };

      img.addEventListener("pointerdown", (event) => {
        if (event.pointerType === "mouse" && event.button !== 0) return;
        opened = false;
        cancel();
        timer = setTimeout(() => {
          opened = true;
          openImageOverlay(img);
        }, LONG_PRESS_MS);
      });
      ["pointerup", "pointercancel", "pointerleave", "dragstart"].forEach((name) => {
        img.addEventListener(name, cancel);
      });
      img.addEventListener("click", (event) => {
        if (!opened) return;
        event.preventDefault();
        event.stopPropagation();
      });
      img.addEventListener("contextmenu", (event) => event.preventDefault());
    });
  }

  function enhance(root) {
    const doc = root.ownerDocument || root;
    if (!doc?.head || !doc?.body) return Promise.resolve();
    injectStyles(doc);
    wrapTables(root);
    prepareImages(root);
    return Promise.all([typesetMath(root), typesetMermaid(root)]).then(() => undefined);
  }

  window.ContentEnhancer = {enhance};
  document.addEventListener("DOMContentLoaded", () => enhance(document));
})();
