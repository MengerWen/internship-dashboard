(function(){
  "use strict";
  window.JournalVariants=window.JournalVariants||{};
  window.JournalVariants.A=function(root,api){
    const {data,esc}=api;
    const chains=data.tracks.flatMap(t=>data.chains.filter(c=>c.track===t.id));
    const index=new Map(chains.map((c,i)=>[c.id,i]));
    const all=api.points({reverse:false}), first=data.days[0].date, last=data.asOf;
    const stamp=d=>Date.parse(d+'T00:00:00Z')/86400000;
    const span=stamp(last)-stamp(first);
    const labels={infra:'数据',snapshot:'快照',footprint:'痕迹',factor:'因子',model:'模型',delivery:'交付',special:'专题'};
    let density=7, connections=true, query='';
    const match=c=>!query||`${c.label} ${c.short} ${c.purpose}`.toLocaleLowerCase().includes(query.toLocaleLowerCase());
    const x=id=>(index.get(id)+.5)/chains.length*1000;
    const y=date=>14+(stamp(date)-stamp(first))*density;
    function render(){
      const height=span*density+30;
      const ticks=[];
      for(let n=stamp(first);n<=stamp(last);n++){
        const date=new Date(n*86400000).toISOString().slice(0,10);
        if(date.endsWith('-01')||n===stamp(first)||new Date(n*86400000).getUTCDay()===1)ticks.push(date);
      }
      const ptsByChain=new Map(chains.map(c=>[c.id,all.filter(p=>p.chain.id===c.id)]));
      root.innerHTML=`<div class="page-heading"><div><h1>研究日志</h1><p>48条链同时并列，保留日期纵轴；全部链名始终留在图面。</p></div><span class="archive-count">${first} 至 ${last}</span></div><div class="vv-toolbar"><label class="field">查找链条<input type="search" data-vv-query value="${esc(query)}" placeholder="只高亮，不隐藏链条"></label><label class="field">纵向间距<select data-vv-density>${[[4,'压缩'],[7,'紧凑'],[12,'舒展']].map(([v,l])=>`<option value="${v}" ${v===density?'selected':''}>${l}</option>`).join('')}</select></label><label class="vv-check"><input type="checkbox" data-vv-connections ${connections?'checked':''}>显示承接线</label><span>${chains.length}条链 / ${all.length}个工作点</span></div><div class="vv-all-chart"><div class="vv-group-head"><span>日期</span>${data.tracks.map(t=>`<span style="grid-column:span ${chains.filter(c=>c.track===t.id).length}" title="${esc(t.label)}">${labels[t.id]||esc(t.label)}</span>`).join('')}</div><div class="vv-chain-head"><span class="vv-head-key">全部<br>链条</span>${chains.map(c=>`<button type="button" data-all-chain="${esc(c.id)}" data-vv-head="${esc(c.id)}" data-open-chain="${esc(c.id)}" class="${query&&match(c)?'is-match':''}" aria-label="${esc(c.label)}"><strong>${esc(c.short||c.label)}</strong><small>${ptsByChain.get(c.id).length}个记录日</small></button>`).join('')}</div><div class="vv-chart-body"><div class="vv-axis" style="height:${height}px">${ticks.map(d=>`<time style="top:${y(d)-7}px">${d.slice(5).replace('-','/')}</time>`).join('')}</div><svg class="vv-plot" width="100%" height="${height}" viewBox="0 0 1000 ${height}" preserveAspectRatio="none" role="group" aria-label="48条研究链的全部工作日期">${ticks.map(d=>`<path class="vv-rule" d="M0 ${y(d)}H1000"/>`).join('')}${connections?data.handoffs.filter(h=>index.has(h.from)&&index.has(h.to)).map(h=>{const ax=x(h.from),bx=x(h.to),ay=y(h.source_date||h.date),by=y(h.date);return `<path class="vv-handoff" d="M${ax},${ay} C${ax},${ay+(by-ay)/2} ${bx},${ay+(by-ay)/2} ${bx},${by}"/>`;}).join(''):''}${chains.map(c=>{const ps=ptsByChain.get(c.id);return `<g data-vv-plot="${esc(c.id)}">${ps.length?`<path class="vv-chain-line" d="M${x(c.id)} ${y(ps[0].date)}V${y(ps.at(-1).date)}"/>`:''}${ps.map(p=>`<g class="vv-point" data-open-point="${esc(c.id)}" data-open-date="${p.date}" tabindex="0" role="button" aria-label="${p.date} ${esc(p.chain.label)} ${esc(p.note)}"><title>${p.date} ${esc(p.note)}</title><circle cx="${x(c.id)}" cy="${y(p.date)}" r="5.5" class="vv-hit"/><circle cx="${x(c.id)}" cy="${y(p.date)}" r="2.8" class="vv-dot"/></g>`).join('')}</g>`;}).join('')}</svg></div></div><p class="vv-legend">每条链的短名对应一列；圆点大小统一，仅表示真实工作记录。日期按自然日排布，承接线来自已登记关系。搜索只高亮，48条链始终保留。</p>`;
      root.oninput=e=>{if(e.target.matches('[data-vv-query]')){query=e.target.value;highlight();}};
      root.onchange=e=>{if(e.target.matches('[data-vv-density]')){density=Number(e.target.value);render();highlight();}if(e.target.matches('[data-vv-connections]')){connections=e.target.checked;render();highlight();}};
      root.onkeydown=e=>{const p=e.target.closest('[data-open-point]');if(p&&(e.key==='Enter'||e.key===' ')){e.preventDefault();api.openPoint(p.dataset.openDate,p.dataset.openPoint);}};
    }
    function highlight(){
      root.querySelectorAll('[data-vv-head]').forEach(el=>el.classList.toggle('is-match',Boolean(query)&&match(api.chain(el.dataset.vvHead))));
      root.querySelectorAll('[data-vv-plot]').forEach(el=>el.classList.toggle('is-match',Boolean(query)&&match(api.chain(el.dataset.vvPlot))));
    }
    render();
  };
}());
