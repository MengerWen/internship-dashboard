(function (root) {
  "use strict";
  const clone = (value) => JSON.parse(JSON.stringify(value));
  const key = (item) => item.id || item.date;
  const safeId = (id) => typeof id === "string" && /^[a-zA-Z0-9_-]{1,64}$/.test(id) && !["__proto__", "constructor", "prototype", "_untagged"].includes(id);
  function validate(input) {
    if (!input || input.schemaVersion !== 1 || !Array.isArray(input.tags) || input.tags.length > 200 ||
        !input.assignments || Array.isArray(input.assignments) || typeof input.assignments !== "object") throw new Error("标签文件格式不正确");
    const ids = new Set(), names = new Set();
    const tags = input.tags.map((tag) => {
      if (!tag || !safeId(tag.id) || ids.has(tag.id)) throw new Error("标签 ID 无效或重复");
      const name = typeof tag.name === "string" ? tag.name.trim() : "";
      if (!name || name.length > 40 || names.has(name.toLocaleLowerCase()) || name === "未标记" || name === "汇报一览") throw new Error("标签名不能为空、重复或使用保留名称，最多 40 字");
      if (!/^#[0-9a-f]{6}$/i.test(tag.color)) throw new Error("标签颜色无效");
      if (!Array.isArray(tag.keywords) || tag.keywords.length > 30 || tag.keywords.some((w) => typeof w !== "string" || !w.trim() || w.length > 60)) throw new Error("每个标签最多 30 个关键词，每个最多 60 字");
      ids.add(tag.id); names.add(name.toLocaleLowerCase());
      return {id: tag.id, name, color: tag.color, keywords: [...new Set(tag.keywords.map((w) => w.trim()))]};
    });
    const entries = Object.entries(input.assignments);
    if (entries.length > 10000) throw new Error("汇报归属条目过多");
    const assignments = {};
    for (const [id, values] of entries) {
      if (!safeId(id) || !Array.isArray(values) || values.length > 200 || values.some((v) => !ids.has(v))) throw new Error("汇报归属包含无效 ID 或不存在的标签");
      if (values.length) assignments[id] = [...new Set(values)];
    }
    return {schemaVersion: 1, tags, assignments};
  }
  function filter(items, state, options = {}) {
    const selected = options.tags || [];
    const query = (options.query || "").trim().toLocaleLowerCase();
    return items.filter((item) => {
      const assigned = state.assignments[key(item)] || [];
      const match = (id) => id === "_untagged" ? !assigned.length : assigned.includes(id);
      const tagMatch = !selected.length || (options.mode === "all" ? selected.every(match) : selected.some(match));
      return tagMatch && (!query || `${item.date} ${item.title} ${item.summary || ""}`.toLocaleLowerCase().includes(query));
    });
  }
  function assign(state, reports, tags, action) {
    const next = clone(state);
    for (const id of reports) {
      const old = next.assignments[id] || [];
      const values = action === "remove" ? old.filter((t) => !tags.includes(t)) : [...new Set([...old, ...tags])];
      if (values.length) next.assignments[id] = values;
      else delete next.assignments[id];
    }
    return validate(next);
  }
  function remove(state, id, target) {
    if (target === id || (target && !state.tags.some((t) => t.id === target))) throw new Error("请选择另一个合并目标");
    const next = clone(state);
    if (!next.tags.some((t) => t.id === id)) throw new Error("标签不存在");
    if (target) {
      const from = next.tags.find((t) => t.id === id), to = next.tags.find((t) => t.id === target);
      to.keywords = [...new Set([...to.keywords, from.name, ...from.keywords])].slice(0, 30);
    }
    next.tags = next.tags.filter((t) => t.id !== id);
    for (const [report, tags] of Object.entries(next.assignments)) {
      next.assignments[report] = [...new Set(tags.flatMap((t) => t === id ? (target ? [target] : []) : [t]))];
    }
    return validate(next);
  }
  function suggest(item, state) {
    const text = `${item.title} ${item.summary || ""}`.toLocaleLowerCase();
    return state.tags.flatMap((tag) => {
      if ((state.assignments[key(item)] || []).includes(tag.id)) return [];
      const hits = [...new Set([tag.name, ...tag.keywords])].filter((w) => text.includes(w.toLocaleLowerCase()));
      return hits.length ? [{id: tag.id, hits}] : [];
    });
  }
  function mergeImport(state, incoming) {
    const next = clone(state), other = validate(incoming), mapping = new Map();
    for (const tag of other.tags) {
      const sameId = next.tags.find((t) => t.id === tag.id);
      const sameName = next.tags.find((t) => t.name.toLocaleLowerCase() === tag.name.toLocaleLowerCase());
      if (sameId && sameId.name !== tag.name && sameName && sameName.id !== tag.id) throw new Error("导入文件的标签 ID 与名称冲突，请先调整标签");
      const existing = sameId || sameName;
      if (existing) mapping.set(tag.id, existing.id);
      else { next.tags.push(tag); mapping.set(tag.id, tag.id); }
    }
    for (const [report, tags] of Object.entries(other.assignments)) {
      next.assignments[report] = [...new Set([...(next.assignments[report] || []), ...tags.map((id) => mapping.get(id))])];
    }
    return validate(next);
  }
  const api = {clone, key, safeId, validate, filter, assign, remove, suggest, mergeImport};
  root.ReportTagModel = api;
  if (typeof module !== "undefined" && module.exports) module.exports = api;
})(globalThis);
