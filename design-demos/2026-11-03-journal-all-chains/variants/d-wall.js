(function(){
  "use strict";
  window.JournalVariants=window.JournalVariants||{};
  window.JournalVariants.D=function(root,api){
    const {data,esc}=api;
    const ordered=data.tracks.flatMap(t=>data.chains.filter(c=>c.track===t.id));
    const first=data.days[0].date,last=data.asOf;
    const stamp=d=>Date.parse(d+'T00:00:00Z');
    const span=stamp(last)-stamp(first);
    let query='', grouping='track';
    const records=ordered.map(c=>({chain:c,points:api.points({chainId:c.id,reverse:false})}));
    function matches(record){return !query||`${record.chain.label} ${record.chain.short} ${record.chain.purpose} ${record.points.map(p=>p.note).join(' ')}`.toLocaleLowerCase().includes(query.toLocaleLowerCase());}
    function render(){
      const list=grouping==='recent'?records.slice().sort((a,b)=>(b.points.at(-1)?.date||'').localeCompare(a.points.at(-1)?.date||'')):records;
      root.innerHTML=`<div class="page-heading dw-heading"><div><h1>研究日志</h1><p>全部48条链先铺开，再从任意一条读进展。</p></div><span class="archive-count">${data.counts.days}个记录日 / ${data.counts.points}个工作点</span></div><div class="dw-controls"><label class="field">查找<input type="search" data-dw-query value="${esc(query)}" placeholder="高亮链名或进展，全部保留"></label><label class="field">排列<select data-dw-order><option value="track" ${grouping==='track'?'selected':''}>按研究方向</option><option value="recent" ${grouping==='recent'?'selected':''}>按最近进展</option></select></label><span class="dw-axis-key">每格时间线均为 ${first.slice(5)} 至 ${last.slice(5)}</span></div><div class="dw-wall">${list.map(r=>{const c=r.chain,ps=r.points;return `<button type="button" class="dw-chain${query&&matches(r)?' is-match':''}" data-all-chain="${esc(c.id)}" data-dw-chain="${esc(c.id)}" data-open-chain="${esc(c.id)}" aria-label="${esc(c.label)}，${ps.length}个记录日，最新${esc(ps.at(-1)?.note||'暂无记录')}" title="${esc(c.label)}"><small class="dw-track">${esc(api.track(c.track)?.label)}</small><strong>${esc(c.short||c.label)}</strong><svg viewBox="0 0 140 22" preserveAspectRatio="none" role="img" aria-label="${esc(c.label)}的工作日期分布"><path class="dw-baseline" d="M3 11H137"/>${ps.length?`<path class="dw-span" d="M${3+(stamp(ps[0].date)-stamp(first))/span*134} 11H${3+(stamp(ps.at(-1).date)-stamp(first))/span*134}"/>`:''}${ps.map(p=>`<circle cx="${3+(stamp(p.date)-stamp(first))/span*134}" cy="11" r="2.2"/>`).join('')}</svg><span class="dw-chain-foot"><span>${ps.length}日</span><time>${ps.at(-1)?.date.slice(5).replace('-','/')||''}</time></span></button>`;}).join('')}</div><p class="dw-note">每格是一条独立链，点表示它实际有记录的日期。按方向或最近进展重排，链条总数始终是48；点击任一链可读全部具体工作。</p><div class="dw-direction-key">${data.tracks.map(t=>`<span><b>${esc(t.label)}</b> ${ordered.filter(c=>c.track===t.id).length}条</span>`).join('')}</div>`;
      root.oninput=e=>{if(e.target.matches('[data-dw-query]')){query=e.target.value;root.querySelectorAll('[data-dw-chain]').forEach(el=>el.classList.toggle('is-match',Boolean(query)&&matches(records.find(r=>r.chain.id===el.dataset.dwChain))));}};
      root.onchange=e=>{if(e.target.matches('[data-dw-order]')){grouping=e.target.value;render();}};
    }
    render();
  };
}());
