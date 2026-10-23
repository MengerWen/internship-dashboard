const cases = [
  ['600 + 400','一笔委托如何拆成多条公开消息',1,'先部分成交、剩余部分再挂上盘口时，成交 T 与后续挂单 A 属于同一笔逻辑订单。'],
  ['只看到成交 T','为什么原始报单属性往往没有唯一解',2,'完全相同的公开成交记录，背后可以同时兼容多种不同的原始限价、市价类型或未公开撤余。'],
  ['先配对还是先删','公开口径如何影响候选配对与 union',4,'如果在配对前就删掉纯成交候选单，会导致撤单错配给次优新单；必须先在全量候选中配对，再按公开规则计零。'],
  ['113,500 为何归零','用真实盘口样本检验谁违背了公开定义',7,'在动作发生前的真实盘口上，必须按替换后的公开价格重新核对该价位的同侧挂单量，不能沿用原始隐藏价上的挂单量。'],
  ['472 项旧参考差异','如何确认深市原生默认逻辑没有被误伤',7,'先将参考基准升级到包含 10-21 三项决议的新版本，从而把“前期口径更新”与“代码回归 bug”彻底区分开。'],
  ['间距从 9 变 5','为什么先后顺序没变，换个时钟因子值还会变',8,'即便订单顺序和价量完全不变，公开消息时钟也会改变两件事之间的序号差（Δseq），进而通过衰减核与配对窗口影响得分。']
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
  return `<div class="split"><div class="visual"><h3>如果拿过期的旧参考当标尺，就会把正常的口径升级误报成回归 bug</h3><div class="regression-row"><span>对比 10-21 前的旧参考 · 5 股 × 344 列</span><strong>472 / 1,720 项不一致</strong><div class="regression-track"><i style="width:27.44186%"></i></div></div><div class="regression-row"><span>对比 r2 / v5 新参考 · 每轮 5 股 × 352 列</span><strong>C2 修正前：0 / 1,760 项不一致</strong><strong>C2 修正后：0 / 1,760 项不一致</strong></div><p class="fine">注：修正前后两轮各对比 r2 与 v5 两份新参考，合计 7,040 次逐位比对全部一致。由于新旧参考的列集合不同（344 列 vs 352 列），分母分别为 1,720 与 1,760，不能混用。</p></div><div class="visual"><h3>旧参考中 472 处差异的逐项归因</h3><div class="metric-line"><div><b>472</b><span>落在 10-21 口径决议影响范围内</span></div><div><b>0</b><span>落在决议影响范围之外</span></div></div><p>这 472 处差异涉及 124 个不同的列标识，经逐一排查，100% 源于“排队稀释只计真正挂出的余量”这一项口径更新及其下游传导；另外两项决议（f16 即时成交、DM 分母）并未产生这批差异。</p><p class="fine">此外，我们分别核对了 r2 与 v5 的生成提交记录与数值逻辑（注：提交 ec7d8c0c 仅是补齐下游消费者登记，并非 DM 分母数值逻辑的修改提交）。</p></div></div><div class="visual" style="margin-top:20px"><h3>5 只深市代表股 × 各 352 列回归结果</h3><div class="regression-stocks">${['000725','300750','000001','000333','300577'].map(s=>`<div><b>${s}</b><span>C2 修正前：0 / 0</span><span>C2 修正后：0 / 0</span></div>`).join('')}</div><p class="fine">每格中的“0 / 0”分别代表相对于 r2 与 v5 两份新参考的不一致项数。整个过程中没有为了迁就旧参考而倒退修改深市生产逻辑。</p></div>`;
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
    ['委托 vs 消息','委托是投资者下达的一笔报单指令；消息则是交易所对外广播的一条公开记录。在沪市，同一笔委托如果先部分成交、剩余再挂单，就会拆成多条成交消息 T 和一条剩余挂单消息 A。'],
    ['A / T / D（C）','A 代表公开挂单（Add）；T 代表成交（Trade）；D 或 C 在不同表结构命名中均代表撤单（Delete / Cancel）。一笔撤单到底是投资者主动撤单还是系统自动撤余，需结合盘口事实与规则判定。'],
    ['盘口与回放','盘口（Order Book）记录买卖各档位的在簿挂单量；回放（Replay）则是按逐笔消息顺序一步步重建出盘口状态。注意：盘口状态能对上快照，不代表背后的隐藏原始报单属性也已经唯一确定。'],
    ['Qᵥ 与 t₀','Qᵥ 是订单的公开可见总量（初始主动成交量 + 剩余挂出量）；t₀ 是该订单首次在公开行情中产生作用的时刻，不能把它当成未知原始报单到达时间的证明。'],
    ['前态 / 后态','分别指同一个市场动作发生前一刻（prestate）与执行更新后（poststate）的订单及盘口状态；在计算市场响应和排队位置时，前后态绝不能混用。'],
    ['FactorInput','沪深共用因子引擎的标准输入接口，由 events（事件）、lifecycle（生命周期）、event_prestate（动作前态）和 event_poststate（动作后态）四张表组成。'],
    ['px / act 双版本','针对纯成交订单追价行为的两种公开度量口径：px 跟踪公开实际成交价的变化，act 跟踪动作发生时相对对手盘最优价的可成交性（侵入程度）变化。'],
    ['union 合成得分','在逐笔订单层面将 L、P、C、R 四大行为族的候选得分合成为总分，再归约到股票日层面；它反映的是多维算法交易行为特征的合成强度，而非经过校准的算法交易概率。'],
    ['消息时钟与 Q_equity','这里的“时钟”指用来度量两个事件相隔多少条消息的序号（seq），而非物理秒数。Q_equity 基于整条通道内所有可见的 A 股消息统一编号，不能按单只股票各自压缩。'],
    ['θ 与结构门限','θ 是核函数中的衰减尺度（按 exp(−d/θ)，距离为 θ 时权重降至 1/e；半衰距离为 θ ln(2)）；结构门限则决定哪些订单链、配对候选和盘口冲击能跨过门槛进入统计。这两类参数都必须在沪市样本上独立标定。'],
    ['路径 S 与路径 H','双路径回环实验的两端：路径 S 把深市认证真值直接按公开口径改写成输入表（作为标尺）；路径 H 先把同一份深市真值转换成沪市 A/T/C 消息流，再走沪市原生回放与适配器还原出来。'],
    ['逐位一致（Bitwise Identical）','指两个有限浮点数在底层二进制位模式上完全相同（两边同为 NaN 时也视为一致）。这比“数值差不多”严格得多，但结论仍严格限定在所测的样本与列范围内。'],
    ['W5 窗口与签收','W5 指开盘后 09:30–09:35 的前五分钟计算窗口；“签收”指特定代码版本在给定样本与口径下通过了验收标准，不能自动外推等同于全历史区间都已验收。'],
    ['交易时段冻结','指公司服务器上的批量计算任务在盘中规定交易时段自动暂停让路（guard 机制），这属于物理算力调度约束，跟因子公式里的“冻结参数”或“消息时钟”完全是两码事。']
  ];
  openDialog('术语短解',`<div class="glossary">${terms.map(([name,desc])=>`<div><h3>${name}</h3><p>${desc}</p></div>`).join('')}</div>`);
}

function whitelist() {
  openDialog('白名单到底放行了哪些差异？背后的验证证据是什么？',`<p>白名单只豁免那些已经通过代码排查与扰动实测、证明对当前 352 列因子输出毫无影响的表示层差异；但这绝不意味着可以笼统声称“引擎从来不读这些字段”。</p><div class="table-wrap"><table><thead><tr><th>豁免项</th><th>允许的差异形式</th><th>验证方法与严格边界</th></tr></thead><tbody><tr><td>received_ts</td><td>本地接收时间戳按固定规律平移或重设</td><td>静态读取点排查 + 10 只代表股 px/act 双版本扰动实测</td></tr><tr><td>vendor_aggressor_side_raw</td><td>外部供应商原始主动性标签置为 NA 或随机字符串</td><td>因子实际使用的主动性由公开盘口事实独立推算，不依赖该原始标签</td></tr><tr><td>event_pos</td><td>在严格保持先后顺序的前提下，四表同步插入间隔或重新编号</td><td>引擎确实会读取该列用于排序和定位；只允许保序同步改号，打乱顺序不在豁免之列</td></tr><tr><td>7 个精确的 attrs 键</td><td>记录数据来源与回放版本的元数据键值不同</td><td>仅精确豁免以下 7 个键，绝不对整个 attrs 字典做一刀切豁免</td></tr></tbody></table></div><p><code>szse_replay_version<br>szse_replay_fix_a<br>szse_replay_fix_c<br>replay_options<br>order_event_semantics<br>original_submissions_established<br>legal_unrested_trade_legs</code></p><p>静态代码扫描共核对 368 处命中点；动态实验抽取高、中、低活跃度分层的 10 只股票 × 10 项扰动 × px / act 双版本 = 200 次有效扰动运行，累计比对 70,400 个因子输出值，结果 100% 逐位不变。至于科学序号 seq 和本次 C2 修正的业务字段，一律不在白名单内。</p>${DATA.source.evidence.body}`);
}

function mechanism(column) {
  const key=Object.keys(DATA.mechanisms).find(k=>column.startsWith(k+'__'));
  return key?DATA.mechanisms[key]:'【推测】序号距离进入衰减或候选窗口，具体贡献仍需沿依赖链逐项归因。';
}

function worst() {
  openDialog('p99 截面尺度误差最大的前 20 列及传导机制',`<p>基于全市场 2,888 只股票的实测汇总。误差以路径 S 的全市场截面稳健尺度 scale(S) 为分母，分位数统计涵盖零误差股票；传导机制说明严格区分【事实】与【推测】。</p><div class="table-wrap"><table><thead><tr><th>因子列</th><th>受影响股票占比</th><th>p99 / 截面尺度</th><th>最大值 / 截面尺度</th><th>Spearman ρ</th><th>误差传导机制</th></tr></thead><tbody>${sortedErrors.slice(0,20).map(r=>`<tr><td>${short(r.column)}</td><td>${pct(r.affected_fraction,2)}</td><td>${num(r.scaled_p99)}</td><td>${num(r.scaled_max)}</td><td>${r.spearman.toFixed(9)}</td><td>${mechanism(r.column)}</td></tr>`).join('')}</tbody></table></div><p class="fine">注：标为【事实】的列，已在代码层面确凿定位到序号间距（Δseq）进入衰减核或窗口的具体路径（但未将单只股票的误差进一步拆解为各子项的独立加权贡献）；标为【推测】的合成列，则尚未做逐个根分量或参数的消融实验。</p>`);
}

function zeroScales() {
  openDialog('6 个零尺度结构列说明',`<p>以下 6 个反向结构零列（如买侧因子在卖侧方向上的结构恒零列）在全市场所有股票上均恒为 0，切换时钟前后逐位不变。由于分母尺度为 0、且全截面取值恒定，其尺度误差比值与 Spearman 秩相关在数学上均无定义——我们在报表中如实记为“未定义”，而不人为填成 0 或 1。</p><div class="table-wrap"><table><thead><tr><th>因子列</th><th>发生变化股票数</th><th>截面尺度比值 / Spearman ρ</th></tr></thead><tbody>${DATA.errors.filter(r=>r.zero_scale).map(r=>`<tr><td>${short(r.column)}</td><td>${r.changed}</td><td>未定义</td></tr>`).join('')}</tbody></table></div>`);
}

function rankDistribution() {
  openDialog('346 个有效列的 Spearman 秩相关系数分布',`<div class="table-wrap"><table><thead><tr><th>分位点</th><th>Spearman ρ(H, S)</th></tr></thead><tbody>${[['最小值','0.999934547509'],['p01','0.999976194649'],['p25','0.999998068846'],['中位数','0.999999657498'],['p75','0.999999944203'],['p99','1.000000000000'],['最大值','1.000000000000']].map(r=>`<tr><td>${r[0]}</td><td>${r[1]}</td></tr>`).join('')}</tbody></table></div><p>注：基于全市场所有有限股票配对计算（并列值取平均秩）；另外 6 个恒零结构列逐位不变，秩相关未定义。该分布表明切换 Q_equity 时钟后全市场横截面排序高度稳定，但它依然不能代替业务上对数值误差的接受拍板，也不代表因子的收益预测能力。</p>`);
}

function performance() {
  openDialog('运行耗时边界、代码版本留痕与磁盘存储说明',DATA.source.status.body+`<h3>单股 000725 与全市场跑批的计时明细</h3><p>000725 单股输入构造耗时 111.411 秒；五次引擎调用每次约 319–385 秒，包含逐位比对、归约统计与内存回收在内的单股完整阶段共耗时 1,915.664 秒。之所以先把 000725 单独完整跑完，就是为了实打实走完它的全部比对，避免大批量任务万一触发耗时上限截断时把“未跑完”误当成“验收通过”。</p><p>全市场主 guard 任务的有效计算墙钟为 3,340.953 秒（自然墙钟总耗时 6,040.937 秒，其中盘中交易时段自动冻结暂停了约 2,699.983 秒）。其余 2,887 只股票阶段平均并发占用 15.967 核；全部 15 次 guard 任务的有效计算墙钟合计 91.56 分钟。</p><div class="table-wrap"><table><thead><tr><th>工程与验证环节</th><th>对应状态与 Git 版本号</th></tr></thead><tbody><tr><td>本地代码提交</td><td>C2(a) 2ecaa8f4、C2(b) e07e0d6d、C2(c) cca9a6ef 分步独立提交；后续归因标签修正提交为 21520d85（未改动任何数值计算逻辑）。</td></tr><tr><td>GitHub 远端同步</td><td>研究代码已推送至 origin/main（原运行记录核对至 21520d85；最终报告与证据归档版本为 2a0dac94）。</td></tr><tr><td>wenjie 服务器同步</td><td>主跑批任务启动前快进同步至 f6592c06；主任务正常退出后，快进至 8de2ca87 执行补充归约统计。</td></tr><tr><td>实际跑批验证</td><td>C4 / C5 主实验在 f6592c06 下跑完，act 对比 v5 及最终汇总归约在 8de2ca87 下跑完；全部 15 次 guard 任务均以状态码 0 正常退出。</td></tr></tbody></table></div><p>注：我们把实际跑批时的代码版本与最终文档归档版本分开如实记录。整理本汇报时，并未重新连上服务器探测磁盘、读取真实沪市底层行情或重跑因子。</p>`);
}

function calibrationIllustration() {
  if(state.calibration===1) return `<div class="kernel-map">${[['墙钟时间','wall_seconds','两个动作之间相隔多少秒'],['消息序号','events','两个事件在消息流里相隔多少步'],['委托数量','qty','委托量与成交量的规模尺度'],['价格档位','price_ticks','成交价或挂单价之间相差多少个 tick'],['最优报价距离','bbo_ticks','相对于本侧或对手侧 BBO 的档位距离'],['可成交性距离','marketability_ticks','相对于对手盘最优报价的主动侵入距离']].map(r=>`<div><b>${r[0]}</b><code>${r[1]}</code><span>${r[2]}</span></div>`).join('')}</div><p class="fine">注：上方卡片列出的是需要在沪市样本上独立标定的六个距离维度（此处不展示尚未签收的沪市 θ 数值）。简单来说，六核尺度决定了“两个事件隔多近才算相近”，而下一步的结构参数则决定“哪些候选关系能跨过门槛参与配对和打分”。</p>`;
  if(state.calibration===2) return `<div class="handoff-flow"><span>采集结构观测值</span>→<span>episode 片段切分</span>→<span>anchor 锚点筛选</span>→<span>cost / match 配对</span>→<span>分位数门限归约</span></div><p class="fine">注意：由于这五步环环相扣，一旦上游核参数或门限发生变化，就必须从头重跑，绝不能直接拿旧门限下存留的中间缓存接着算。九组结构参数的完整统计规则可点击左下角“本页技术与证据”展开查看（其中 f85 与 z12 直接取加权中位数、不除以 ln(2)，与六核及 f16 的口径严格区分）。</p>`;
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
