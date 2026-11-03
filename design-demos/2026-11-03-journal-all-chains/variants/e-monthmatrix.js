/* 全部链按月并置；单元格只展开对应月份的真实工作点。 */
(function () {
  "use strict";

  window.JournalVariants = window.JournalVariants || {};
  window.JournalVariants.E = function (root, api) {
    const {data, esc} = api;
    const year = data.asOf.slice(0, 4);
    const months = [6, 7, 8, 9, 10, 11].map(number => ({
      number,
      key: `${year}-${String(number).padStart(2, "0")}`,
      label: `${number}月`,
      length: new Date(Number(year), number, 0).getDate(),
    }));
    const allPoints = api.points({reverse: false});
    const chainRows = new Map(data.chains.map(chain => {
      const points = allPoints.filter(point => point.chain.id === chain.id);
      const buckets = months.map(month => {
        const monthlyPoints = points.filter(point => point.date.slice(0, 7) === month.key);
        const dates = [...new Set(monthlyPoints.map(point => point.date))].sort();
        return {points: monthlyPoints, dates};
      });
      return [chain.id, {chain, points, buckets}];
    }));
    const recordDays = new Set(allPoints.map(point => point.date)).size;
    let selected = null;

    function monthCell(row, month, index) {
      const bucket = row.buckets[index];
      const dateNumbers = bucket.dates.map(date => Number(date.slice(8, 10)));
      const calendar = dateNumbers.map(number => `<span>${number}</span>`).join("");
      const ticks = dateNumbers.map(number => `<i style="left:${((number - 1) / (month.length - 1) * 100).toFixed(3)}%"></i>`).join("");
      const label = `${row.chain.label}，${year}年${month.label}，${bucket.dates.length}个记录日${dateNumbers.length ? `，日期为${dateNumbers.join("、")}日` : ""}`;
      return `<div class="mm-cell${bucket.dates.length ? " has-records" : ""}" role="cell">
        ${bucket.dates.length ? `<button type="button" class="mm-month" data-mm-month="${index}" data-mm-chain="${esc(row.chain.id)}" aria-label="${esc(label)}" aria-expanded="false">
          <span class="mm-mobile-month">${month.label}</span>
          <span class="mm-amount"><b>${bucket.dates.length}</b><span>日</span></span>
          <span class="mm-spark" aria-hidden="true">${ticks}</span>
          <span class="mm-dates" aria-hidden="true">${calendar}</span>
        </button>` : `<div class="mm-blank" aria-label="${esc(label)}"><span class="mm-mobile-month">${month.label}</span><span aria-hidden="true">—</span></div>`}
      </div>`;
    }

    function chainRow(chain) {
      const row = chainRows.get(chain.id);
      return `<div class="mm-chain-row" role="row" data-all-chain="${esc(chain.id)}">
        <div class="mm-name" role="rowheader">
          <button type="button" class="mm-chain-name" data-open-chain="${esc(chain.id)}">${esc(chain.label)}</button>
          <div class="mm-chain-meta"><span>${new Set(row.points.map(point => point.date)).size}个记录日</span><span class="mm-match-tag">匹配</span></div>
        </div>
        ${months.map((month, index) => monthCell(row, month, index)).join("")}
      </div>`;
    }

    root.innerHTML = `<section class="mm-page" data-cell-mode="count">
      <header class="page-heading mm-heading">
        <div><h1>研究日志</h1><p>全部${data.chains.length}条链，按月份读研究进展。</p></div>
        <p class="mm-archive"><span>${year}年6—11月</span><span>${recordDays}个记录日，${allPoints.length}个工作点</span></p>
      </header>
      <div class="mm-tools">
        <div class="mm-mode" role="group" aria-label="单元格显示方式"><button type="button" data-mm-mode="count" aria-pressed="true">记录天数</button><button type="button" data-mm-mode="dates" aria-pressed="false">具体日期</button></div>
        <label class="mm-search"><span>查找并高亮</span><input type="search" data-mm-search placeholder="链名、进展或日期" autocomplete="off"></label>
      </div>
      <div class="mm-explainer"><p>数字表示该链当月有记录的天数，短刻度对应日期。点击非空格，展开当月记录。</p><p class="mm-search-status" data-mm-status aria-live="polite">${data.chains.length}条链全部展开</p></div>
      <div class="mm-matrix" role="table" aria-label="全部研究链的月份矩阵" aria-colcount="7">
        <div class="mm-grid-header" role="row"><div role="columnheader">研究链条<span>按${data.tracks.length}个方向分区</span></div>${months.map(month => `<div role="columnheader">${month.label}</div>`).join("")}</div>
        ${data.tracks.map(track => {
          const chains = data.chains.filter(chain => chain.track === track.id);
          const count = chains.reduce((total, chain) => total + chainRows.get(chain.id).points.length, 0);
          return `<div class="mm-group" role="rowgroup" aria-label="${esc(track.label)}"><div class="mm-group-title" role="row"><div role="cell" aria-colspan="7"><h2>${esc(track.label)}</h2><span>${chains.length}条链，${count}个工作点</span></div></div>${chains.map(chainRow).join("")}</div>`;
        }).join("")}
      </div>
      <p class="mm-endnote">全部链条已列出。记录截至${esc(data.asOf)}；空格表示该链当月没有登记工作点。</p>
    </section>`;

    const page = root.querySelector(".mm-page");
    const search = root.querySelector("[data-mm-search]");
    const status = root.querySelector("[data-mm-status]");

    function highlightSearch() {
      const term = search.value.trim().toLocaleLowerCase();
      let matches = 0;
      root.querySelectorAll(".mm-chain-row").forEach(element => {
        const row = chainRows.get(element.dataset.allChain);
        const identity = `${row.chain.label} ${row.chain.short || ""} ${row.chain.purpose || ""} ${api.track(row.chain.track)?.label || ""}`.toLocaleLowerCase();
        const identityMatch = !!term && identity.includes(term);
        const matchingMonths = row.buckets.map(bucket => !!term && bucket.points.some(point => `${point.date} ${point.note}`.toLocaleLowerCase().includes(term)));
        const isMatch = identityMatch || matchingMonths.some(Boolean);
        element.classList.toggle("is-search-match", isMatch);
        if (isMatch) matches += 1;
        element.querySelectorAll("[data-mm-month]").forEach(button => {
          button.classList.toggle("is-search-match", identityMatch || matchingMonths[Number(button.dataset.mmMonth)]);
        });
      });
      status.textContent = term ? `高亮${matches}条链，全部${data.chains.length}条链仍在` : `${data.chains.length}条链全部展开`;
    }

    function closeMonth(restoreFocus) {
      const previousButton = selected?.button;
      root.querySelector(".mm-detail-row")?.remove();
      root.querySelectorAll(".mm-month.is-selected").forEach(button => {
        button.classList.remove("is-selected");
        button.setAttribute("aria-expanded", "false");
        button.removeAttribute("aria-controls");
      });
      root.querySelectorAll(".mm-chain-row.is-selected").forEach(row => row.classList.remove("is-selected"));
      selected = null;
      if (restoreFocus && previousButton?.isConnected) previousButton.focus({preventScroll: true});
    }

    function openMonth(button) {
      const chainId = button.dataset.mmChain;
      const index = Number(button.dataset.mmMonth);
      if (selected?.chainId === chainId && selected?.index === index) {
        closeMonth(false);
        return;
      }
      closeMonth(false);
      const row = chainRows.get(chainId);
      const month = months[index];
      const bucket = row?.buckets[index];
      if (!bucket?.points.length) return;
      const detail = document.createElement("div");
      detail.className = "mm-detail-row";
      detail.setAttribute("role", "row");
      detail.innerHTML = `<div role="cell" aria-colspan="7"><section class="mm-detail" id="mm-month-reading" aria-labelledby="mm-month-title">
        <header class="mm-detail-heading"><div><p>${year}年${month.label} / ${bucket.dates.length}个记录日，${bucket.points.length}个工作点</p><h3 id="mm-month-title">${esc(row.chain.label)}</h3></div><button type="button" class="mm-close" data-mm-close>收起当月记录</button></header>
        <ol class="mm-point-list">${bucket.points.map(point => `<li><button type="button" class="mm-point" data-open-point="${esc(chainId)}" data-open-date="${esc(point.date)}"><time datetime="${esc(point.date)}">${esc(point.date)}</time><span>${esc(point.note)}${point.outcome === "dropped" ? '<small>历史方案未采用</small>' : ""}</span><span class="mm-read-label">阅读</span></button></li>`).join("")}</ol>
      </section></div>`;
      const element = button.closest(".mm-chain-row");
      element.insertAdjacentElement("afterend", detail);
      element.classList.add("is-selected");
      button.classList.add("is-selected");
      button.setAttribute("aria-expanded", "true");
      button.setAttribute("aria-controls", "mm-month-reading");
      selected = {chainId, index, button};
    }

    root.addEventListener("click", event => {
      const mode = event.target.closest("[data-mm-mode]");
      if (mode) {
        page.dataset.cellMode = mode.dataset.mmMode;
        root.querySelectorAll("[data-mm-mode]").forEach(button => button.setAttribute("aria-pressed", String(button === mode)));
        return;
      }
      const month = event.target.closest("[data-mm-month]");
      if (month) {
        openMonth(month);
        return;
      }
      if (event.target.closest("[data-mm-close]")) closeMonth(true);
    });
    root.addEventListener("keydown", event => {
      if (event.key === "Escape" && selected && !document.getElementById("reading-dialog")?.open) {
        closeMonth(true);
      }
    });
    search.addEventListener("input", highlightSearch);
  };
}());
