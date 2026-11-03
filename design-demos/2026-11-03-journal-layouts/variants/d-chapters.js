/* D：按日期分章，保留章内并行研究与逐点记录。 */
(function () {
  "use strict";

  window.JournalVariants = window.JournalVariants || {};
  window.JournalVariants.D = function (root, api) {
    const esc = api.esc;
    const chapters = [
      {
        title: "快照与论文复现", from: "2026-06-23", to: "2026-07-05",
        question: "快照怎样重建，论文中的指标怎样复现？",
        description: "从逐笔数据、交易规则和论文出发，阅读这一时期的环境准备、快照重建与指标复现记录。"
      },
      {
        title: "从论文指标到正式因子", from: "2026-07-06", to: "2026-08-05",
        question: "论文指标进入正式因子计算，还需要补齐哪些口径？",
        description: "这一章集中阅读指标实现、正式计算、门限与历史回补，也保留同一时期的数据和交付工作。"
      },
      {
        title: "五分钟因子库与模型", from: "2026-08-06", to: "2026-09-21",
        question: "五分钟因子怎样积累，模型研究又在检验什么？",
        description: "把因子库、定标、模型与各专题放在同一段时间里阅读；各项研究的具体进展仍以本链记录为准。"
      },
      {
        title: "市场适配与参数复核", from: "2026-09-22", to: "2026-10-19",
        question: "不同市场的实现与参数，需要怎样逐项复核？",
        description: "在这一时期的记录中查看市场适配、分组定标、因子计算与基础正确性核对，沿登记的承接关系继续读。"
      },
      {
        title: "修正回放与新研究", from: "2026-10-20", to: api.data.asOf,
        question: "回放和基础口径如何修正，新的因子与模型研究又在推进什么？",
        description: "从修正回放读到因子补算、评价与新候选研究，先看近期工作，再展开这一章的完整记录。"
      }
    ];
    const chapterNames = ["第一章", "第二章", "第三章", "第四章", "第五章"];
    const state = { chapter: chapters.length - 1, track: "", allChains: false, allHandoffs: false, allDays: false };
    const allPoints = api.points({ reverse: false });

    function chapterPoints(chapter, track) {
      return api.points({ from: chapter.from, to: chapter.to, trackId: track || undefined });
    }

    function measure(points) {
      return { days: new Set(points.map(p => p.date)).size, chains: new Set(points.map(p => p.chain.id)).size, points: points.length };
    }

    function statsText(stats) {
      return `${stats.days} 个记录日 / ${stats.chains} 条研究链 / ${stats.points} 个工作点`;
    }

    function chapterMenu() {
      return `<nav class="d-chapter-nav" aria-label="研究阶段">${chapters.map((chapter, index) => {
        const count = measure(chapterPoints(chapter));
        return `<button type="button" class="d-chapter-tab${state.chapter === index ? " is-current" : ""}" data-d-chapter="${index}" aria-pressed="${state.chapter === index}" aria-controls="d-chapter-content"><span class="d-chapter-number">${chapterNames[index]}</span><strong>${esc(chapter.title)}</strong><span class="d-chapter-dates">${esc(chapter.from.slice(5).replace("-", "."))} — ${esc(chapter.to.slice(5).replace("-", "."))}</span><span class="d-chapter-count">${count.days} 日 · ${count.chains} 链 · ${count.points} 点</span></button>`;
      }).join("")}</nav>`;
    }

    function chainEntries(points) {
      const groups = new Map();
      points.forEach(point => {
        if (!groups.has(point.chain.id)) groups.set(point.chain.id, { chain: point.chain, points: [] });
        groups.get(point.chain.id).points.push(point);
      });
      return Array.from(groups.values()).sort((a, b) => b.points[0].date.localeCompare(a.points[0].date) || b.points.length - a.points.length || a.chain.label.localeCompare(b.chain.label, "zh-CN"));
    }

    function researchSection(points) {
      const groups = chainEntries(points);
      const shown = state.allChains ? groups : groups.slice(0, 4);
      return `<section class="d-research-section" aria-labelledby="d-research-title"><div class="d-section-heading"><h3 id="d-research-title">本章研究链</h3><span>${groups.length} 条，按最近记录排列</span></div>${shown.length ? `<div class="d-chain-list">${shown.map(({ chain, points: rows }) => {
        const latest = rows[0];
        const first = rows[rows.length - 1];
        return `<article class="d-chain-entry"><div class="d-chain-heading"><h4>${api.chainLink(chain.id)}</h4><span class="d-chain-track">${esc(api.track(chain.track)?.label || chain.track)}</span></div><p class="d-chain-purpose">${esc(chain.purpose || "可打开研究链，查看逐日记录。")}</p><p class="d-chain-meta">本章 ${rows.length} 个工作点，${esc(api.formatDate(first.date))}${latest.date !== first.date ? ` 至 ${esc(api.formatDate(latest.date))}` : ""}</p><div class="d-latest-point"><span class="d-point-caption">最近记录 <time datetime="${esc(latest.date)}">${esc(latest.date)}</time></span>${api.pointLink(latest)}</div></article>`;
      }).join("")}</div>` : '<p class="empty">这一章没有当前方向的工作点。可切换方向，或阅读其他章节。</p>'}${groups.length > 4 ? `<button type="button" class="button d-expand" data-d-action="chains" aria-expanded="${state.allChains}">${state.allChains ? "收起研究链" : `展开本章全部 ${groups.length} 条研究链`}</button>` : ""}</section>`;
    }

    function handoffSection(chapter, points) {
      const ids = new Set(points.map(p => p.chain.id));
      const relations = api.data.handoffs.filter(edge => edge.date && edge.date >= chapter.from && edge.date <= chapter.to && api.chain(edge.from) && api.chain(edge.to) && (ids.has(edge.from) || ids.has(edge.to))).sort((a, b) => b.date.localeCompare(a.date));
      const shown = state.allHandoffs ? relations : relations.slice(0, 3);
      return `<aside class="d-handoff-section" aria-labelledby="d-handoff-title"><div class="d-section-heading"><h3 id="d-handoff-title">本章登记的承接</h3><span>${relations.length} 项</span></div><p class="d-handoff-explainer">按承接日期归入本章。章节只是阅读分段，各方向可以并行。</p>${shown.length ? shown.map(edge => `<article class="d-handoff-entry"><p class="d-handoff-meta"><time datetime="${esc(edge.date)}">${esc(edge.date)}</time><span>${esc(edge.type)}</span></p><div class="d-handoff-links">${api.chainLink(edge.from)}<span class="d-handoff-verb">承接至</span>${api.chainLink(edge.to)}</div>${edge.source_date && edge.source_date !== edge.date ? `<p class="d-handoff-source">来源记录：${esc(edge.source_date)}</p>` : ""}<p class="d-handoff-note">${esc(edge.note || "可打开两条研究链，查看登记的具体进展。")}</p></article>`).join("") : '<p class="d-no-handoff">当前范围没有登记跨链承接；各链的工作点仍可独立阅读。</p>'}${relations.length > 3 ? `<button type="button" class="button d-expand" data-d-action="handoffs" aria-expanded="${state.allHandoffs}">${state.allHandoffs ? "收起承接记录" : `展开全部 ${relations.length} 项承接`}</button>` : ""}</aside>`;
    }

    function dailySection(points) {
      const days = new Map();
      points.forEach(point => {
        if (!days.has(point.date)) days.set(point.date, []);
        days.get(point.date).push(point);
      });
      const entries = Array.from(days.entries());
      const shown = state.allDays ? entries : entries.slice(0, 3);
      const visiblePoints = shown.reduce((sum, [, rows]) => sum + rows.length, 0);
      return `<section class="d-daily-section" aria-labelledby="d-daily-title"><div class="d-section-heading"><div><h3 id="d-daily-title">${state.allDays ? "本章完整记录" : "本章近期记录"}</h3><p>按日期从近到远，每项保留对应研究链的进展。</p></div><span>${state.allDays ? `共 ${entries.length} 日、${points.length} 点` : `显示最近 ${shown.length} 日、${visiblePoints} 点`}</span></div>${shown.length ? `<div class="d-day-list">${shown.map(([date, rows]) => `<article class="d-day-entry"><div class="d-day-index"><button type="button" class="d-day-button" data-open-day="${esc(date)}"><time datetime="${esc(date)}">${esc(api.formatDate(date))}</time><span>${esc(date.slice(0, 4))} · ${rows.length} 项工作</span><span class="d-day-open">阅读这一天</span></button></div><div class="d-day-points">${rows.map(point => `<div class="d-day-point"><div class="d-day-chain">${api.chainLink(point.chain.id, point.chain.short || point.chain.label)}</div><div class="d-day-note">${api.pointLink(point)}${point.outcome === "dropped" ? '<span class="d-point-status">历史方案未采用</span>' : ""}</div></div>`).join("")}</div></article>`).join("")}</div>` : '<p class="empty">当前方向在这一章没有记录。</p>'}${entries.length > 3 ? `<button type="button" class="button d-expand" data-d-action="days" aria-expanded="${state.allDays}">${state.allDays ? "收起，查看最近 3 个记录日" : `展开本章全部 ${entries.length} 个记录日`}</button>` : ""}</section>`;
    }

    function render(focusTarget) {
      const chapter = chapters[state.chapter];
      const fullChapter = chapterPoints(chapter);
      const points = chapterPoints(chapter, state.track);
      const stats = measure(fullChapter);
      const filteredStats = measure(points);
      const allStats = measure(allPoints);
      const trackCounts = new Map();
      fullChapter.forEach(point => trackCounts.set(point.chain.track, (trackCounts.get(point.chain.track) || 0) + 1));
      root.innerHTML = `<div class="d-chapters"><header class="d-page-intro"><div><h1>把研究读成五个阶段</h1><p>先找一段时间，再读当时的问题、研究链和具体工作。</p></div><p class="d-archive-count">${esc(allPoints[0]?.date || chapters[0].from)} 至 ${esc(api.data.asOf)}<br>${allStats.days} 个记录日，${allStats.points} 个工作点</p></header>${chapterMenu()}<article id="d-chapter-content" class="d-chapter-content" aria-labelledby="d-chapter-title"><header class="d-chapter-lead"><div class="d-lead-copy"><p class="d-chapter-kicker">${chapterNames[state.chapter]}<span>${esc(chapter.from)} 至 ${esc(chapter.to)}</span></p><h2 id="d-chapter-title">${esc(chapter.title)}</h2><p class="d-chapter-question">${esc(chapter.question)}</p><p class="d-chapter-description">${esc(chapter.description)}</p></div><dl class="d-chapter-stats"><div><dt>记录日</dt><dd>${stats.days}</dd></div><div><dt>研究链</dt><dd>${stats.chains}</dd></div><div><dt>工作点</dt><dd>${stats.points}</dd></div></dl></header><div class="d-chapter-scope"><label for="d-track-filter">本章研究方向<select id="d-track-filter" data-d-filter="track"><option value="">全部方向（${fullChapter.length} 点）</option>${api.data.tracks.map(track => `<option value="${esc(track.id)}"${track.id === state.track ? " selected" : ""}>${esc(track.label)}（${trackCounts.get(track.id) || 0} 点）</option>`).join("")}</select></label><p role="status" aria-live="polite">${state.track ? `当前方向：${esc(api.track(state.track)?.label || state.track)}，${statsText(filteredStats)}` : `当前显示本章全部方向：${statsText(stats)}`}</p></div><div class="d-chapter-overview">${researchSection(points)}${handoffSection(chapter, points)}</div>${dailySection(points)}<nav class="d-chapter-paging" aria-label="相邻章节">${state.chapter > 0 ? `<button type="button" class="button" data-d-chapter="${state.chapter - 1}"><span>上一章</span><strong>${esc(chapters[state.chapter - 1].title)}</strong></button>` : '<span class="d-chapter-boundary">这里是研究记录的开始。</span>'}${state.chapter < chapters.length - 1 ? `<button type="button" class="button" data-d-chapter="${state.chapter + 1}"><span>下一章</span><strong>${esc(chapters[state.chapter + 1].title)}</strong></button>` : `<span class="d-chapter-boundary">记录截至 ${esc(api.data.asOf)}。</span>`}</nav></article></div>`;
      if (focusTarget) root.querySelector(focusTarget)?.focus({ preventScroll: true });
    }

    root.addEventListener("click", event => {
      const chapterButton = event.target.closest("[data-d-chapter]");
      if (chapterButton && root.contains(chapterButton)) {
        const nextChapter = Number(chapterButton.dataset.dChapter);
        if (!Number.isInteger(nextChapter) || !chapters[nextChapter]) return;
        state.chapter = nextChapter;
        state.allChains = false;
        state.allHandoffs = false;
        state.allDays = false;
        render(`.d-chapter-tab[data-d-chapter="${nextChapter}"]`);
        return;
      }
      const expandButton = event.target.closest("[data-d-action]");
      if (!expandButton || !root.contains(expandButton)) return;
      const actions = { chains: "allChains", handoffs: "allHandoffs", days: "allDays" };
      const key = actions[expandButton.dataset.dAction];
      if (!key) return;
      state[key] = !state[key];
      render(`[data-d-action="${expandButton.dataset.dAction}"]`);
    });

    root.addEventListener("change", event => {
      if (!event.target.matches('[data-d-filter="track"]')) return;
      state.track = event.target.value;
      state.allChains = false;
      state.allHandoffs = false;
      state.allDays = false;
      render("#d-track-filter");
    });

    render();
  };
}());
