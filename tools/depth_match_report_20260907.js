'use strict';
const D=JSON.parse(document.getElementById('report-data').textContent),$=id=>document.getElementById(id),BASE='../assets/depth-match-2026-09-07/',cols=D.registry.columns,periods=[...new Set(D.period_summary.map(r=>r.period))],specs=D.registry.specs;
const num=(v,n=5)=>v===null||v===undefined||!Number.isFinite(+v)?'—':Number(v).toFixed(n),comma=v=>Number(v).toLocaleString('en-US'),pname=p=>p==='full'?'全部 601 日':p,esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const find=(arr,c,p)=>arr.find(r=>r.formal_column===c&&r.period===p),stat=(c,p,m='rank_ic')=>D.period_summary.find(r=>r.formal_column===c&&r.period===p&&r.metric===m),spread=(c,p)=>find(D.decile_spread_summary,c,p),spec=c=>specs[cols.indexOf(c)];
function save(s,name,type='text/csv;charset=utf-8'){const u=URL.createObjectURL(new Blob([s],{type})),a=document.createElement('a');a.href=u;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(u),1000)}
const csv=rs=>rs.map(r=>r.map(v=>'"'+String(v??'').replaceAll('"','""')+'"').join(',')).join('\r\n');
function table(headers,rows){return '<table><thead><tr>'+headers.map(h=>'<th>'+h+'</th>').join('')+'</tr></thead><tbody>'+rows.map(r=>'<tr>'+r.map(v=>'<td>'+v+'</td>').join('')+'</tr>').join('')+'</tbody></table>'}
const notes=[
'要求提交时可触及第一档，并且 Q=D1；按原始整数股数精确比较。',
'在精确一档匹配上要求初始主动撮合已确认结束且仅吃完原第一档，不能用生命周期总成交代替。',
'精确匹配一档数量，同时提交价格允许触及第二档，描述数量止于一档的行为。',
'精确匹配一档数量，且提交价格只允许触及第一档。第二档不存在或类型语义未知时不可判。',
'一档深度至少 100 股，Q 等于将 D1 向下取整到百股网格后的数量。',
'Q 不超过 D1；只在一档以下 1% 容差内给线性权重，Q=D1 时得 1。',
'精确匹配当前一档，且与严格早于一秒前的合法状态相比，最优价相同而数量不同；不要求中间路径价格始终不变。',
'同股同向最近可主动成交前单与当前单都精确匹配一档，间隔不超过一秒且提交量不同；每张当前订单最多记一次。',
'订单允许触及第二档，两档均存在，Q=D1+D2；此定义允许穿透第一档。',
'Q>D1，价格封顶第一档并确认主动吃完该档；初始撮合结束后 100ms 内全撤 Q−D1，期间无被动成交，且数量守恒。',
'精确一档匹配得分乘以距 09:35 的指数权重，半衰期 60 秒；09:34 权重为 0.5，分母不加权。',
'每侧的精确匹配命中数 C/N 乘以五个一分钟箱的归一化熵。单箱集中得 0，五箱均匀熵为 1；C=0 且可判时得 0。'];
const fullRanked=[...cols].sort((a,b)=>Math.abs(stat(b,'full').mean)-Math.abs(stat(a,'full').mean)),strongest=fullRanked[0];
$('hero-rank').textContent=num(Math.abs(stat(strongest,'full').mean),5);$('hero-t').textContent=num(Math.max(...cols.map(c=>Math.abs(stat(c,'full').nw_t))),2);
$('result-reading').textContent=strongest+'（'+spec(strongest).title+' · 卖侧）全期日均 Rank IC 为 '+num(stat(strongest,'full').mean,6)+'，NW t 为 '+num(stat(strongest,'full').nw_t,3)+'；G10−G1 为 '+num(spread(strongest,'full').mean*10000,3)+'bp。相关与组差分别描述排序和收益幅度，均保持原始方向。';
const corr=(a,b)=>D.correlation.find(r=>r.formal_column===a)[b];
$('redundancy-reading').textContent='全部 24 列的共同完整样本为 '+comma(D.redundancy.complete_stock_days)+' 个股票日，中心化原值协方差的熵有效秩为 '+num(D.redundancy.effective_rank,3)+'。一档精确匹配、执行确认、百股网格与软匹配的部分列非常接近；不能把 24 列当作 24 个独立信号。';
function drawComparisonTables(cs){
 const leaders=fullRanked.filter(c=>cs.includes(c)),best=leaders[0];
 $('result-reading').textContent=best+'（'+spec(best).title+' · '+(spec(best).side==='buy'?'买侧':'卖侧')+'）在当前方向范围内的全期 |Rank IC| 最大：日均 Rank IC '+num(stat(best,'full').mean,6)+'，NW t '+num(stat(best,'full').nw_t,3)+'；G10−G1 '+num(spread(best,'full').mean*10000,3)+'bp。相关与组差分别描述排序和收益幅度，均保持原始方向。';
 $('year-table').innerHTML=table(['正式列','2024 Rank IC','2025 Rank IC','2026H1 Rank IC','全期 Rank IC'],leaders.slice(0,6).map(c=>[c,...['2024','2025','2026H1','full'].map(p=>num(stat(c,p).mean,6))]));
 const pairs=[];
 for(const side of ['buy','sell'])for(const prefix of ['dm02_confirmed','dm05_lot_floor','dm06_soft_under']){const a='dm01_exact_'+side,b=prefix+'_'+side;if(!cs.includes(a))continue;const q=D.definition_pair_comparison.find(r=>r.column_a===a&&r.column_b===b);pairs.push([a+' ↔ '+b,num(corr(a,b),8),num(q.equality_rate*100,3)+'%',num(q.mean_absolute_difference,8)])}
 $('pair-table').innerHTML=table(['基础定义配对','Pearson r','逐值相等比例','平均绝对差'],pairs);
 $('correlation').previousElementSibling.textContent='展开当前方向范围的 '+cs.length+' 列原值相关矩阵';
 $('correlation').innerHTML='<table><thead><tr><th>列</th>'+cs.map((c,i)=>'<th title="'+c+'">'+(i+1)+'</th>').join('')+'</tr></thead><tbody>'+cs.map((c,i)=>'<tr><th title="'+c+'">'+(i+1)+' '+c+'</th>'+cs.map(b=>{const v=corr(c,b);return '<td title="'+c+' / '+b+': '+v+'" style="background:rgba('+(v>=0?'8,123,120':'178,79,53')+','+(Math.abs(v)*.55)+')">'+num(v,2)+'</td>'}).join('')+'</tr>').join('')+'</tbody></table>';
}
const MATH=JSON.parse($('formula-data').textContent),FIGS=JSON.parse($('figure-data').textContent);
const LOGICS=[
 {id:'quantity',title:'数量与深度匹配',defs:[1,5,6,9]},
 {id:'execution',title:'价格约束与执行行为',defs:[2,3,4,10]},
 {id:'adaptation',title:'盘口变化与相邻订单',defs:[7,8]},
 {id:'time',title:'近期权重与时间分布',defs:[11,12]}
];
const definitionNumber=c=>Number(spec(c).name.slice(2,4));
const logicFor=c=>LOGICS.find(g=>g.defs.includes(definitionNumber(c)));
const mathFor=c=>MATH['DM'+String(definitionNumber(c)).padStart(2,'0')];
const sideName=side=>side==='buy'?'Buy · 买侧':'Sell · 卖侧';
const tabs=[['daily','日度与累计'],['monthly','月度相关'],['groups','分组与诊断'],['scatter','散点与 OLS'],['distribution','原值分布'],['definition','定义与口径']];
const params=new URLSearchParams(location.search),collapsed=new Set();
let viewMode=params.get('view')==='separate'?'separate':'all',direction=params.get('direction')==='buy'?'buy':'sell';
let selected=cols.includes(location.hash.slice(8))?location.hash.slice(8):strongest;
let selection={kind:'definition',key:spec(selected).name},activePane=tabs.some(t=>t[0]===params.get('tab'))?params.get('tab'):'daily';
let dateRange={},selectionNotice='',zoomURL=null;
const dailyRefresh=new Map();
$('detail-period').innerHTML=periods.map(p=>'<option value="'+p+'">'+pname(p)+'</option>').join('');$('detail-period').value='full';
$('family-filter').innerHTML+=notes.map((n,i)=>'<option value="'+specs[i*2].name+'">'+specs[i*2].name+' · '+specs[i*2].title+'</option>').join('');
$('logic-filter').innerHTML+=LOGICS.map(g=>'<option value="'+g.id+'">'+g.title+'</option>').join('');
for(const [id,key] of [['detail-period','period'],['factor-arrangement','arrangement'],['factor-sort','sort'],['family-filter','family'],['logic-filter','logic']]){
 const control=$(id),value=params.get(key);if([...control.options].some(o=>o.value===value))control.value=value;
}
$('factor-search').value=params.get('q')||'';
if(params.get('scope')==='leaf'||location.hash&&!params.has('scope'))selection={kind:'leaf',key:selected};
else if(LOGICS.some(g=>'logic-'+g.id===params.get('scope')))selection={kind:'logic',key:params.get('scope').slice(6)};
else if(specs.some(s=>'definition-'+s.name===params.get('scope')))selection={kind:'definition',key:params.get('scope').slice(11)};
function resetDateRange(){const s=stat(cols[0],$('detail-period').value);dateRange={start:s.start,end:s.end}}
resetDateRange();
for(const key of ['start','end'])if(/^\d{4}-\d{2}-\d{2}$/.test(params.get(key)||''))dateRange[key]=params.get(key);
$('families').innerHTML=notes.map((n,i)=>'<article class="family"><span class="tag">'+specs[i*2].name+' · Buy / Sell</span><h3>'+specs[i*2].title+'</h3><p>'+n+'</p><div class="formula">'+MATH['DM'+String(i+1).padStart(2,'0')]+'</div><p class="small">'+(i===11?'日度因子：已含 C/N，不再除以 N。':'单笔已观察订单得分 v；日内按该侧求和后除以双边订单总数 N。')+'</p></article>').join('');
const isFlat=()=>$('factor-arrangement').value==='flat';
function filtered(){const q=$('factor-search').value.trim().toLowerCase(),family=$('family-filter').value,logic=$('logic-filter').value;
 return cols.filter(c=>(viewMode==='all'||spec(c).side===direction)&&(!family||spec(c).name===family)&&(!logic||logicFor(c).id===logic)&&(!q||(c+' '+spec(c).title+' '+sideName(spec(c).side)).toLowerCase().includes(q)));
}
function sorted(cs){const key=$('factor-sort').value,p=$('detail-period').value;
 const value=c=>{let v=key==='spread'?spread(c,p).mean:stat(c,p,key.startsWith('ic')?'pearson_ic':'rank_ic').mean;return Number.isFinite(v)?(['rank','ic_abs','spread'].includes(key)?Math.abs(v):v):-Infinity};
 return [...cs].sort((a,b)=>(key==='id'?0:value(b)-value(a))||cols.indexOf(a)-cols.indexOf(b));
}
function ordered(){const cs=sorted(filtered());if(isFlat())return cs;
 return LOGICS.flatMap(g=>{const group=cs.filter(c=>logicFor(c)===g),names=[...new Set(group.map(c=>spec(c).name))];return names.flatMap(name=>group.filter(c=>spec(c).name===name).sort((a,b)=>cols.indexOf(a)-cols.indexOf(b)))});
}
function inScope(c){return selection.kind==='leaf'?c===selection.key:selection.kind==='definition'?spec(c).name===selection.key:logicFor(c).id===selection.key}
function scopeColumns(){return ordered().filter(inScope)}
function ensureSelection(){selectionNotice='';const cs=ordered();if(!cs.length)return;
 if(isFlat()&&selection.kind!=='leaf')selection={kind:'leaf',key:cs.includes(selected)?selected:cs[0]};
 if(!cs.some(inScope)){selected=cs[0];selection={kind:'leaf',key:selected};selectionNotice='原选择不在当前筛选范围，已显示 '+selected+'。'}
 selected=cs.filter(inScope).includes(selected)?selected:cs.find(inScope);
}
function updateURL(){const u=new URL(location.href);for(const [key,value] of Object.entries({view:viewMode,direction,scope:selection.kind==='leaf'?'leaf':selection.kind+'-'+selection.key,period:$('detail-period').value,arrangement:$('factor-arrangement').value,sort:$('factor-sort').value,family:$('family-filter').value,logic:$('logic-filter').value,q:$('factor-search').value,tab:activePane,start:dateRange.start,end:dateRange.end})){if(value)u.searchParams.set(key,value);else u.searchParams.delete(key)}u.hash='factor-'+selected;history.replaceState(null,'',u)}
function select(c){if(!cols.includes(c))return;selected=c;direction=spec(c).side;selection={kind:'leaf',key:c};refresh()}
function selectScope(kind,key){selection={kind,key};refresh()}
function metric(value,key){return '<span class="metric-value '+key+'-value '+(value>0?'rank-positive':value<0?'rank-negative':'')+'">'+(value>0?'+':'')+num(value,6)+'</span>'}
function factorButton(c,index){const p=$('detail-period').value,active=selection.kind==='leaf'&&selection.key===c,label=isFlat()?(index+1)+'. '+spec(c).name.slice(0,4)+' · '+spec(c).side.toUpperCase()+'<small>'+spec(c).title+'</small>':sideName(spec(c).side);
 return '<button class="factor-item '+(active?'active':'')+'" data-id="'+c+'" aria-pressed="'+active+'"><span class="side-label">'+label+'</span>'+metric(stat(c,p,'pearson_ic').mean,'ic')+metric(stat(c,p).mean,'rank')+'</button>';
}
function branch(kind,key,title,count){return '<summary><button class="tree-toggle" aria-label="展开或收起 '+title+'"><span aria-hidden="true">▸</span></button><button class="tree-title" data-kind="'+kind+'" data-key="'+key+'" aria-pressed="'+(selection.kind===kind&&selection.key===key)+'">'+title+'<small>'+count+' 个方向因子</small></button></summary>'}
function drawList(){const cs=ordered();$('factor-count').textContent=cs.length+' / '+(viewMode==='all'?24:12)+' 个方向因子';
 $('navigation-description').textContent=isFlat()?'全部符合筛选条件的方向因子 · 不分组排序':'研究逻辑 → 具体定义 → Buy / Sell';document.querySelector('.tree-controls').hidden=isFlat();
 let content=isFlat()?cs.map(factorButton).join(''):LOGICS.map(g=>{const group=cs.filter(c=>logicFor(c)===g);if(!group.length)return '';
  return '<details class="factor-family" data-branch="logic-'+g.id+'" '+(collapsed.has('logic-'+g.id)?'':'open')+'>'+branch('logic',g.id,g.title,group.length)+[...new Set(group.map(c=>spec(c).name))].map(name=>{
   const variants=group.filter(c=>spec(c).name===name);return '<details class="factor-variant" data-branch="definition-'+name+'" '+(collapsed.has('definition-'+name)?'':'open')+'>'+branch('definition',name,name.slice(0,4)+' · '+spec(variants[0]).title,variants.length)+variants.map(factorButton).join('')+'</details>';
  }).join('')+'</details>';
 }).join('');
 $('factor-list').innerHTML=content||'<p class="empty">没有符合筛选条件的因子。</p>';
 $('factor-list').querySelectorAll('.factor-item').forEach(b=>b.onclick=()=>select(b.dataset.id));
 $('factor-list').querySelectorAll('summary').forEach(el=>el.onclick=e=>e.preventDefault());
 $('factor-list').querySelectorAll('.tree-title').forEach(b=>b.onclick=e=>{e.preventDefault();e.stopPropagation();selectScope(b.dataset.kind,b.dataset.key)});
 $('factor-list').querySelectorAll('details').forEach(el=>{const b=el.querySelector(':scope > summary .tree-toggle'),sync=()=>{b.setAttribute('aria-expanded',String(el.open));if(el.open)collapsed.delete(el.dataset.branch);else collapsed.add(el.dataset.branch)};b.setAttribute('aria-expanded',String(el.open));b.onclick=e=>{e.preventDefault();e.stopPropagation();el.open=!el.open;sync()};el.ontoggle=()=>{if(el.isConnected)sync()}});
}
function drawRanking(){const cs=ordered(),p=$('detail-period').value;let group='';
 $('ranking-description').textContent=pname(p)+' · '+cs.length+' 个方向因子 · '+(isFlat()?'不分组，按所选数值排序。':'保留研究逻辑和定义分组，Buy / Sell 相邻显示。')+' 表格、导航与下载共用筛选及排序。';
 $('download-summary').disabled=!cs.length;
 $('ranking').querySelector('tbody').innerHTML=cs.map(c=>{const g=logicFor(c),head=!isFlat()&&group!==g.id?'<tr class="ranking-group"><th colspan="9">'+g.title+'</th></tr>':'';group=g.id;const s=stat(c,p),a=stat(c,p,'pearson_ic'),d=spread(c,p);
  return head+'<tr data-column="'+c+'"><td><a href="#factor-'+c+'" data-factor="'+c+'">'+c+'</a><br><small>'+spec(c).title+'</small></td><td>'+sideName(spec(c).side)+'</td>'+[num(a.mean,6),num(s.mean,6),num(s.icir,3),num(s.nw_t,3),num(d.mean*10000,3),num(d.nw_t,3),s.valid_days].map(v=>'<td class="number">'+v+'</td>').join('')+'</tr>';
 }).join('');
 $('ranking').querySelectorAll('[data-factor]').forEach(a=>a.onclick=e=>{e.preventDefault();select(a.dataset.factor);$('scope-summary').scrollIntoView()});
}
$('download-summary').onclick=()=>{const p=$('detail-period').value;save(csv([['formal_column','side','period','IC','Rank_IC','ICIR','Rank_NW_t','G10_minus_G1_bps','spread_NW_t','valid_days'],...ordered().map(c=>[c,spec(c).side,p,stat(c,p,'pearson_ic').mean,stat(c,p).mean,stat(c,p).icir,stat(c,p).nw_t,spread(c,p).mean*10000,spread(c,p).nw_t,stat(c,p).valid_days])]),'depth-match-'+(viewMode==='all'?'all':direction)+'-'+p+'.csv')};
function showPane(k,focus=false,root=null){activePane=k;document.querySelectorAll('#detail-cards [data-pane]').forEach(b=>{const on=b.dataset.pane===k;b.setAttribute('aria-selected',String(on));b.tabIndex=on?0:-1});document.querySelectorAll('#detail-cards .detail-pane').forEach(p=>p.hidden=p.dataset.key!=='pane-'+k);if(focus&&root)root.querySelector('[data-pane="'+k+'"]').focus();updateURL()}
function imageSource(c,kind){const key=(['daily','monthly','groups'].includes(kind)?'figures/':'assets/')+c+'-'+kind+'.png';return FIGS[key]?'data:image/png;base64,'+FIGS[key]:BASE+key}
function figure(c,kind,caption){const src=imageSource(c,kind);return '<figure><button class="figure-button" data-image="'+src+'" data-file="'+c+'-'+kind+'.png" data-column="'+c+'" aria-label="放大 '+c+' '+kind+' 图"><img src="'+src+'" alt="'+c+' '+kind+'" loading="lazy"></button><figcaption>'+caption+'</figcaption></figure>'}
function openSVG(svg,name,title){if(zoomURL)URL.revokeObjectURL(zoomURL);zoomURL=URL.createObjectURL(new Blob([svg],{type:'image/svg+xml'}));openImage(zoomURL,name,title,'SVG')}
function openImage(src,name,title,type='PNG'){$('figure-image').src=src;$('figure-title').textContent=title;$('figure-download').href=src;$('figure-download').download=name;$('figure-download').textContent='下载 '+type;$('figure-dialog').showModal()}
document.addEventListener('click',e=>{const b=e.target.closest('[data-image],[data-svg-zoom]');if(!b)return;if(b.hasAttribute('data-image'))openImage(b.dataset.image,b.dataset.file,b.dataset.column);else openSVG(b.querySelector('svg').outerHTML,b.dataset.file,b.dataset.title)});
$('figure-close').onclick=()=>$('figure-dialog').close();$('figure-dialog').onclick=e=>{if(e.target===$('figure-dialog'))$('figure-dialog').close()};$('figure-dialog').addEventListener('close',()=>{if(zoomURL){URL.revokeObjectURL(zoomURL);zoomURL=null}});
function overviewSVG(side){const cs=cols.filter(c=>spec(c).side===side),max=Math.max(...cols.map(c=>Math.abs(stat(c,'full').mean)))*1.18,w=620,h=548,l=210,r=78,t=38,mid=l+(w-l-r)/2,scale=(w-l-r)/2/max;
 let s='<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 '+w+' '+h+'" role="img" aria-label="'+sideName(side)+' 全期 Rank IC" data-axis-max="'+max+'" style="font-family:Microsoft YaHei,sans-serif;background:white"><rect width="100%" height="100%" fill="white"/>';
 [-max,-max/2,0,max/2,max].forEach(v=>{const x=mid+v*scale;s+='<line x1="'+x+'" x2="'+x+'" y1="20" y2="502" stroke="'+(v===0?'#61716f':'#e4e8e2')+'"/><text x="'+x+'" y="525" text-anchor="middle" font-size="11" fill="#61716f">'+num(v,3)+'</text>'});
 cs.forEach((c,i)=>{const v=stat(c,'full').mean,y=t+i*38,x=mid+v*scale;s+='<text x="198" y="'+(y+14)+'" text-anchor="end" font-size="12" fill="#243648">'+spec(c).name.slice(0,4)+' · '+spec(c).title+'</text><rect data-column="'+c+'" x="'+Math.min(mid,x)+'" y="'+y+'" width="'+Math.abs(v*scale)+'" height="20" fill="'+(v>=0?'#087b78':'#b24f35')+'"><title>'+c+': '+v+'</title></rect><text x="'+(w-8)+'" y="'+(y+14)+'" text-anchor="'+'end'+'" font-size="11" fill="#243648">'+num(v,5)+'</text>'});return s+'</svg>';
}
function drawOverview(){const sides=viewMode==='all'?['buy','sell']:[direction];drawComparisonTables(cols.filter(c=>sides.includes(spec(c).side)));$('overview-plot').classList.toggle('single',sides.length===1);$('overview-plot').innerHTML=sides.map(side=>'<figure data-side="'+side+'"><h3>'+sideName(side)+'</h3><button class="figure-button" data-svg-zoom data-file="depth-match-'+side+'-full-rank-ic.svg" data-title="'+sideName(side)+' · 全部 601 日">'+overviewSVG(side)+'</button></figure>').join('')}
function drawDetails(){const cs=scopeColumns();dailyRefresh.clear();$('detail-cards').replaceChildren();
 const title=selection.kind==='leaf'?selected:selection.kind==='definition'?(specs.find(s=>s.name===selection.key)?.title||selection.key):(LOGICS.find(g=>g.id===selection.key)?.title||selection.key);
 $('scope-summary').innerHTML='<h3>'+esc(title)+'</h3><p>'+pname($('detail-period').value)+' · 当前范围 '+cs.length+' 个方向因子</p>'+(selectionNotice?'<p>'+selectionNotice+'</p>':'')+(cs.length?'<p class="small">上方指标和分组诊断使用所选区间；日度图、月度图、分布与 OLS 使用全部 601 日。选择定义可对照 Buy / Sell；标签页和明细日期同步。</p>':'<p>没有符合筛选条件的因子。可调整筛选或清空筛选。</p>');
 [...new Set(cs.map(c=>spec(c).name))].forEach(name=>{const pair=cs.filter(c=>spec(c).name===name),wrap=document.createElement('div');wrap.className='detail-pair'+(pair.length===1?' single':'');$('detail-cards').append(wrap);
  pair.forEach(c=>{const root=document.createElement('article');root.className='detail';root.dataset.column=c;root.dataset.side=spec(c).side;root.innerHTML='<div class="eyebrow" data-key="detail-id"></div><h3 data-key="detail-title"></h3><div class="detail-tabs" role="tablist" aria-label="'+c+' 详情"></div><div class="scope-badge">评价区间：'+pname($('detail-period').value)+'</div><div class="detail-metrics" data-key="detail-metrics"></div><p class="small" data-key="detail-coverage"></p><div data-key="panes"></div>';wrap.append(root);renderDetail(root,c)});
 });showPane(activePane);
}
function refresh(){ensureSelection();document.querySelectorAll('.view-mode-select').forEach(e=>e.value=viewMode);document.querySelectorAll('.direction-select').forEach(e=>e.value=direction);document.querySelectorAll('.side-control').forEach(e=>e.hidden=viewMode==='all');drawRanking();drawList();drawDetails();drawOverview();updateURL()}
['factor-search','family-filter','logic-filter','factor-sort','factor-arrangement'].forEach(id=>$(id).addEventListener(id==='factor-search'?'input':'change',()=>{if(id==='factor-arrangement'&&isFlat()&&$('factor-sort').value==='id')$('factor-sort').value='ic';refresh()}));
$('detail-period').onchange=()=>{resetDateRange();refresh()};$('reset-filters').onclick=()=>{['factor-search','family-filter','logic-filter'].forEach(id=>$(id).value='');refresh()};
$('expand-tree').onclick=()=>{collapsed.clear();drawList()};$('collapse-tree').onclick=()=>{LOGICS.forEach(g=>collapsed.add('logic-'+g.id));drawList()};
document.addEventListener('change',e=>{if(e.target.matches('.view-mode-select')){viewMode=e.target.value;refresh()}if(e.target.matches('.direction-select')){direction=e.target.value;if(selection.kind==='leaf'){selected=spec(selected).name+'_'+direction;selection.key=selected}refresh()}});
function bars(gs,kind,disp){
const mean=kind==='mean',w=mean?820:540,h=mean?370:360,l=65,r=22,t=42,b=60,mus=gs.map(g=>g.mean*10000),errs=gs.map((g,i)=>kind==='within'?disp[i].typical_within_std*10000:kind==='nw'?1.96*g.nw_se*10000:0),color=kind==='within'?'#087b78':'#b24f35';let lo=Math.min(0,...mus.map((v,i)=>v-errs[i])),hi=Math.max(0,...mus.map((v,i)=>v+errs[i])),pad=Math.max((hi-lo)*.17,.1);lo-=pad;hi+=pad;const y=v=>t+(hi-v)/(hi-lo)*(h-t-b),bw=(w-l-r)/10,x=i=>l+(i+.5)*bw;
let s='<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 '+w+' '+h+'" role="img" aria-label="十分组收益" style="font-family:Microsoft YaHei,sans-serif;background:white"><rect width="100%" height="100%" fill="white"/><text x="'+l+'" y="22" font-size="13" fill="#61716f">日均毛收益（bp）</text>';
for(let j=0;j<=4;j++){const v=lo+(hi-lo)*j/4;s+='<line x1="'+l+'" x2="'+(w-r)+'" y1="'+y(v)+'" y2="'+y(v)+'" stroke="#e4e8e2"/><text x="'+(l-10)+'" y="'+(y(v)+4)+'" text-anchor="end" font-size="12" fill="#61716f">'+num(v,1)+'</text>'}
s+='<line x1="'+l+'" x2="'+(w-r)+'" y1="'+y(0)+'" y2="'+y(0)+'" stroke="#61716f"/>';
if(!mean)s+='<polyline points="'+mus.map((v,i)=>x(i)+','+y(v)).join(' ')+'" fill="none" stroke="'+color+'" stroke-width="1.3"/>';
mus.forEach((v,i)=>{const xx=x(i),yy=y(v),c=v>=0?'#087b78':'#b24f35',a=y(v+errs[i]),z=y(v-errs[i]);if(mean){s+='<rect x="'+(xx-bw*.32)+'" y="'+Math.min(yy,y(0))+'" width="'+bw*.64+'" height="'+Math.max(.5,Math.abs(yy-y(0)))+'" fill="'+c+'"><title>G'+(i+1)+': '+num(v,5)+'bp</title></rect><text x="'+xx+'" y="'+(v>=0?yy-8:yy+19)+'" text-anchor="middle" font-size="12" fill="#243648">'+num(v,2)+'</text>'}else{s+='<g><title>G'+(i+1)+'：均值 '+num(v,5)+'bp；误差棒半宽 '+num(errs[i],5)+'bp</title><line x1="'+xx+'" x2="'+xx+'" y1="'+a+'" y2="'+z+'" stroke="'+color+'" stroke-width="1.5"/><path d="M '+(xx-5)+' '+a+' H '+(xx+5)+' M '+(xx-5)+' '+z+' H '+(xx+5)+'" stroke="'+color+'" stroke-width="1.5"/><circle cx="'+xx+'" cy="'+yy+'" r="3.6" fill="'+color+'"/></g>'}s+='<text x="'+xx+'" y="'+(h-b+25)+'" text-anchor="middle" font-size="13" fill="#243648">G'+(i+1)+'</text>'});return s+'<text x="'+w/2+'" y="'+(h-8)+'" text-anchor="middle" font-size="12" fill="#61716f">因子原值由低到高 → · 未计成本</text></svg>'}


/* DETAIL */
function renderDetail(root,c){const $=id=>id==='detail-period'?document.getElementById(id):root.querySelector('[data-key="'+id+'"]');
root.querySelector('.detail-tabs').innerHTML=tabs.map(([k,t],i)=>'<button role="tab" id="tab-'+k+'" aria-controls="pane-'+k+'" aria-selected="'+(k===activePane)+'" tabindex="'+(k===activePane?0:-1)+'" data-pane="'+k+'">'+t+'</button>').join('');
const p=$('detail-period').value,s=stat(c,p),a=stat(c,p,'pearson_ic'),g=spread(c,p),o=D.ols[c],d=D.distribution[c],gs=D.decile_summary.filter(r=>r.formal_column===c&&r.period===p).sort((a,b)=>a.group-b.group),diag=D.group_diagnostics.filter(r=>r.formal_column===c&&r.period===p).sort((a,b)=>a.group-b.group),disp=D.group_dispersion.filter(r=>r.formal_column===c&&r.period===p).sort((a,b)=>a.group-b.group);
$('detail-id').textContent=c+' / '+(spec(c).side==='buy'?'买侧':'卖侧');$('detail-title').textContent=spec(c).title;
$('detail-metrics').innerHTML=[['IC',num(a.mean,6)],['Rank IC',num(s.mean,6)],['ICIR · 不年化',num(s.icir,4)],['Rank IC · NW t',num(s.nw_t,3)],['G10−G1 · bp',num(g.mean*10000,3)],['组差 · NW t',num(g.nw_t,3)]].map(([k,v])=>'<div class="metric"><b>'+v+'</b><span>'+k+'</span></div>').join('');
$('detail-coverage').textContent=pname(p)+'：'+s.valid_days+' 个有效 IC 日，成对样本 '+comma(s.effective_stock_days)+' 股票日。全期原值有限 '+comma(d.finite_count)+'，缺失 '+comma(d.nan_count)+'，恰为零 '+comma(d.zero_count)+'。';
let panes={daily:'<h4>日度相关与累计轨迹 · 全部 601 日</h4>'+figure(c,'daily','每日 IC、Rank IC、20 日滚动均值与累计和。累计 IC 是相关系数之和，不是资金净值；区间选择不裁剪静态图。')+'<h4>日度明细</h4><div class="controls date-controls"><label>起始日期<input id="date-start" type="date" value="'+dateRange.start+'"></label><label>结束日期<input id="date-end" type="date" value="'+dateRange.end+'"></label><button id="download-daily">下载筛选后日度 CSV</button><span id="daily-count" class="small"></span></div><p class="small">明细日期在当前显示的因子间同步，只筛选下表与日度 CSV，不改变上方图或评价指标。累计列保留从全历史起点开始的累计值，不在筛选起点重新归零。</p><div id="daily-table" class="table-scroll daily-table"></div>',monthly:'<h4>全部 601 日 · 30 个月的相关表现</h4>'+figure(c,'monthly','固定展示全历史月度结果；图中颜色与统计显著性无关。'),groups:'<h4>'+pname(p)+' · 十分组毛收益（bp）</h4><div class="groups-wrap">'+bars(gs,'mean',disp)+'</div><p>G10−G1 = '+num(g.mean*10000,3)+'bp；配对 95% NW 区间 ['+num(g.ci_low*10000,3)+', '+num(g.ci_high*10000,3)+']bp。先按日计算再对有效日等权，毛收益包含市场共同波动，未计成本。</p><div class="two"><div><h4>均值 ± 典型日内组内标准差</h4><div class="groups-wrap">'+bars(gs,'within',disp)+'</div></div><div><h4>均值 ± 1.96 × NW 标准误</h4><div class="groups-wrap">'+bars(gs,'nw',disp)+'</div></div></div><p class="small">左图表示组内个股收益离散尺度，不是均值置信区间；右图用组日均收益时间序列计算 lag=1 NW 近似区间。两图尺度不同，均未作多重比较校正。</p><div class="table-scroll">'+table(['组','日均 bp','收益百分位 %','日内中位数 bp','缩尾均值 bp','尾部贡献 bp','有效日','股票日'],gs.map((v,i)=>['G'+v.group,num(v.mean*10000,3),num(diag[i].return_percentile*100,3),num(diag[i].median_return*10000,3),num(diag[i].winsorized_mean*10000,3),num(diag[i].tail_contribution*10000,3),v.valid_days,comma(v.stock_days)]))+'</div><p class="small">分组保持原样。收益平均秩百分位、中位数和缩尾均值均先按日统计，再对有效日等权；缩尾阈值为每日成对样本 P1/P99，尾部贡献为原均值减缩尾均值。</p><button id="download-groups">下载所选区间完整分组诊断 CSV</button><details><summary>查看全期原始分组图</summary>'+figure(c,'groups','正式报告的全历史分组图；所选分期数据见上方动态统计。')+'</details>',scatter:'<h4>因子原值与同日收益 · 全部 601 日</h4><p class="fit-equation">收益（bp） = '+num(o.alpha*10000,6)+(o.beta>=0?' + ':' − ')+num(Math.abs(o.beta)*10000,6)+' × 因子原值</p><p>拟合 '+comma(o.n)+' 股票日；R²='+num(o.r_squared,8)+'，汇集 Pearson r='+num(o.pooled_r,6)+'，RMSE='+num(o.rmse*10000,3)+'bp。</p>'+figure(c,'scatter','全范围与放大图均传入全部 '+comma(o.n)+' 个真实成对样本。放大只改变坐标范围；OLS 使用同一完整样本，不抽样、不截尾。')+'<p>模型包含截距、每个股票日等权。汇集相关与日均横截面 IC 口径不同；日期及股票重复带来依赖，这里不报告假设观测独立的 OLS t 或 p。区间选择不改变全期拟合。</p><button id="download-ols">下载此因子 OLS JSON</button>',distribution:'<h4>因子原值分布 · 全部 601 日</h4>'+figure(c,'distribution','正式全期原值分布图；缺失值不填零。')+'<div class="table-scroll">'+table(['统计','值'],[['有限数',comma(d.finite_count)],['缺失数',comma(d.nan_count)],['零值数',comma(d.zero_count)],['均值',num(d.mean,8)],['标准差',num(d.std,8)],...Object.entries(d.quantiles).map(([k,v])=>['分位 '+k,num(v,8)])])+'</div>',definition:'<h4>正式列名</h4><code>'+c+'</code><p>'+notes[Math.floor(cols.indexOf(c)/2)]+'</p><div class="formula">'+mathFor(c)+'</div><p class="small">'+(definitionNumber(c)===12?'这是日度因子，已包含 C/N；不再除以 N。':'这是单笔已观察订单得分，按该侧日内求和后除以双边订单总数 N。')+'</p><details><summary>原始登记表达式</summary><code>'+esc(spec(c).formula)+'</code></details><div class="formula">'+MATH.IC+'</div><p>窗口 [09:30, 09:35)，共同分母为全部有效双边新订单。买卖分别统计；所有有限值保持 [0,1] 的原始方向。未知状态的处理及符号定义见报告第 02 节。</p><p class="definition-symbols">A：允许触及第一档；R₂：允许第二档；B₁：价格封顶第一档；E：初始主动撮合结束并确认仅吃完原第一档；prev：同股同向最近的可主动成交前单；lag：严格早于提交前 1 秒的合法盘口。𝟙 为指示函数，unknown 按第 02 节规则处理。</p><h4>独立复算</h4><p>全部 601 个因子日独立复算通过，计数、分组及 NaN 模式一致。全批次相关最大误差 3.89×10⁻¹⁶，小于 atol=10⁻¹²、rtol=10⁻¹⁰ 的验收阈值。</p><a href="'+BASE+'notebooks/'+c+'.ipynb" download>下载此因子的已执行 notebook</a>'};
$('panes').innerHTML=tabs.map(([k,t])=>'<div class="detail-pane" id="pane-'+k+'" role="tabpanel" aria-labelledby="tab-'+k+'" '+(k===activePane?'':'hidden')+'>'+panes[k]+'</div>').join('');
root.querySelectorAll('[id]').forEach(el=>{el.dataset.key=el.id;el.id=c+'-'+el.id});
root.querySelectorAll('[aria-controls],[aria-labelledby]').forEach(el=>['aria-controls','aria-labelledby'].forEach(attr=>{if(el.hasAttribute(attr))el.setAttribute(attr,c+'-'+el.getAttribute(attr))}));
const tabButtons=[...root.querySelectorAll('[data-pane]')];tabButtons.forEach((b,i)=>{b.onclick=()=>showPane(b.dataset.pane);b.onkeydown=e=>{const j=e.key==='ArrowRight'?(i+1)%tabs.length:e.key==='ArrowLeft'?(i+tabs.length-1)%tabs.length:e.key==='Home'?0:e.key==='End'?tabs.length-1:null;if(j!==null){e.preventDefault();showPane(tabButtons[j].dataset.pane,true,root)}}});
root.querySelectorAll('.groups-wrap').forEach((el,i)=>{el.tabIndex=0;el.setAttribute('role','button');el.setAttribute('aria-label','放大 '+c+' 分组图');el.dataset.svgZoom='';el.dataset.file=c+'-'+p+'-'+['groups','within-dispersion','nw-interval'][i]+'.svg';el.dataset.title=c+' / '+pname(p);el.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();el.click()}}});
$('download-ols').onclick=()=>save(JSON.stringify({formal_column:c,side:spec(c).side,period:'full',...o},null,2),c+'-full-ols.json','application/json');
function dailyRows(){return D.daily_ic.filter(r=>r.formal_column===c&&(!dateRange.start||r.date>=dateRange.start)&&(!dateRange.end||r.date<=dateRange.end))}
function drawDaily(){ $('date-start').value=dateRange.start;$('date-end').value=dateRange.end;const rs=dailyRows(),invalid=dateRange.start&&dateRange.end&&dateRange.start>dateRange.end;$('daily-count').textContent=invalid?'起始日期晚于结束日期，请调整。':rs.length+' 日 · 累计值沿用全历史';$('download-daily').disabled=!rs.length;
$('daily-table').innerHTML=table(['日期','成对数','IC','Rank IC','全历史累计 IC','全历史累计 Rank IC'],rs.map(r=>[r.date,comma(r.n),num(r.pearson_ic,6),num(r.rank_ic,6),num(r.pearson_ic_cumulative,5),num(r.rank_ic_cumulative,5)]));
}
dailyRefresh.set(c,drawDaily);['date-start','date-end'].forEach(id=>$(id).onchange=()=>{dateRange={start:$('date-start').value,end:$('date-end').value};dailyRefresh.forEach(fn=>fn());updateURL()});drawDaily();
$('download-daily').onclick=()=>{const rs=dailyRows(),ks=Object.keys(D.daily_ic[0]);save(csv([ks,...rs.map(r=>ks.map(k=>r[k]))]),c+'-'+(dateRange.start||'start')+'-'+(dateRange.end||'end')+'-daily.csv')};
$('download-groups').onclick=()=>save(csv([['formal_column','period','group','mean_return','nw_se','ci_low','ci_high','typical_within_std','return_percentile','median_return','winsorized_mean','tail_contribution','valid_days','stock_days'],...gs.map((v,i)=>[c,p,v.group,v.mean,v.nw_se,v.ci_low,v.ci_high,disp[i].typical_within_std,diag[i].return_percentile,diag[i].median_return,diag[i].winsorized_mean,diag[i].tail_contribution,v.valid_days,v.stock_days])]),c+'-'+p+'-groups.csv');
}

function hashSelect(){const c=location.hash.replace('#factor-','');if(cols.includes(c)){select(c);$('scope-summary').scrollIntoView()}}
window.addEventListener('hashchange',hashSelect);
for(const [id,prefix] of [['evaluation-files','evaluation/'],['notebook-files','notebooks/'],['evidence-files','evidence/']]){$(id).innerHTML=D.files.filter(f=>f.startsWith(prefix)&&!(id==='evidence-files'&&f.includes('/notebooks/'))).map(f=>'<a download href="'+BASE+f+'">'+esc(f.slice(prefix.length))+'</a>').join('')}
$('seal-info').textContent='RUN_ROOT: /home/wangly/hdd-store/outputs/sirui/published/open5m-depth-match/20260908T100452Z-full-history-i01-147ab55\n'+JSON.stringify(D.seal,null,2);
refresh();
