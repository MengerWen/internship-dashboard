(function () {
  "use strict";
  window.JournalVariants = window.JournalVariants || {};
  window.JournalVariants.A = function (root, api) {
    const {data, esc} = api;
    let period = "1m", selectedTrack = "", selectedDay = data.asOf;
    const stamp = date => Date.parse(date + "T00:00:00Z");
    function dateSequence(from, to) {
      const result = [];
      for (let n = stamp(from); n <= stamp(to); n += 86400000) result.push(new Date(n).toISOString().slice(0,10));
      return result;
    }
    function overview(from, to) {
      const dates = dateSequence(from, to);
      const map = new Map();
      api.points({from,to}).forEach(p => {const key = `${p.date}:${p.chain.track}`;map.set(key,(map.get(key) || 0) + 1);});
      const height = dates.length * 19;
      return `<div class="atlas-overview"><div class="atlas-map-header"><span>工作日期</span>${data.tracks.map(t => `<button type="button" data-atlas-track="${esc(t.id)}">${esc(t.label)}<small>${data.chains.filter(c => c.track === t.id).length} 条链</small></button>`).join("")}</div><div class="atlas-map-body" style="--map-height:${height}px"><div class="atlas-date-axis">${dates.map((date,i) => `<span style="top:${i * 19}px" class="${date === selectedDay ? "is-current" : ""}">${date.slice(5).replace("-","/")}</span>`).join("")}</div>${data.tracks.map(t => `<div class="atlas-track-lane">${dates.map((date,i) => {const count=map.get(`${date}:${t.id}`);return `<div class="atlas-day-rule" style="top:${i * 19 + 9}px"></div>${count ? `<button type="button" class="atlas-mark${date === selectedDay ? " is-selected" : ""}" data-atlas-date="${date}" data-atlas-focus-track="${esc(t.id)}" style="top:${i * 19 + 9}px" aria-label="${date}，${esc(t.label)}，${count}项工作"><span>${count > 1 ? count : ""}</span></button>` : ""}`;}).join("")}</div>`).join("")}</div></div><div class="atlas-mobile-list">${data.tracks.map(t => {const records=api.points({from,to,trackId:t.id});return `<button type="button" data-atlas-track="${esc(t.id)}"><strong>${esc(t.label)}</strong><span>${records.length} 项工作 / ${new Set(records.map(p=>p.chain.id)).size} 条活跃链</span><p>${esc(records[0]?.note || "此时间范围没有记录")}</p></button>`;}).join("")}</div>`;
    }
    function trackView(from,to) {
      const chains = data.chains.filter(c=>c.track===selectedTrack);
      const active = chains.filter(c=>api.points({chainId:c.id,from,to}).length);
      const inactive = chains.filter(c=>!active.includes(c));
      const duration = Math.max(1,stamp(to)-stamp(from));
      return `<div class="atlas-track-heading"><h2>${esc(api.track(selectedTrack).label)}</h2><span>${active.length} 条链在此期间有记录</span></div><div class="atlas-time-ruler"><span>研究链与最新进展</span><div><time>${from}</time><span>按自然日排列</span><time>${to}</time></div></div><div class="atlas-chain-rows">${active.map(c => {const ps=api.points({chainId:c.id,from,to,reverse:false});return `<section class="atlas-chain-row"><div class="atlas-chain-caption">${api.chainLink(c.id)}<p>${esc(ps.at(-1).note)}</p></div><div class="atlas-chain-track"><div class="atlas-chain-stroke" style="left:${(stamp(ps[0].date)-stamp(from))/duration*94+3}%;right:${97-(stamp(ps.at(-1).date)-stamp(from))/duration*94}%"></div>${ps.map(p=>`<button class="atlas-chain-dot${p.outcome === "dropped" ? " is-dropped" : ""}" type="button" data-open-point="${esc(c.id)}" data-open-date="${p.date}" style="left:${(stamp(p.date)-stamp(from))/duration*94+3}%" aria-label="${p.date}，${esc(p.note)}"><i></i></button>`).join("")}</div><div class="atlas-chain-mobile-dates">${ps.slice(-3).map(p=>`<div><time>${api.formatDate(p.date)}</time>${api.pointLink(p)}</div>`).join("")}</div></section>`;}).join("")}</div>${inactive.length ? `<details class="atlas-inactive"><summary>此期间无新记录的 ${inactive.length} 条链</summary><div>${inactive.map(c=>api.chainLink(c.id)).join("")}</div></details>` : ""}`;
    }
    function render() {
      const {from,to} = api.range(period);
      const visible=api.points({from,to,trackId:selectedTrack || undefined});
      const focused=api.day(selectedDay) || data.days.at(-1);
      const dayPoints=api.dayTasks(focused).filter(p=>!selectedTrack || p.chain.track===selectedTrack);
      root.innerHTML=`<div class="page-heading"><div><h1>研究日志</h1><p>先看研究方向怎样推进，再展开一组链，找到具体的一天。</p></div><span class="archive-count">${data.counts.chains} 条链 / ${data.counts.days} 个记录日</span></div><div class="atlas-toolbar"><div class="toolbar">${["1m","3m","all"].map((p,i)=>`<button type="button" class="button${period===p?" is-active":""}" data-atlas-period="${p}">${["近一个月","近三个月","全部历史"][i]}</button>`).join("")}</div><span class="date-label">${from} 至 ${to} / ${visible.length} 项工作</span></div>${selectedTrack?`<div class="atlas-breadcrumb"><button class="subtle-button" type="button" data-atlas-track="">全部研究方向</button><span>/ ${esc(api.track(selectedTrack).label)}</span></div>`:""}<div class="atlas-chart">${selectedTrack?trackView(from,to):overview(from,to)}</div><p class="atlas-caption">${selectedTrack?"每行是一条链；圆点对应真实工作日期，点开可读具体进展。":"每列是一个方向；标记表示当天有记录，数字表示同方向当天并行的工作项数。点击方向名称展开链条。"}</p><section class="atlas-day-detail"><div class="section-heading"><h2>${api.formatDate(focused.date)}的具体工作</h2><button class="subtle-button" type="button" data-open-day="${focused.date}">阅读当天记录</button></div><div class="atlas-task-list">${dayPoints.map(p=>`<div><span>${api.chainLink(p.chain.id,p.chain.short||p.chain.label)}</span><p>${api.pointLink(p)}</p></div>`).join("") || '<p class="muted">所选方向在这一天没有记录。</p>'}</div></section>`;
      root.onclick=e=>{
        const range=e.target.closest("[data-atlas-period]");if(range){period=range.dataset.atlasPeriod;render();return;}
        const track=e.target.closest("[data-atlas-track]");if(track){selectedTrack=track.dataset.atlasTrack;render();return;}
        const day=e.target.closest("[data-atlas-date]");if(day){selectedDay=day.dataset.atlasDate;selectedTrack=day.dataset.atlasFocusTrack;render();}
      };
    }
    render();
  };
}());
