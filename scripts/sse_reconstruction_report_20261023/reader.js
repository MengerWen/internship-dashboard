const cases = [
  ['600 + 400','一笔订单怎样变成多条消息',1,'先成交、后挂出时，成交与余量属于同一个订单。'],
  ['只看到成交','为什么原始属性没有唯一答案',2,'同一组公开成交记录，可以兼容不同原始价格、类型和未公开余量。'],
  ['先匹配还是先删','公开定义怎样影响匹配和 union',4,'候选集的变化会改变配对结果，不能只在最后修改贡献值。'],
  ['113500 为什么变 0','用真实盘口判断谁违反了定义',7,'在动作前盘口中，按公开价格独立核对该价位的同侧数量。'],
  ['472 项旧参考差异','怎样确认深市默认没有被误伤',7,'先更新参考身份，再区分定义变更与适配器回归。'],
  ['序号 10 变成 6','换时钟为什么会改变因子',8,'顺序和价格数量不变，序号间隔仍会进入衰减核与窗口。']
];
const relatedCases = [[0,1],[0],[1],[0,3],[2],[3],[4,5],[3,4],[5],[5],[4,5]];

function sceneMarkup(i) {
  const s = scenes[i];
  return `<header class="scene-head"><div class="copy"><h1 tabindex="-1">${s[1]}</h1><p class="lead">${s[2]}</p></div><div class="page-count">${String(i+1).padStart(2,'0')} / 11</div></header>
    <div class="case-shortcuts"><span>用案例理解</span>${relatedCases[i].map(n=>btn('case-link',n,cases[n][0])).join('')}</div>
    <div class="scene-body">${renderers[i]()}</div>
    <div class="scene-caption"><b>这一步的作用</b><p>${s[4]}</p></div>`;
}

function deck() {
  app.innerHTML = `<div class="deck"><nav class="chapter-nav" aria-label="汇报章节"><p>全景 → 机制 → 证据 → 交接</p>${scenes.map((s,i)=>`<button type="button" data-action="scene" data-value="${i}" ${state.scene===i?'aria-current="step"':''}><span>${String(i+1).padStart(2,'0')}</span><span>${s[0]}</span></button>`).join('')}</nav>
    <article class="page-shell">${sceneMarkup(state.scene)}<footer class="page-footer">${detailButton(scenes[state.scene][3],'本页技术与证据')}<div class="pager"><button class="secondary" data-action="page" data-value="-1" ${state.scene===0?'disabled':''}>← 上一页</button><button class="primary" data-action="page" data-value="1" ${state.scene===10?'disabled':''}>下一页 →</button></div><span class="fine">支持 ← → 翻页</span></footer></article></div>`;
  const nav = document.querySelector('.chapter-nav');
  const current = nav.querySelector('[aria-current]');
  if (nav.scrollWidth > nav.clientWidth) nav.scrollLeft = Math.max(0,current.offsetLeft-nav.offsetLeft-15);
}

function regressionDiagram() {
  return `<div class="split"><div class="visual"><h3>参考过期，会把定义变更误报成回归</h3><div class="regression-row"><span>旧参考 · 5 × 344 列</span><strong>472 / 1,720 不等</strong><div class="regression-track"><i style="width:27.44186%"></i></div></div><div class="regression-row"><span>r2 / v5 新参考 · 每轮 5 × 352 列</span><strong>修正前：0 / 1,760</strong><strong>修正后：0 / 1,760</strong></div><p class="fine">每轮对两份参考；两轮合计 7,040 次逐位比较。旧、新列集合不同，不能把 1,720 和 1,760 混成一个分母。</p></div><div class="visual"><h3>旧差异逐项归属</h3><div class="metric-line"><div><b>472</b><span>落在三项决定影响范围</span></div><div><b>0</b><span>落在影响范围外</span></div></div><p>涉及 124 个不同列身份，均属于“排队稀释只计挂出余量”及其传播范围。其他两项决定不是这 472 项的来源。</p><p class="fine">r2 / v5 的生成提交与数值逻辑分别核对；ec7d8c0c 是消费者登记补齐，不能误写成 DM 分母的数值实现。</p></div></div><div class="visual" style="margin-top:20px"><h3>五只股票，各 352 列</h3><div class="regression-stocks">${['000725','300750','000001','000333','300577'].map(s=>`<div><b>${s}</b><span>修正前：0 / 0</span><span>修正后：0 / 0</span></div>`).join('')}</div><p class="fine">每组“0 / 0”分别为对 r2 / v5 的不等项数。深市逻辑没有为追平旧参考而修改。</p></div>`;
}

function caseDiagram(i) {
  if (i===2) return matchingDiagram();
  if (i===4) return regressionDiagram();
  return renderers[cases[i][2]]();
}

function laboratory() {
  const c=cases[state.case];
  app.innerHTML = `<article class="lab"><header class="lab-header"><div><h1 tabindex="-1">六个案例，讲清关键判断</h1><p>消息机制、真实差异和误差统计分别标注；每个案例都能回到对应主线。</p></div><button class="secondary" data-action="return-story">返回分页主线</button></header><div class="case-layout"><nav class="case-list" aria-label="六个案例">${cases.map((c,i)=>btn('case',i,`<b>${c[0]}</b><small>${c[1]}</small>`,state.case===i)).join('')}</nav><section class="case-stage"><header class="case-head"><div><h2 tabindex="-1">${c[1]}</h2><p>${c[3]}</p></div><span class="tag ${state.case===3||state.case===4?'real':''}">${state.case===3?'真实盘口样本':state.case===4?'实测回归':'机制图解'}</span></header>${caseDiagram(state.case)}<div class="case-role"><b>这个案例在项目中的作用</b>${scenes[c[2]][4]}</div><div class="controls"><button class="primary" data-action="scene" data-value="${c[2]}">回到主线第 ${c[2]+1} 页</button>${detailButton(scenes[c[2]][3],'案例依据与技术细节')}</div></section></div></article>`;
}

function render() {
  if (state.view==='cases') laboratory(); else deck();
  document.querySelectorAll('[data-action="view"]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.value===state.view)));
  document.getElementById('reading-state').textContent=state.view==='cases'?`案例 ${state.case+1} / 6：${cases[state.case][0]}`:`主线 ${state.scene+1} / 11：${scenes[state.scene][0]}`;
}

function normalizeEvidenceLinks() {
  const body=document.getElementById('evidence-body');
  const links=[...body.querySelectorAll('a[href^="https://"]')];
  if (!links.length) return;
  const refs=document.createElement('details');
  refs.className='reference-addresses';
  refs.innerHTML='<summary>原始引用地址（可选中复制）</summary><p class="fine">引用固定到报告版本；访问需要研究仓库权限。</p>';
  for (const a of links) {
    const row=document.createElement('p'), label=document.createElement('b'), address=document.createElement('input');
    label.textContent=a.textContent; address.readOnly=true; address.value=a.href;
    address.setAttribute('aria-label',a.textContent+' 原始地址');
    row.append(label,address);refs.append(row);
    if (window.self!==window.top) {
      const span=document.createElement('span');span.className='reference-name';span.textContent=a.textContent;a.replaceWith(span);
    } else {a.target='_blank';a.rel='noopener noreferrer';}
  }
  body.append(refs);
}

function openDialog(title,body) {
  document.getElementById('evidence-title').textContent=title;
  document.getElementById('evidence-body').innerHTML=body;
  normalizeEvidenceLinks();
  if (!dialog.open) dialog.showModal();
  dialog.scrollTop=0;
}

function evidence(key) {
  if (key&&DATA.source[key]) {const s=DATA.source[key];openDialog(s.title,s.body);}
  else openDialog('技术细节、限制与证据',`<p>按主题核对完整定义、样本范围、参数口径与固定版本报告。这里的业务状态截至 2026-10-23。</p>${Object.entries(DATA.source).map(([k,s])=>`<details><summary>${s.title}</summary>${s.body}</details>`).join('')}<details><summary>本页引用的数据身份</summary><p>报告版本：<code>${esc(DATA.provenance.revision)}</code></p>${Object.values(DATA.provenance.inputs).map(v=>`<p><code>${esc(v.path)}</code><br>SHA-256：<code>${esc(v.sha256)}</code></p>`).join('')}</details>`);
}

function glossary() {
  const terms=[
    ['委托 / 消息','委托是一次交易指令；消息是交易所公开发布的一次效果。同一委托可能对应多条成交和一条剩余挂单。'],
    ['A / T / D（C）','A 为公开挂单；T 为成交；D 或 C 在不同输入命名中表示撤单。具体撤单性质还须由事实和规则判定。'],
    ['盘口 / 回放','盘口记录买卖各价位的在簿量；回放按消息顺序重建这些状态。状态对上，仍不代表隐藏原始属性已知。'],
    ['Qᵥ / t₀','Qᵥ 为初始可见成交量加剩余挂出量；t₀ 为首次公开效果的位置，不是未知原始报单时刻的证明。'],
    ['前态 / 后态','同一动作发生前、更新后的订单与盘口状态；计算反应和排队时不能混用。'],
    ['FactorInput','因子引擎的统一接口，包含事件、生命周期、动作前态与动作后态。'],
    ['px / act','公开成交追价的两种口径：px 跟踪公开执行价变化；act 跟踪实际可成交性变化。'],
    ['union','合并多个行为族的订单候选分数，再归约为股票因子；它不是已校准的算法交易概率。'],
    ['时钟 / Q_equity','这里的消息时钟是衡量消息间距的序号，不等同于秒数。Q_equity 从整条通道的可见权益消息建立，不按单股压缩。'],
    ['θ / 结构门限','θ 决定距离多大时权重衰减；结构门限决定哪些链路、匹配和行为候选可纳入。参数需要独立沪市样本。'],
    ['S / H','S 为深市真值直接改写成公开口径的参照；H 将同一真值转成沪市消息形态后，经沪市适配器恢复。'],
    ['逐位一致','有限浮点按位模式比较；双方 NaN 视为相等。它比“误差很小”更严格，范围仍限定于对应样本和列。'],
    ['W5 / 签收','W5 指开盘后 09:30–09:35 的五分钟窗口。签收指特定版本、输入与范围通过验收，不自动覆盖全历史。'],
    ['交易时段冻结','公司计算任务在规定交易时段暂停，属于资源运行约束；它与因子里的消息时钟是两件事。']
  ];
  openDialog('术语短解',`<div class="glossary">${terms.map(([name,desc])=>`<div><h3>${name}</h3><p>${desc}</p></div>`).join('')}</div>`);
}

function whitelist() {
  openDialog('白名单允许什么变化，证据覆盖什么',`<p>白名单只豁免已证明不影响本次固定 352 列输出的表示变化；不能据此称这些信息从来不被读取。</p><div class="table-wrap"><table><thead><tr><th>项目</th><th>允许变化</th><th>证明与边界</th></tr></thead><tbody><tr><td>received_ts</td><td>接收时间按性质平移</td><td>静态读点清单 + 10 股双版本扰动</td></tr><tr><td>vendor_aggressor_side_raw</td><td>原始供应商标签设 NA / 随机字符串</td><td>公开计算所用主动性另由事实计算</td></tr><tr><td>event_pos</td><td>保持顺序，并在四表中一致插入间隔、改号</td><td>引擎确实读取排序；任意置乱不在白名单</td></tr><tr><td>7 个精确 attrs 键</td><td>替换来源标记取值</td><td>不将 attrs 整体豁免</td></tr></tbody></table></div><p><code>szse_replay_version<br>szse_replay_fix_a<br>szse_replay_fix_c<br>replay_options<br>order_event_semantics<br>original_submissions_established<br>legal_unrested_trade_legs</code></p><p>静态清单 368 条命中。10 只高 / 中 / 低活跃样本 × 10 项 × px / act = 200 次有效扰动，累计 70,400 个值逐位不变。科学序号 seq、C2 修正字段不在白名单。</p>${DATA.source.evidence.body}`);
}

function mechanism(column) {
  const key=Object.keys(DATA.mechanisms).find(k=>column.startsWith(k+'__'));
  return key?DATA.mechanisms[key]:'【推测】序号距离进入衰减或候选窗口，具体贡献仍需沿依赖链逐项归因。';
}

function worst() {
  openDialog('p99 稳健尺度误差最大的 20 列',`<p>全市场实测汇总。误差以 S 的截面稳健尺度为分母，统计包含零误差股票；机制沿用验收报告的【事实】与【推测】标记。</p><div class="table-wrap"><table><thead><tr><th>列</th><th>受影响</th><th>p99 / 尺度</th><th>最大 / 尺度</th><th>ρ</th><th>机制</th></tr></thead><tbody>${sortedErrors.slice(0,20).map(r=>`<tr><td>${short(r.column)}</td><td>${pct(r.affected_fraction,2)}</td><td>${num(r.scaled_p99)}</td><td>${num(r.scaled_max)}</td><td>${r.spearman.toFixed(9)}</td><td>${mechanism(r.column)}</td></tr>`).join('')}</tbody></table></div><p class="fine">【事实】确认序号进入计算的路径；没有把每一个个股误差分解为独立因果贡献。【推测】列尚未进行根成员或参数消融。</p>`);
}

function zeroScales() {
  openDialog('6 个零尺度列',`<p>以下方向结构零列均逐位不变。尺度比值和 Spearman 未定义，保留“未定义”，不填造 0 或 1。</p><div class="table-wrap"><table><thead><tr><th>列</th><th>变化股票数</th><th>尺度 / ρ</th></tr></thead><tbody>${DATA.errors.filter(r=>r.zero_scale).map(r=>`<tr><td>${short(r.column)}</td><td>${r.changed}</td><td>未定义</td></tr>`).join('')}</tbody></table></div>`);
}

function rankDistribution() {
  openDialog('346 列 Spearman 秩相关分布',`<div class="table-wrap"><table><thead><tr><th>分位</th><th>ρ(H, S)</th></tr></thead><tbody>${[['最小','0.999934547509'],['p01','0.999976194649'],['p25','0.999998068846'],['中位数','0.999999657498'],['p75','0.999999944203'],['p99','1.000000000000'],['最大','1.000000000000']].map(r=>`<tr><td>${r[0]}</td><td>${r[1]}</td></tr>`).join('')}</tbody></table></div><p>按全部有限股票配对计算，使用平均并列秩。另 6 个方向结构零列不变，秩相关未定义。这个分布描述排序稳定程度，不代替误差接受决定或预测效果评价。</p>`);
}

function performance() {
  openDialog('计时边界、运行版本与存储限制',DATA.source.status.body+`<h3>000725 与全市场的计时范围</h3><p>000725 输入构造 111.411 秒；五次引擎调用各约 319–385 秒，含比较、归约和回收的单股完整阶段 1,915.664 秒。它已先单独跑完，不能把预算截断当作验收通过。</p><p>主 guard 有效墙钟 3,340.953 秒，实际墙钟 6,040.937 秒，其中冻结约 2,699.983 秒。其余 2,887 股阶段平均 15.967 核；15 次 guard 的有效墙钟合计 91.56 分钟。</p><div class="table-wrap"><table><thead><tr><th>历史业务环节</th><th>状态与版本</th></tr></thead><tbody><tr><td>本地提交</td><td>C2(a) 2ecaa8f4、C2(b) e07e0d6d、C2(c) cca9a6ef 分别提交；归因标签校正为 21520d85，不改数值逻辑。</td></tr><tr><td>GitHub 推送</td><td>研究代码进入 origin/main，原记录核对到 21520d85；报告与证据定稿为 2a0dac94。</td></tr><tr><td>wenjie 同步</td><td>主任务前快进 f6592c06；退出后快进 8de2ca87 运行补充归约。</td></tr><tr><td>业务运行</td><td>C4/C5 在 f6592c06，act 对 v5 及最终归约在 8de2ca87；15 次 guard 均退出 0。</td></tr></tbody></table></div><p>业务运行版本和文档版本各自保留。这里没有重新探测服务器、读取真实沪市输入或重跑因子。</p>`);
}

function calibrationIllustration() {
  if(state.calibration===1) return `<div class="kernel-map">${[['时间','wall_seconds','两个动作间隔多少秒'],['消息','events','两端序号之间相隔多少'],['数量','qty','委托和动作的数量尺度'],['价格','price_ticks','执行 / 报价相差多少 tick'],['最优报价','bbo_ticks','相对本侧 / 对侧 BBO 的距离'],['可成交性','marketability_ticks','相对对手报价的可成交距离']].map(r=>`<div><b>${r[0]}</b><code>${r[1]}</code><span>${r[2]}</span></div>`).join('')}</div><p class="fine">这些框说明需要估计的距离维度，不展示尚未签收的沪市 θ 数值。六核决定“多近算相近”，结构参数继续决定“哪些关系计入、怎样匹配”。</p>`;
  if(state.calibration===2) return `<div class="handoff-flow"><span>结构观测</span>→<span>episode 分段</span>→<span>anchor 选择</span>→<span>cost / match</span>→<span>门限归约</span></div><p class="fine">上游门限改变后，不能沿用依赖旧门限的阶段缓存。九组完整统计规则可在本页“技术与证据”展开；f85、z12 不除 ln(2)，与六核和 f16 区分。</p>`;
  return '';
}

function updateLocation() {
  const hash=state.view==='cases'?`#view=cases&case=${state.case}&scene=${state.scene}`:`#scene=${state.scene}`;
  try {window.history.replaceState(null,'',hash);} catch (_) { /* Opaque srcdoc keeps its state in memory. */ }
}

function moveTop() {
  window.scrollTo(0,0);
  (app.querySelector(state.view==='cases'?'.case-head h2':'h1'))?.focus({preventScroll:true});
}

function setScene(n) {
  state.scene=Math.max(0,Math.min(10,n));state.view='story';
  render();updateLocation();moveTop();
}

function selectCase(n) {
  state.case=Math.max(0,Math.min(5,n));state.view='cases';
  if(state.case===0){state.order='partial';state.step=0;}
  if(state.case===1)state.reveal=false;
  if(state.case===2)state.match='v5';
  if(state.case===3)state.fix=2;
  if(state.case===5)state.clock='q';
  render();updateLocation();moveTop();
}

function refresh(t) {
  const y=window.scrollY,action=t?.dataset.action,value=t?.dataset.value;
  render();
  if(action){const selector=`[data-action="${CSS.escape(action)}"]${value!=null?`[data-value="${CSS.escape(value)}"]`:''}`;app.querySelector(selector)?.focus({preventScroll:true});}
  window.scrollTo(0,y);
}

document.addEventListener('click',e=>{
  const t=e.target.closest('[data-action]');if(!t)return;
  const a=t.dataset.action,v=t.dataset.value;
  if(a==='sources'){evidence();return;}
  if(a==='glossary'){glossary();return;}
  if(a==='evidence'){evidence(v);return;}
  if(a==='whitelist'){whitelist();return;}
  if(a==='performance'){performance();return;}
  if(a==='worst'){worst();return;}
  if(a==='zero-scales'){zeroScales();return;}
  if(a==='rank-distribution'){rankDistribution();return;}
  if(a==='close-dialog'){dialog.close();return;}
  if(a==='scene'){setScene(+v);return;}
  if(a==='page'){setScene(state.scene+Number(v));return;}
  if(a==='case'||a==='case-link'){selectCase(+v);return;}
  if(a==='return-story'){setScene(state.scene);return;}
  if(a==='view'){state.view=v;render();updateLocation();moveTop();return;}
  if(a==='order'){state.order=v;state.step=0;}
  else if(a==='step')state.step=Math.max(0,Math.min(orderCases[state.order].max,state.step+Number(v)));
  else if(a==='reveal')state.reveal=!state.reveal;
  else if(['pipe','family','proof','fix','calibration','history'].includes(a))state[a]=+v;
  else if(['match','route','clock'].includes(a))state[a]=v;
  else return;
  refresh(t);
});
document.addEventListener('change',e=>{if(e.target.dataset.action==='error'){state.error=e.target.value;refresh(e.target);}});
document.addEventListener('click',e=>{if(e.target.matches('.reference-addresses input'))e.target.select();});
document.addEventListener('keydown',e=>{
  if(dialog.open||e.altKey||e.ctrlKey||e.metaKey||e.target.closest('input,select,textarea,button,a,summary'))return;
  if(e.key==='ArrowRight'||e.key==='ArrowLeft'){
    e.preventDefault();const d=e.key==='ArrowRight'?1:-1;
    if(state.view==='cases')selectCase(state.case+d);else setScene(state.scene+d);
  }
});
function readLocation() {
  const p=new URLSearchParams(location.hash.slice(1));
  const bounded=(key,max)=>{const n=Number(p.get(key));return Number.isInteger(n)&&n>=0&&n<=max?n:0;};
  state.scene=bounded('scene',10);
  if(p.get('view')==='cases')selectCase(bounded('case',5));
  else {state.view='story';render();}
}
window.addEventListener('hashchange',readLocation);
readLocation();
})();
