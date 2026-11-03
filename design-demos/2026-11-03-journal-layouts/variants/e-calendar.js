(function () {
  "use strict";
  window.JournalVariants = window.JournalVariants || {};
  window.JournalVariants.E = function(root, api) {
    const {data,esc}=api;
    const months=[...new Set(data.days.map(d=>d.date.slice(0,7)))];
    let month=data.asOf.slice(0,7), selected=data.asOf, track="";
    const inDirection=day=>api.dayTasks(day).filter(p=>!track || p.chain.track===track);
    function render() {
      const [year,num]=month.split("-").map(Number);
      const first=(new Date(Date.UTC(year,num-1,1)).getUTCDay()+6)%7;
      const length=new Date(Date.UTC(year,num,0)).getUTCDate();
      const count=Math.ceil((first+length)/7)*7;
      const monthDays=data.days.filter(d=>d.date.startsWith(month) && inDirection(d).length);
      const chosen=api.day(selected);
      const tasks=chosen?inDirection(chosen):[];
      const index=months.indexOf(month);
      const trackCount=new Set(monthDays.flatMap(d=>inDirection(d).map(p=>p.chain.id))).size;
      root.innerHTML=`<div class="page-heading"><div><h1>研究日志</h1><p>从一个日期进入，看清当天有哪些并行工作。</p></div><span class="archive-count">${data.counts.days} 个记录日 / ${data.counts.chains} 条研究链</span></div><div class="calendar-toolbar"><div class="toolbar"><button class="button" type="button" data-calendar-nav="-1" ${index===0?"disabled":""}>上个月</button><label class="field"><span class="calendar-select-label">查看月份</span><select data-calendar-month aria-label="查看月份">${months.map(m=>`<option value="${m}" ${m===month?"selected":""}>${m.slice(0,4)}年${Number(m.slice(5))}月</option>`).join("")}</select></label><button class="button" type="button" data-calendar-nav="1" ${index===months.length-1?"disabled":""}>下个月</button></div><label class="field">研究方向<select data-calendar-track><option value="">全部方向</option>${data.tracks.map(t=>`<option value="${esc(t.id)}" ${track===t.id?"selected":""}>${esc(t.label)}</option>`).join("")}</select></label></div><div class="calendar-layout"><section class="calendar-month" aria-label="${year}年${num}月研究日志"><div class="calendar-month-title"><h2>${num}<span>月</span></h2><div><strong>${year}</strong><span>${monthDays.length} 个记录日 / ${trackCount} 条链</span></div></div><div class="calendar-weekdays">${["周一","周二","周三","周四","周五","周六","周日"].map(t=>`<span>${t}</span>`).join("")}</div><div class="calendar-cells">${Array.from({length:count},(_,i)=>{const n=i-first+1;if(n<1||n>length)return '<span class="calendar-padding" aria-hidden="true"></span>';const date=`${month}-${String(n).padStart(2,"0")}`;const day=api.day(date);const ps=day?inDirection(day):[];return `<button type="button" class="calendar-cell${date===selected?" is-selected":""}${ps.length?" has-records":""}" data-calendar-day="${date}" aria-pressed="${date===selected}" aria-label="${api.formatDate(date)}，${ps.length}项工作" ${date>data.asOf||date<data.days[0].date?"disabled":""}><span>${n}</span>${ps.length?`<small>${ps.length} 项</small>`:'<i aria-hidden="true"></i>'}</button>`;}).join("")}</div><p class="calendar-key">日期下方的数量是工作项数；空白表示没有已登记记录。</p><section class="calendar-month-recap"><h3>这个月的记录</h3>${monthDays.slice(-4).reverse().map(day=>`<button type="button" data-calendar-day="${day.date}" class="calendar-recap-day"><time>${api.formatDate(day.date)}</time><span>${esc(day.headline)}</span></button>`).join("")||'<p class="muted">这个月在所选方向没有记录。</p>'}</section></section><section class="calendar-agenda" aria-live="polite"><div class="calendar-agenda-title"><div><p>${api.formatDate(selected)}<span>${["周日","周一","周二","周三","周四","周五","周六"][new Date(selected+"T00:00:00Z").getUTCDay()]}</span></p><h2>${esc(chosen?.headline||"这一天没有已登记工作")}</h2></div><span class="calendar-agenda-count">${tasks.length}<small>项工作</small></span></div>${chosen?`<div class="calendar-agenda-tasks">${tasks.map(p=>`<article><div class="calendar-agenda-track">${esc(api.track(p.chain.track)?.label)}</div><h3>${api.chainLink(p.chain.id)}</h3><p>${api.pointLink(p)}</p></article>`).join("")||'<p class="empty">所选方向在这一天没有记录。可以选择其他有标记的日期。</p>'}</div><button class="button calendar-read-day" type="button" data-open-day="${chosen.date}">阅读这一天的完整记录</button>`:'<p class="empty">选择有工作项数的日期，查看当天进展。</p>'}</section></div>`;
      root.onclick=e=>{
        const nav=e.target.closest("[data-calendar-nav]");
        if(nav){month=months[index+Number(nav.dataset.calendarNav)];selected=data.days.filter(d=>d.date.startsWith(month)).at(-1)?.date||`${month}-01`;render();return;}
        const day=e.target.closest("[data-calendar-day]");if(day){selected=day.dataset.calendarDay;render();}
      };
      root.onchange=e=>{
        if(e.target.matches("[data-calendar-month]")){month=e.target.value;selected=data.days.filter(d=>d.date.startsWith(month)).at(-1)?.date||`${month}-01`;render();}
        if(e.target.matches("[data-calendar-track]")){track=e.target.value;render();}
      };
    }
    render();
  };
}());
