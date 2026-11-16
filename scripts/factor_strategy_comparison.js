/* 同一套条件驱动收益曲线、区间成绩和下载。 */
(() => {
  const MARKET = {sh:'沪市', sz:'深市', all:'沪深合计'};
  const HORIZON = {morning:'11:30', close:'收盘'};
  const VIEW = {wealth:'绝对收益',excess:'同底仓超额',delta:'相对 B0 增量'};
  const indices = market => market === 'all' ? [0,1] : [market === 'sh' ? 0 : 1];
  function sum(row, columns) {
    return row && columns.every(i => Number.isFinite(row[i])) ? columns.reduce((n,i) => n+row[i],0) : null;
  }
  function configKey(state, horizon) {
    return [state.weight,state.sorting,horizon,state.strategy,state.q].join('-') + (String(state.trade)==='10' ? '' : '-t'+state.trade);
  }
  function paths(data, key, market, ids) {
    const weight = key.split('-')[0], col = indices(market), capital = sum(data.initial[weight],col);
    const base = data.base[weight].map(row => sum(row,col));
    const amounts = Object.fromEntries(ids.map(id => {
      const result = data.results[id];
      const byDate = new Map((result?.dates || []).map((d,i) => [d,result.series[key]?.[i]]));
      return [id,data.dates.map(d => sum(byDate.get(d),col))];
    }));
    const first = amounts.B0;
    const versions = Object.fromEntries(ids.map(id => [id,{
      wealth:amounts[id].map((a,i) => a === null ? null : ((base[i]+a)/capital-1)*100),
      excess:amounts[id].map(a => a === null ? null : a/capital*100),
      delta:amounts[id].map((a,i) => a === null || first[i] === null ? null : (a-first[i])/capital*100),
      amount:amounts[id]
    }]));
    return {capital,base,basket:base.map(b => (b/capital-1)*100),versions};
  }
  function interval(data, key, market, series, id, parent, start, stop) {
    const v=series.versions[id], base=series.base;
    const ids=Array.from({length:stop-start+1},(_,i)=>i+start);
    const covered=ids.filter(i=>v.amount[i]!==null).length;
    const priorA=start ? v.amount[start-1] : 0;
    if (covered!==ids.length || priorA===null) return {covered};
    const priorB=start ? base[start-1] : series.capital;
    const wealth0=priorB+priorA;
    const addition=v.amount[stop]-priorA;
    const wealth1=base[stop]+v.amount[stop];
    let peak=wealth0, drawdown=0;
    for (const i of ids) {
      const value=base[i]+v.amount[i];
      peak=Math.max(peak,value); drawdown=Math.min(drawdown,value/peak-1);
    }
    function delta(other) {
      if (!other) return null;
      const a=series.versions[other]?.amount;
      if (!a || a[stop]===null || (start&&a[start-1]===null)) return null;
      return (addition-(a[stop]-(start?a[start-1]:0)))/priorB*100;
    }
    const ledger=data.results[id], trading=ledger?.trading?.[key];
    const local=new Map((ledger?.dates || []).map((d,i)=>[d,i]));
    const marketColumns=indices(market);
    let cost=null,turnover=null;
    if(trading && ids.every(i=>Array.isArray(trading[local.get(data.dates[i])]))) {
      cost=0;turnover=0;
      for(const i of ids) for(const m of marketColumns) {
        const row=trading[local.get(data.dates[i])]; turnover+=row[m*2];cost+=row[m*2+1];
      }
    }
    return {covered,wealth:(wealth1/wealth0-1)*100,excess:addition/priorB*100,
      delta:delta('B0'),parent:delta(parent),drawdown:drawdown*100,
      fee:cost===null?null:cost/priorB*10000, turnover:turnover===null?null:turnover/priorB*100};
  }
  function linePath(values,x,y,start=0,stop=values.length-1) {
    let connected=false, result='';
    for(let i=start;i<=stop;i++) {
      if (!Number.isFinite(values[i])) {connected=false;continue;}
      const u=x(i).toFixed(2), v=y(values[i]).toFixed(2);
      result+=`${connected?'L':'M'}${u},${v}`;connected=true;
    }
    return result;
  }
  const shown = (value, digits=4) => Number.isFinite(value) ? value.toFixed(digits) : '—';
  const selected = state => [...new Set(['B0',state.candidate,state.extra].filter(Boolean))];
  const panels = state => state.focus ? [state.focus] : (state.market==='all' ? ['all'] : ['sh','sz']).flatMap(
    market=>Object.keys(HORIZON).map(horizon=>`${market}/${horizon}`));
  function csvRows(data, state) {
    const ids=selected(state), rows=[];
    for(const pane of panels(state)) {
      const [market,horizon]=pane.split('/'),key=configKey(state,horizon);
      const p=paths(data,key,market,ids);
      for(const id of ids) for(let i=state.start;i<=state.stop;i++) {
        const v=p.versions[id];
        rows.push([data.dates[i],data.stages[i],market,horizon,key,id,p.capital,p.base[i],
          v.amount[i],v.wealth[i],v.excess[i],v.delta[i]]);
      }
    }
    return rows;
  }
  if(typeof module!=='undefined') module.exports={configKey,paths,interval,linePath,selected,panels,csvRows};
  if(typeof document==='undefined') return;

  const get=id=>document.getElementById(id), form=get('comparison-filters');
  const grid=get('comparison-panels'), slider=get('comparison-cursor'), pin=get('comparison-pin');
  const ns='http://www.w3.org/2000/svg', colors={B0:'var(--base)',G2:'var(--g2)',H01:'#8b4c17',H02:'#693b70',H03:'#57682e',H04:'#99495c',HALL:'#1d568b',basket:'var(--basket)'};
  const state={focus:null,start:0,stop:565,cursor:565,pinned:false,active:'sz/close'};
  let data, versionIndex, chartState=[];
  const visiblePaths=new Map();
  const tag=(name,text,attrs={})=>{const n=document.createElement(name);if(text!==undefined)n.textContent=text;for(const [a,v]of Object.entries(attrs))n.setAttribute(a,v);return n;};
  const svg=(name,attrs,text)=>{const n=document.createElementNS(ns,name);for(const [a,v]of Object.entries(attrs))n.setAttribute(a,v);if(text!==undefined)n.textContent=text;return n;};
  const stroke = id => ({stroke:colors[id] || 'var(--blue)','stroke-width':id==='basket'?1:2,
    'stroke-dasharray':id==='B0'?'6 4':id==='basket'?'2 4':'none'});
  const nameFor=id=>id==='basket'?'无 T 底仓':versionIndex[id].label;

  function readFilters() {
    for(const input of form.elements) if(input.name) state[input.name]=input.value;
    const nearest=(value,edge)=>{
      if(!value)return edge==='start'?0:data.dates.length-1;
      if(edge==='start') {const at=data.dates.findIndex(d=>d>=value);return at<0?data.dates.length-1:at;}
      const at=data.dates.findLastIndex(d=>d<=value);return at<0?0:at;
    };
    state.start=nearest(state.from,'start');state.stop=nearest(state.to,'stop');
    if(state.start>state.stop) [state.start,state.stop]=[state.stop,state.start];
    form.elements.from.value=data.dates[state.start];form.elements.to.value=data.dates[state.stop];
    state.cursor=Math.max(state.start,Math.min(state.cursor,state.stop));
    slider.min=state.start;slider.max=state.stop;
  }

  function chart(container,p,view,pane,ids) {
    const width=640,height=view==='delta'?148:218,left=61,right=16,top=25,bottom=27;
    const lines=ids.filter(id=>view!=='delta'||id!=='B0').map(id=>[id,p.versions[id][view]]);
    if(view==='wealth')lines.push(['basket',p.basket]);
    const [start,stop]=[state.start,state.stop];
    const paneName=pane.split('/');
    const unit=view==='delta'?'百分点':'%';
    const area=svg('svg',{viewBox:`0 0 ${width} ${height}`,class:'plot',role:'img',
      'aria-label':`${MARKET[paneName[0]]} ${HORIZON[paneName[1]]} ${VIEW[view]}（${unit}）`});
    const vals=lines.flatMap(([,v])=>v.slice(start,stop+1)).filter(Number.isFinite);
    const pad=(Math.max(0,...vals)-Math.min(0,...vals)||.02)*.09;
    const lo=Math.min(0,...vals)-pad,hi=Math.max(0,...vals)+pad;
    const x=i=>left+(stop===start?.5:(i-start)/(stop-start))*(width-left-right);
    const y=v=>top+(hi-v)/(hi-lo)*(height-top-bottom);
    area.append(svg('text',{x:left,y:16,fill:'var(--text)','font-size':14},`${VIEW[view]}（${unit}）`));
    const axis=v=>hi-lo<.05?shown(v,3):shown(v,1);
    for (const v of [lo,(lo+hi)/2,hi]) {
      area.append(svg('line',{x1:left,x2:width-right,y1:y(v),y2:y(v),stroke:'var(--soft)','stroke-width':.6}));
      area.append(svg('text',{x:left-7,y:y(v)+4,'text-anchor':'end',fill:'currentColor','font-size':12},axis(v)));
    }
    area.append(svg('line',{x1:left,x2:width-right,y1:y(0),y2:y(0),stroke:'var(--basket)','stroke-dasharray':'2 4'}));
    const transitions=[...new Set([start,...data.stages.flatMap((s,i)=>i>start&&i<stop&&s!==data.stages[i-1]?[i]:[]),stop])];
    for(const i of transitions) {
      if(i!==start&&i!==stop)area.append(svg('line',{x1:x(i),x2:x(i),y1:top,y2:height-bottom,stroke:'var(--soft)','stroke-dasharray':'3 3'}));
      if(i===start||i===stop)area.append(svg('text',{x:x(i),y:height-6,'text-anchor':i===start?'start':'end',fill:'currentColor','font-size':11},data.dates[i]));
    }
    for(const [id,values] of lines) {
      area.append(svg('path',{d:linePath(values,x,y,start,stop),fill:'none',...stroke(id),'vector-effect':'non-scaling-stroke'}));
      for(let i=start;i<=stop;i++) if(Number.isFinite(values[i])&&
        (i===start||!Number.isFinite(values[i-1]))&&(i===stop||!Number.isFinite(values[i+1])))
        area.append(svg('circle',{cx:x(i),cy:y(values[i]),r:2.5,fill:colors[id]||'var(--blue)'}));
    }
    if(!vals.length)area.append(svg('text',{x:width/2,y:height/2,'text-anchor':'middle',fill:'currentColor','font-size':13},'所选区间没有签收结果'));
    const cursor=svg('line',{y1:top,y2:height-bottom,stroke:'var(--line)','stroke-dasharray':'3 4','pointer-events':'none'});
    const selection=svg('rect',{y:top,height:height-top-bottom,fill:'var(--blue)',opacity:.10,visibility:'hidden','pointer-events':'none'});
    area.append(selection,cursor);container.append(area);
    chartState.push({cursor,x});
    let down=null;
    function coordinate(event){return (event.clientX-area.getBoundingClientRect().left)*width/area.getBoundingClientRect().width;}
    function dateAt(c){return Math.max(start,Math.min(stop,Math.round(start+(c-left)/(width-left-right)*(stop-start))));}
    area.addEventListener('pointerdown',event=>{if(event.button!==0)return;down=coordinate(event);area.setPointerCapture(event.pointerId);});
    area.addEventListener('pointermove',event=>{
      const c=coordinate(event);
      if(down!==null&&Math.abs(c-down)>5){selection.setAttribute('visibility','visible');selection.setAttribute('x',Math.min(x(dateAt(c)),x(dateAt(down))));selection.setAttribute('width',Math.abs(x(dateAt(c))-x(dateAt(down))));}
      if(!state.pinned&&event.pointerType!=='touch'){state.active=pane;selectDate(dateAt(c));}
    });
    area.addEventListener('pointerup',event=>{
      if(down===null)return;
      const c=coordinate(event),i=dateAt(c),a=dateAt(down);down=null;selection.setAttribute('visibility','hidden');
      state.active=pane;
      if(Math.abs(i-a)>1){form.elements.from.value=data.dates[Math.min(i,a)];form.elements.to.value=data.dates[Math.max(i,a)];render();}
      else{state.pinned=true;selectDate(i);}
    });
    area.addEventListener('pointercancel',()=>{down=null;selection.setAttribute('visibility','hidden');});
  }

  function selectDate(i) {
    state.cursor=i;slider.value=i;pin.setAttribute('aria-pressed',state.pinned);pin.textContent=state.pinned?'取消固定':'固定读数';
    for(const {cursor,x} of chartState){cursor.setAttribute('x1',x(i));cursor.setAttribute('x2',x(i));}
    const panes=panels(state),active=panes.includes(state.active)?state.active:panes[0];
    const [m,h]=active.split('/'), ids=selected(state), p=visiblePaths.get(active);
    const mode=state.view==='wealth'?'wealth':'excess';
    get('comparison-readout').textContent=`${data.dates[i]} · ${MARKET[m]} ${HORIZON[h]} · ${VIEW[mode]}： ${ids.map(id=>{
      const value=p.versions[id][mode][i],delta=p.versions[id].delta[i];
      return `${nameFor(id)} ${shown(value)}${value===null?'':'%'}${id!=='B0'&&delta!==null?`（较 B0 ${shown(delta)} pp）`:''}`;
    }).join('；')}`;
  }

  function rows(panes) {
    const body=get('comparison-rows'),nodes=[];
    const ids=data.versions.map(v=>v.id);
    for(const pane of panes){
      const [m,h]=pane.split('/'),key=configKey(state,h),p=paths(data,key,m,ids);
      for(const v of data.versions){
        const r=interval(data,key,m,p,v.id,v.parent,state.start,state.stop);
        const tr=tag('tr');
        tr.append(tag('th',v.label,{scope:'row',class:'no-wrap'}),tag('td',v.parent||'—'),tag('td',`${v.markets}；${v.features}`),tag('td',`${MARKET[m]} · ${HORIZON[h]}`,{class:'no-wrap'}),
          tag('td',`${r.covered}/${state.stop-state.start+1} 日 · ${v.status}`));
        for(const col of ['wealth','excess','delta','parent','drawdown','fee','turnover'])tr.append(tag('td',shown(r[col]),{class:'number'}));
        nodes.push(tr);
      }
    }
    body.replaceChildren(...nodes);
    get('comparison-table-caption').textContent=`${data.dates[state.start]} 至 ${data.dates[state.stop]}。区间内有缺失时不计算区间收益；进场金额以该区间期初底仓归一。`;
  }

  function render() {
    readFilters();chartState=[];visiblePaths.clear();
    const ids=selected(state), panes=panels(state), group=[];
    grid.classList.toggle('single',Boolean(state.focus));
    for(const pane of panes){
      const [m,h]=pane.split('/'),p=paths(data,configKey(state,h),m,ids);
      visiblePaths.set(pane,p);
      const panel=tag('figure',undefined,{class:'panel'}),heading=tag('div',undefined,{class:'panel-head'});
      const btn=tag('button',state.focus?'返回分面':'放大此图',{type:'button','aria-label':`${state.focus?'返回分面':`放大${MARKET[m]} ${HORIZON[h]}收益图`}`});
      btn.addEventListener('click',()=>{state.focus=state.focus?null:pane;state.active=pane;render();const button=grid.querySelector('button');button?.focus({preventScroll:true});});
      heading.append(tag('h3',`${MARKET[m]} · ${HORIZON[h]}`),btn);panel.append(heading);
      const views=state.view==='both'?['wealth','excess']:[state.view];
      for(const view of [...views,'delta'])chart(panel,p,view,pane,ids);
      group.push(panel);
    }
    grid.replaceChildren(...group);
    const legend=ids.slice();if(state.view!=='excess')legend.push('basket');
    get('comparison-legend').replaceChildren(...legend.map(id=>{
      const item=tag('li'),mark=svg('svg',{viewBox:'0 0 28 10','aria-hidden':true});
      mark.append(svg('line',{x1:0,x2:28,y1:5,y2:5,...stroke(id)}));item.append(mark,tag('span',nameFor(id)));return item;
    }));
    get('comparison-status').textContent=ids.map(id=>`${nameFor(id)}：${versionIndex[id].coverage} 日，${versionIndex[id].status}`).join('；');
    rows(panes);selectDate(state.cursor);
  }

  function detail(factor,focus=false) {
    const el=get('factor-definition'),list=tag('dl');
    el.replaceChildren(tag('h3',`${factor.name} · ${factor.id}`));
    const missing='尚无签收诊断';
    const sections=[['变体与假设',`${factor.variant}。${factor.hypothesis}`],['定义与信息窗',`${factor.definition} 只用 [09:30:00, 09:35:00) 和可得的前期历史。`],['数据质量',factor.quality??`${factor.input}；覆盖、合法零、常数和缺失分别待核。`],['IC 与稳定性',factor.predictive??missing],['分组与不确定性',factor.grouping??missing],['增量与去重',factor.nearest],['入模影响',`${factor.state}。${factor.stateReason}`]];
    for(const [label,text]of sections)list.append(tag('dt',label),tag('dd',text));el.append(list);
    if(focus){el.setAttribute('tabindex','-1');el.focus({preventScroll:true});el.scrollIntoView({block:'nearest'});}
  }
  function factorRows(){
    const needle=get('factor-search').value.trim().toLowerCase(), batch=get('factor-batch').value;
    const matches=data.factors.filter(f=>(!batch||batch===f.batch)&&(!needle||[f.name,f.family,f.id,f.batch,f.nearest].join(' ').toLowerCase().includes(needle)));
    const nodes=matches.map(f=>{
      const tr=tag('tr'),th=tag('th',undefined,{scope:'row'}),a=tag('button',f.name,{type:'button','aria-describedby':'factor-detail'});
      a.addEventListener('click',()=>detail(f,true));th.append(a,tag('small',` ${f.batch} · ${f.id}`));tr.append(th);
      const fields=[`${f.market} · ${f.side}`,`${shown(f.coverage)} / ${f.validDays??'—'}`,`${shown(f.zero)} / ${f.constant??'—'}`,
        shown(f.ic),shown(f.rankIc),shown(f.icir),shown(f.hac),shown(f.spread),`${f.nearest}；${shown(f.correlation)}`,f.state];
      for(const cell of fields)tr.append(tag('td',cell));return tr;
    });
    if(!nodes.length){const tr=tag('tr');tr.append(tag('td','没有符合条件的因子。',{colspan:11}));nodes.push(tr);}
    get('factor-rows').replaceChildren(...nodes);
  }
  async function start() {
    try {
      const raw=Uint8Array.from(atob(get('comparison-data').textContent.trim()),letter=>letter.charCodeAt(0));
      data=JSON.parse(await new Response(new Blob([raw]).stream().pipeThrough(new DecompressionStream('gzip'))).text());
      versionIndex=Object.fromEntries(data.versions.map(v=>[v.id,v]));
      for(const v of data.versions.filter(v=>v.id!=='B0')) for(const field of ['candidate','extra'])
        form.elements[field].append(tag('option',v.label,{value:v.id}));
      form.elements.candidate.value=data.default_candidate;
      for(const n of ['from','to']){form.elements[n].min=data.dates[0];form.elements[n].max=data.dates.at(-1);}
      form.addEventListener('submit',event=>event.preventDefault());
      form.addEventListener('change',event=>{if(event.target.name==='market')state.focus=null;render();});
      slider.addEventListener('input',()=>selectDate(Number(slider.value)));
      pin.addEventListener('click',()=>{state.pinned=!state.pinned;selectDate(state.cursor);});
      get('comparison-reset').addEventListener('click',()=>{form.elements.from.value='';form.elements.to.value='';state.cursor=data.dates.length-1;state.pinned=false;render();});
      get('comparison-download').addEventListener('click',()=>{
        const fields='date,stage,market,horizon,configuration,version,initial_cash,base_value,overlay_value,wealth_pct,excess_pct,delta_B0_pp';
        const blob=new Blob(['\ufeff'+[fields,...csvRows(data,state).map(row=>row.join(','))].join('\n')],{type:'text/csv;charset=utf-8'});
        const url=URL.createObjectURL(blob),link=tag('a',undefined,{href:url,download:'factor-strategy-comparison.csv'});link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
      });
      get('factor-search').addEventListener('input',factorRows);get('factor-batch').addEventListener('change',factorRows);
      factorRows();if(data.factors.length)detail(data.factors[0]);render();
    } catch(error){get('comparison-status').textContent=`比较数据未能读取：${error.message}`;get('comparison-status').setAttribute('role','alert');}
  }
  start();
})();
