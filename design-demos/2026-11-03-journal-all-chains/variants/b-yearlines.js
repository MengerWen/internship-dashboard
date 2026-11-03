/* 全部链条默认展开；横轴使用同一段自然日比例。 */
(function () {
  "use strict";
  window.JournalVariants = window.JournalVariants || {};

  window.JournalVariants.B = function (root, api) {
    const { data, esc } = api;
    const allPoints = api.points({ reverse: false });
    const byChain = new Map(data.chains.map(chain => [chain.id, []]));
    allPoints.forEach(point => byChain.get(point.chain.id)?.push(point));

    const dates = data.days.map(day => day.date).sort();
    const firstDate = dates[0] || data.asOf;
    const lastDate = data.asOf || dates[dates.length - 1];
    const dayStamp = date => Date.parse(`${date}T00:00:00Z`);
    const firstStamp = dayStamp(firstDate);
    const lastStamp = dayStamp(lastDate);
    const elapsedDays = Math.max(1, Math.round((lastStamp - firstStamp) / 86400000));
    const calendarDays = Math.round((lastStamp - firstStamp) / 86400000) + 1;
    const position = date => Math.max(0, Math.min(100, (dayStamp(date) - firstStamp) / (lastStamp - firstStamp || 1) * 100));
    const percent = value => `${value.toFixed(5)}%`;
    const shortDate = date => `${Number(date.slice(5, 7))}.${Number(date.slice(8, 10))}`;
    const fullDate = date => `${Number(date.slice(5, 7))}月${Number(date.slice(8, 10))}日`;
    const lower = value => String(value || "").toLocaleLowerCase();
    const months = [];
    let monthCursor = new Date(firstStamp);
    monthCursor.setUTCDate(1);
    while (monthCursor.getTime() <= lastStamp) {
      const monthStart = Math.max(firstStamp, monthCursor.getTime());
      const next = new Date(monthCursor);
      next.setUTCMonth(next.getUTCMonth() + 1);
      months.push({
        label: `${monthCursor.getUTCMonth() + 1}月`,
        left: position(new Date(monthStart).toISOString().slice(0, 10)),
        right: position(new Date(Math.min(lastStamp, next.getTime())).toISOString().slice(0, 10)),
      });
      monthCursor = next;
    }

    function monthLabels(className = "") {
      return `<div class="yearline-months ${className}" aria-hidden="true">${months.map((month, index) => `<span class="yearline-axis-rule" style="left:${percent(month.left)}"></span><span class="yearline-month${index === 0 ? " is-first" : ""}${index === months.length - 1 ? " is-last" : ""}" style="left:${percent((month.left + month.right) / 2)}">${esc(month.label)}</span>`).join("")}</div>`;
    }

    function monthRules() {
      return months.slice(1).map(month => `<span class="yearline-month-rule" style="left:${percent(month.left)}" aria-hidden="true"></span>`).join("");
    }

    function plot(chain, points) {
      const links = points.slice(1).map((point, index) => {
        const previous = points[index];
        const gap = Math.round((dayStamp(point.date) - dayStamp(previous.date)) / 86400000);
        return `<span class="yearline-span${gap > 3 ? " is-gap" : ""}" style="left:${percent(position(previous.date))};width:${percent(position(point.date) - position(previous.date))}" aria-hidden="true"></span>`;
      }).join("");
      return `<div class="yearline-plot" role="group" aria-label="${esc(chain.label)}的日期分布，共${points.length}个记录日"><div class="yearline-plot-inner" style="--day-step:${percent(100 / elapsedDays)}">${monthRules()}${links}${points.map(point => `<button type="button" class="yearline-point" data-open-point="${esc(chain.id)}" data-open-date="${esc(point.date)}" style="left:${percent(position(point.date))}" aria-label="${esc(`${point.date}，${chain.label}：${point.note}`)}" title="${esc(`${point.date} · ${point.note}`)}"><span aria-hidden="true"></span></button>`).join("")}</div></div>`;
    }

    function chainRow(chain) {
      const points = byChain.get(chain.id) || [];
      const first = points[0];
      const latest = points[points.length - 1];
      const range = first ? `${shortDate(first.date)}${first.date !== latest.date ? `—${shortDate(latest.date)}` : ""}` : "暂无记录";
      return `<article class="yearline-row" data-all-chain="${esc(chain.id)}">
        <div class="yearline-identity">
          <h3>${api.chainLink(chain.id, chain.label)}</h3>
          <p class="yearline-chain-meta"><span>${points.length} 个记录日</span><span>${esc(range)}</span></p>
        </div>
        <div class="yearline-history">
          ${monthLabels("yearline-mobile-months")}
          ${plot(chain, points)}
          ${latest ? `<button type="button" class="yearline-latest" data-open-point="${esc(chain.id)}" data-open-date="${esc(latest.date)}"><time datetime="${esc(latest.date)}">${esc(fullDate(latest.date))}</time><span>${esc(latest.note)}</span></button>` : '<p class="yearline-latest">当前没有登记工作点。</p>'}
        </div>
      </article>`;
    }

    root.innerHTML = `<header class="page-heading yearline-heading">
      <div><h1>研究日志</h1><p>每条链各占一行，按自然日对齐${esc(fullDate(firstDate))}至${esc(fullDate(lastDate))}的全部记录。</p></div>
      <p class="yearline-total">${data.chains.length} 条链<br>${dates.length} 个记录日 · ${allPoints.length} 个工作点</p>
    </header>
    <div class="yearline-tools">
      <label class="field yearline-search"><span>查找并高亮</span><input type="search" id="yearline-search" placeholder="链名、日期或进展" autocomplete="off"></label>
      <button type="button" class="button" id="yearline-clear" disabled>清除高亮</button>
      <p id="yearline-search-status" role="status" aria-live="polite">全部 ${data.chains.length} 条链均已展开</p>
    </div>
    <nav class="yearline-index" aria-label="跳至研究方向">${data.tracks.map(track => `<a href="#yearline-track-${esc(track.id)}">${esc(track.label)}<span>${data.chains.filter(chain => chain.track === track.id).length}</span></a>`).join("")}</nav>
    <div class="yearline-guide"><p><span class="yearline-legend-point" aria-hidden="true"></span>记录日 <span class="yearline-legend-line" aria-hidden="true"></span>相邻记录 <span class="yearline-legend-line is-gap" aria-hidden="true"></span>间隔超过三天</p><p>点位等大。连接线只表示记录跨度；点击链名或日期点读取进展与依据。</p></div>
    <div class="yearline-table" aria-label="全部链条的全历史年表">
      <div class="yearline-axis"><span class="yearline-axis-title">链条与记录区间</span><div class="yearline-axis-time">${monthLabels()}<p><time datetime="${esc(firstDate)}">${esc(firstDate)}</time><span>${calendarDays} 个自然日</span><time datetime="${esc(lastDate)}">${esc(lastDate)}</time></p></div></div>
      ${data.tracks.map(track => {
        const chains = data.chains.filter(chain => chain.track === track.id);
        return `<section class="yearline-track" id="yearline-track-${esc(track.id)}" aria-labelledby="yearline-label-${esc(track.id)}"><header class="yearline-track-heading"><h2 id="yearline-label-${esc(track.id)}">${esc(track.label)}</h2><span>${chains.length} 条链</span></header>${chains.map(chainRow).join("")}</section>`;
      }).join("")}
    </div>
    <p class="yearline-endnote">以上为 ${esc(firstDate)} 至 ${esc(lastDate)} 的正式日志记录。空白日期表示该链当天没有登记工作点，不据此判断是否运行或完成。</p>`;

    const search = root.querySelector("#yearline-search");
    const clear = root.querySelector("#yearline-clear");
    const status = root.querySelector("#yearline-search-status");
    const rows = Array.from(root.querySelectorAll("[data-all-chain]"));
    const pointButtons = Array.from(root.querySelectorAll(".yearline-point"));
    const searchableChains = new Map(data.chains.map(chain => [chain.id, lower(`${chain.label} ${chain.purpose} ${chain.fate_note || ""} ${(byChain.get(chain.id) || []).map(point => `${point.date} ${point.note}`).join(" ")}`)]));
    const searchablePoints = new Map(allPoints.map(point => [`${point.chain.id}:${point.date}`, lower(`${point.chain.label} ${point.date} ${point.note}`)]));
    function updateHighlight() {
      const query = lower(search.value.trim());
      let matches = 0;
      rows.forEach(row => {
        const match = Boolean(query && searchableChains.get(row.dataset.allChain)?.includes(query));
        row.classList.toggle("is-match", match);
        if (match) matches += 1;
      });
      pointButtons.forEach(button => button.classList.toggle("is-match", Boolean(query && searchablePoints.get(`${button.dataset.openPoint}:${button.dataset.openDate}`)?.includes(query))));
      clear.disabled = !query;
      status.textContent = query ? `${matches} 条链有匹配，全部 ${data.chains.length} 条仍显示` : `全部 ${data.chains.length} 条链均已展开`;
    }
    search.addEventListener("input", updateHighlight);
    clear.addEventListener("click", () => {
      search.value = "";
      updateHighlight();
      search.focus();
    });
  };
}());
