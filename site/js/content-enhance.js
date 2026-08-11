(function () {
  const LONG_PRESS_MS = 600;
  const HEADING_SELECTOR = "h1, h2, h3, h4, h5, h6";

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
        background: var(--surface, #f8f4eb);
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
        background: var(--surface, #f8f4eb);
        text-align: center;
      }
      .mermaid svg {
        display: block;
        max-width: none;
        height: auto;
        margin: 0 auto;
      }
      .mermaid.mermaid-error {
        color: var(--danger, #ad4339);
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
      .collapsible-section {
        min-width: 0;
      }
      .collapsible-heading-row {
        display: grid;
        grid-template-columns: 26px minmax(0, 1fr);
        gap: 7px;
        align-items: center;
      }
      .collapsible-section[data-heading-level="1"] > .collapsible-heading-row {
        margin: 0 0 18px;
      }
      .collapsible-section[data-heading-level="2"] > .collapsible-heading-row {
        margin-top: 32px;
      }
      .collapsible-section[data-heading-level="3"] > .collapsible-heading-row {
        margin-top: 24px;
      }
      .collapsible-section[data-heading-level="4"] > .collapsible-heading-row,
      .collapsible-section[data-heading-level="5"] > .collapsible-heading-row,
      .collapsible-section[data-heading-level="6"] > .collapsible-heading-row {
        margin-top: 20px;
      }
      .collapsible-heading-row > :is(h1, h2, h3, h4, h5, h6) {
        min-width: 0;
        margin: 0;
      }
      .heading-collapse-toggle,
      .toc-collapse-toggle {
        position: relative;
        display: inline-grid;
        place-items: center;
        flex: 0 0 auto;
        width: 26px;
        height: 26px;
        padding: 0;
        border: 1px solid transparent;
        border-radius: 6px;
        background: transparent;
        color: var(--muted, #8a95a5);
        cursor: pointer;
      }
      .heading-collapse-toggle::before,
      .toc-collapse-toggle::before {
        width: 0;
        height: 0;
        border-right: 5px solid transparent;
        border-left: 5px solid transparent;
        border-top: 7px solid currentColor;
        content: "";
        transform: rotate(0deg);
        transition: transform 150ms ease;
      }
      .heading-collapse-toggle[aria-expanded="false"]::before,
      .toc-collapse-toggle[aria-expanded="false"]::before {
        transform: rotate(-90deg);
      }
      .heading-collapse-toggle:hover,
      .heading-collapse-toggle:focus-visible,
      .toc-collapse-toggle:hover,
      .toc-collapse-toggle:focus-visible {
        border-color: var(--focus, #fff6d6);
        color: var(--focus, #fff6d6);
        outline: 0;
      }
      .collapsible-section-body[hidden] {
        display: none !important;
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
      @media (prefers-reduced-motion: reduce) {
        .heading-collapse-toggle::before,
        .toc-collapse-toggle::before {
          transition: none;
        }
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

  function directChildByClass(parent, className) {
    return Array.from(parent?.children || []).find((child) => child.classList.contains(className));
  }

  function headingForSection(section) {
    const row = directChildByClass(section, "collapsible-heading-row");
    return Array.from(row?.children || []).find((child) => child.matches?.(HEADING_SELECTOR)) || null;
  }

  function sectionForHeading(heading) {
    const row = heading?.parentElement;
    const section = row?.parentElement;
    return row?.classList.contains("collapsible-heading-row")
      && section?.classList.contains("collapsible-section")
      ? section
      : null;
  }

  function setSectionExpanded(section, expanded) {
    if (!section?.classList.contains("collapsible-section")) return;
    const row = directChildByClass(section, "collapsible-heading-row");
    const body = directChildByClass(section, "collapsible-section-body");
    const toggle = directChildByClass(row, "heading-collapse-toggle");
    const heading = headingForSection(section);
    if (!body || !toggle || !heading) return;

    const nextExpanded = Boolean(expanded);
    const previousExpanded = toggle.getAttribute("aria-expanded") !== "false";
    const headingText = heading.textContent.trim() || "当前标题";
    section.classList.toggle("is-collapsed", !nextExpanded);
    body.hidden = !nextExpanded;
    toggle.setAttribute("aria-expanded", String(nextExpanded));
    toggle.setAttribute("aria-label", `${nextExpanded ? "收起" : "展开"}“${headingText}”内容`);
    toggle.title = nextExpanded ? "收起本节" : "展开本节";

    if (previousExpanded !== nextExpanded) {
      const EventType = section.ownerDocument.defaultView?.CustomEvent || CustomEvent;
      section.dispatchEvent(new EventType("content-section-toggle", {
        bubbles: true,
        detail: {section, expanded: nextExpanded},
      }));
    }
  }

  function expandSectionAncestors(section) {
    let ancestor = section?.parentElement?.closest?.(".collapsible-section") || null;
    while (ancestor) {
      setSectionExpanded(ancestor, true);
      ancestor = ancestor.parentElement?.closest?.(".collapsible-section") || null;
    }
  }

  function nextCollapseBodyId(doc) {
    doc.__contentCollapseId = (doc.__contentCollapseId || 0) + 1;
    return `collapsible-section-body-${doc.__contentCollapseId}`;
  }

  function prepareCollapsibleContainer(container) {
    const hasPreparedSections = Array.from(container.children).some((child) => (
      child.classList.contains("collapsible-section")
    ));
    if (container.dataset.collapsibleReady === "true" && hasPreparedSections) return;
    delete container.dataset.collapsibleReady;
    const children = Array.from(container.children);
    if (!children.some((child) => child.matches?.(HEADING_SELECTOR))) return;

    const doc = container.ownerDocument;
    const fragment = doc.createDocumentFragment();
    const stack = [];

    children.forEach((child) => {
      if (!child.matches?.(HEADING_SELECTOR)) {
        const target = stack.length ? stack[stack.length - 1].body : fragment;
        target.appendChild(child);
        return;
      }

      const level = Number(child.tagName.slice(1));
      while (stack.length && stack[stack.length - 1].level >= level) stack.pop();

      const section = doc.createElement("section");
      section.className = "collapsible-section";
      section.dataset.headingLevel = String(level);

      const row = doc.createElement("div");
      row.className = "collapsible-heading-row";

      const body = doc.createElement("div");
      body.className = "collapsible-section-body";
      body.id = nextCollapseBodyId(doc);

      const toggle = doc.createElement("button");
      toggle.type = "button";
      toggle.className = "heading-collapse-toggle";
      toggle.setAttribute("aria-controls", body.id);
      toggle.setAttribute("aria-expanded", "true");
      toggle.addEventListener("click", () => {
        setSectionExpanded(section, toggle.getAttribute("aria-expanded") === "false");
      });

      row.append(toggle, child);
      section.append(row, body);
      const target = stack.length ? stack[stack.length - 1].body : fragment;
      target.appendChild(section);
      stack.push({level, body});
      setSectionExpanded(section, true);
    });

    container.appendChild(fragment);
    container.dataset.collapsibleReady = "true";
  }

  function prepareCollapsibleSections(root) {
    const containers = [];
    if (root.matches?.(".markdown-body")) containers.push(root);
    root.querySelectorAll?.(".markdown-body").forEach((container) => containers.push(container));
    containers.forEach(prepareCollapsibleContainer);
  }

  function enhance(root) {
    const doc = root.ownerDocument || root;
    if (!doc?.head || !doc?.body) return Promise.resolve();
    injectStyles(doc);
    prepareCollapsibleSections(root);
    wrapTables(root);
    prepareImages(root);
    return Promise.all([typesetMath(root), typesetMermaid(root)]).then(() => undefined);
  }

  window.ContentEnhancer = {
    enhance,
    expandSectionAncestors,
    headingForSection,
    prepareCollapsibleSections,
    sectionForHeading,
    setSectionExpanded,
  };
  document.addEventListener("DOMContentLoaded", () => enhance(document));
})();
