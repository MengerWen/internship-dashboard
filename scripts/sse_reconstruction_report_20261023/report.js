(() => {
'use strict';
const DATA = JSON.parse(document.getElementById('report-data').textContent);
const app = document.getElementById('app');
const dialog = document.getElementById('evidence-dialog');
const state = {scene:0, view:'story', order:'partial', step:0, reveal:false, pipe:0, family:0, match:'v5', proof:0, route:'input', fix:0, clock:'q', error:'', calibration:0, history:4, case:0};
const esc = value => String(value).replace(/[&<>"']/g, c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const pct = (n,d=3) => n==null?'未定义':(n*100).toFixed(d)+'%';
const num = n => n==null?'未定义':n!==0&&Math.abs(n)<1e-5?Number(n).toExponential(5):Number(n).toLocaleString('en-US',{maximumFractionDigits:7});
const short = column => (DATA.factor_names[column.split('__')[0]]||column.split('__')[0])+' · '+(column.includes('__side_buy')?'买侧':'卖侧');
const btn = (action,value,label,active=false,cls='') => `<button type="button" class="${cls}" data-action="${action}" data-value="${value}"${['scene','case-link','return-story'].includes(action)?'':` aria-pressed="${active}"`}>${label}</button>`;
const detailButton = (key,label='展开字段、限制与原始证据') => `<button type="button" class="secondary" data-action="evidence" data-value="${key}">${label}</button>`;
const tags = label => `<span class="tag real">${label||'实测'}</span>`;
const scenes = [
 [
  "项目总结果",
  "已经能用公开信息算因子，正式生产还需定参与历史面板",
  "先看已经得到的结果，再看每一步怎样改变订单、计算过程和因子数值。",
  "position"
 ],
 [
  "先把订单记对",
  "600 股成交＋400 股挂单，应合成一笔 1,000 股委托",
  "本页用一个数量示意，解释为什么不能把行情中的每条消息都当成一笔新委托。",
  "observable"
 ],
 [
  "哪些能知道",
  "公开事实能确定，部分原始报单属性仍只能估计",
  "同样的成交记录可以来自不同原始报单。先分清哪些是事实，哪些是模型估计。",
  "observable"
 ],
 [
  "怎样接到因子",
  "动作前后状态对齐后，同一套程序才能正确评分",
  "先讲四类输入各自解决什么问题，再看它们服务于哪些因子计算。",
  "replay"
 ],
 [
  "定义怎样影响因子",
  "配对修正改善了直接分量，下游因子并非一起改善",
  "先用图解释配对为什么会错，再看同一批股票上的改前 / 改后数值。",
  "definition"
 ],
 [
  "输入核验结果",
  "数量守恒通过；外部逐秒盘口仍有 302 帧未全等",
  "分别看订单数量、外部盘口和样本准入，说明证据覆盖到哪里。",
  "replay"
 ],
 [
  "三种比较分开",
  "改定义会改分数；适配器同条件对照为零差异",
  "同一套深市数据做三组比较，分清数值变化来自哪里。S 和 H 只是两条比较路径的简称。",
  "evidence"
 ],
 [
  "输入修正的影响",
  "修正输入问题后，已验收的因子值没有变化",
  "用真实样本说明改了哪些输入，并单独回答这些修改有没有传到最终因子。",
  "evidence"
 ],
 [
  "换时钟影响多少",
  "换消息时钟后，272 列有变化，80 列保持不变",
  "这里的“时钟”是两次动作之间相隔多少条消息。价格、数量和实际时间都不改，只改变这个间距。",
  "clock"
 ],
 [
  "真实沪市与下一步",
  "真实沪市试运行已跑通，参数仍需独立估计",
  "先交代这次试运行的覆盖与结果，再说明正式生产还需要哪五步。",
  "next"
 ],
 [
  "交付与待办",
  "已交付输入和误差证据，尚未交付正式面板与收益检验",
  "把已完成结果与下一阶段交付分开，不用代码进度代替研究结论。",
  "reference"
 ]
];

const orderCases = {
 partial:{label:'先成交、再挂单', submit:'买入限价 10.03 × 1,000 股', max:2, tokens:[['T','10.00 × 600','首次可见成交'],['A','10.03 × 400','成交后的剩余挂出']], notes:['此时订单刚刚提交，还没在公开行情里产生任何可见记录（原始报单仅在上帝视角可见）。','第一步发出成交消息 T：先吃掉卖一档 600 股。此时这笔逻辑订单已经入场生效，不能等到后面出 A 消息时再重算一次入场。','第二步发出挂单消息 A：剩余 400 股挂上买一档。公开可见总量 Qᵥ = 600 + 400 = 1,000 股；这条 A 只是同一笔订单的剩余部分，不是新委托。']},
 rest:{label:'直接挂出',submit:'买入限价 9.98 × 1,000 股',max:1,tokens:[['A','9.98 × 1,000','未即时成交，直接入簿']],notes:['此时订单刚提交，尚未产生公开记录。','由于未触及对手价，直接发出公开挂单消息 A 并进入买二档排队，公开挂出价即为 9.98。']},
 pure:{label:'只有成交',submit:'隐藏的原始报单：背后有多种可能解释',max:1,tokens:[['T','10.00 × 600','公开消息中没有剩余挂单 A']],notes:['我们先遮住上帝视角的原始报单，只看公开行情流能提供什么。','只能看到一笔 600 股的成交 T，没有任何后续挂单 A。因此公开可见数量 Qᵥ 就是 600 股；至于它原本报的是什么限价、哪种市价类型、有没有未公开的即时撤余，单凭公开记录无法唯一确定。']},
 zero:{label:'完全不可见',submit:'既无成交、也无剩余挂出（当场自动撤销）',max:1,tokens:[],notes:['这里演示一笔既没能成交、也没能挂上盘口，入场即被系统自动撤销的订单。','公开行情里连一条 A 或 T 都不存在。因此公开订单事实表里绝不会凭空造出这笔订单，系统自动撤余也不能混充成投资者的主动公开撤单。']}
};
function orderDiagram(){
 const c=orderCases[state.order],step=Math.min(state.step,c.max),filled=step>0&&(state.order==='partial'||state.order==='pure');
 const newTop=state.order==='partial'&&step===2;
 const newSecond=state.order==='rest'&&step===1;
 const rows=[[filled?'卖一':'卖二','10.05','400',false],[filled?'原卖一 · 已成交':'卖一','10.00',filled?'0':'600',filled],[newTop?'买二':'买一','9.99','500',false],[newTop||newSecond?'买三':'买二','9.97','800',false]];
 if(newTop)rows.splice(2,0,['买一 · 新增','10.03','400',true]);
 if(newSecond)rows.splice(3,0,['买二 · 新增','9.98','1,000',true]);
 return `<div class="segmented" aria-label="订单情形">${Object.entries(orderCases).map(([k,v])=>btn('order',k,v.label,state.order===k)).join('')}</div><div class="split"><div class="visual"><div class="scenario-title"><h3>内部动作与公开消息</h3><span class="tag">示意 · 非真实行情</span></div><div class="trace-lanes"><div class="trace-lane"><span class="label">原始动作</span><div class="trace-stream"><div class="event-empty">${c.submit}</div></div></div><div class="trace-lane"><span class="label">公开消息</span><div class="trace-stream">${c.tokens.length?c.tokens.map((t,i)=>`<div class="event-token ${step===i+1?'current':step<i+1?'future':''}"><b>${t[0]}</b><span>${t[1]}</span><span>${t[2]}</span><span>${step<i+1?'待发布':'已发布'}</span></div>`).join(''):'<div class="event-empty">T：无　　A：无</div>'}</div></div></div><div class="story-control"><button class="secondary" data-action="step" data-value="-1" ${step===0?'disabled':''}>上一步</button><button class="primary" data-action="step" data-value="1" ${step===c.max?'disabled':''}>${step===c.max?'已到最后一步':'下一条消息'}</button><span class="stage-count">${step} / ${c.max}</span></div><p class="readout" aria-live="polite">${c.notes[step]}</p></div><div class="visual"><table class="book"><caption>公开盘口 · 当前步骤</caption><thead><tr><th>档位</th><th>价格</th><th>股数</th></tr></thead><tbody>${rows.map(r=>`<tr class="${r[0].includes('卖')?'ask':'bid'} ${r[3]?'changed':''}"><td>${r[0]}</td><td>${r[1]}</td><td>${r[2]}</td></tr>`).join('')}</tbody></table><div class="property-row"><div class="property"><b>t₀ 的含义</b>首次在公开行情中产生作用的时刻</div><div class="property"><b>Qᵥ 的含义</b>初始主动成交量 + 剩余公开挂出量</div></div><p class="fine">注：T = 成交消息，A = 公开挂单消息。图中价格与股数仅为拆解发布机制的示意。</p></div></div>`;
}
function ambiguityDiagram(){
 return `<div class="visual"><div class="same-evidence"><span>公开行情只给出这条记录</span><span class="print">T：10.00 × 600 股</span><span>后续没有 A 消息</span></div><div class="hypotheses">${[['买入限价 10.00','原始委托 600 股','刚好在 10.00 全量成交'],['买入限价 10.02','原始委托 600 股','对手盘只有 10.00，同样按 10.00 成交'],['带保护价的即时成交剩余撤销','原始委托 1,000 股','吃掉卖一 600 股后，剩余 400 股未公开即自动撤销']].map((r,i)=>`<div class="hypothesis ${state.reveal?'reveal':''}"><b>可能的原始报单 ${i+1}</b><p>${state.reveal?r[0]:'隐藏的原始类型 / 报单价'}</p><p>${state.reveal?r[1]:'隐藏的原始委托量'}</p><div class="value">${state.reveal?r[2]:'？'}</div></div>`).join('')}</div><div class="controls">${btn('reveal','',state.reveal?'重新遮住原始报单':'点此揭开三种完全兼容的原始报单',state.reveal,'primary')}<span class="fine">注：此处为撮合机制示意，实际各板块可用的订单类型受交易所规则约束。</span></div></div><div class="fork" style="margin-top:22px"><div class="branch"><span class="tag">研究探索线 · 推断隐藏属性</span><h3>模型到底能猜多准，用样本外实测说话</h3><div class="path-step">加入更多约束的 v2，仍未在留出数据上胜过简单 v1</div><p>深市留出日（2026-06-30）原始限价预测准确率：82.7566% → 82.5314%；平均绝对误差：2.8604 → 2.9208 个最小价格变动单位。</p></div><div class="branch selected"><span class="tag">生产实施线 · 锚定公开事实</span><h3>用公开可验证的价格和数量定义因子</h3><div class="path-step">可见总量、首次生效时刻、挂出价、最深成交价</div><p>这些公开事实用来构造输入；不知道的原始报单属性仍保留为未知，不把模型猜测当作真值。</p></div></div>`;
}
const pipes = [
 [
  "重建订单与盘口",
  "按沪市公开消息处理",
  "把同一笔委托的先成交、后挂出合起来，逐条更新买卖各档位的挂单量。",
  "成交与挂单消息 → 一笔逻辑订单和当时盘口"
 ],
 [
  "提取可确认的事实",
  "只采用公开可见的信息",
  "提取可见总量、首次生效时刻、成交价和挂出价。没有公开成交和挂单的订单，不凭空建立记录。",
  "订单与盘口 → 可确认的价、量、时间和动作"
 ],
 [
  "组织四类计算输入",
  "技术接口名：FactorInput",
  "把发生的动作、整笔订单过程、动作前状态和动作后状态放到四张对应的数据表中。",
  "同一动作的身份与前后状态 → 因子计算输入"
 ],
 [
  "计算行为得分",
  "价格版 px / 可成交性版 act",
  "复用已有的配对、打分和汇总程序；先让输入含义一致，再用沪市样本独立估计参数。",
  "公开事实＋确定的参数 → 各股票的因子值"
 ]
];
function pipelineDiagram(){const p=pipes[state.pipe];return `<div class="pipeline">${pipes.map((p,i)=>btn('pipe',i,`<strong>${p[0]}</strong><small>${p[1]}</small>`,state.pipe===i,'pipe-node')).join('')}</div><div class="split"><div class="inspector"><h3>${p[0]}解决什么问题？</h3><p>${p[2]}</p><div class="boundary">${p[3]}</div></div><div class="visual"><h3>四类信息怎样影响因子？</h3><div class="schema">${[['发生的动作','用于确认何时出现报单、成交或撤单，防止订单漏计或重复计数。'],['整笔订单过程','用于汇总公开总量、主动成交和剩余挂出量，决定按订单打分的分母与权重。'],['动作前状态','用于判断当时价格是否可成交、同价位前面还有多少量，影响追价与排队计算。'],['动作后状态','用于观察成交价和盘口变化，影响市场响应与报价调整类因子。']].map(r=>`<div class="schema-row"><b>${r[0]}</b><span>${r[1]}</span></div>`).join('')}</div></div></div>`;}
const families=[['46','直接可比','公开信息已足以支撑原公式定义，但仍需通过统一输入接口与逐列对账验收。'],['40','定义调整','在缺少原始隐藏属性的地方，明确改用公开价格、可见数量或可观测动作来替代。'],['254','公开信息替代','构造基于公开事实的代理候选列；在命名与标识上与深市原口径严格区分，不直接冒充原定义真值。'],['12','停用 / 排除','包含公开信息无法支撑或原本就已登记停用的列；原停用列不会因为迁移沪市而自动重新启用。']];
function matchingDiagram(){const old=state.match==='v4';return `<div class="segmented">${btn('match','v4','修正前：先删掉没有余量挂出的新单',old)}${btn('match','v5','修正后：先保留候选完成配对，再按规则计分',!old)}</div><div class="split"><div class="visual"><h3>同一笔撤单 O，面对两笔候选新单</h3><svg class="matching-graph" viewBox="0 0 680 260" role="img" aria-label="旧单 O 优先选择纯成交 N1；预先删除 N1 会错误转配给 N2"><path d="M200 130 L440 65" class="${old?'discarded':'chosen'}"/><path d="M200 130 L440 195" class="${old?'chosen':'inactive'}"/><rect x="25" y="93" width="175" height="75" rx="2" class="focus-node"/><rect x="440" y="25" width="215" height="80" rx="2" class="node"/><rect x="440" y="155" width="215" height="80" rx="2" class="node"/><text x="58" y="136">旧单 O</text><text x="464" y="58">N1：纯成交新单</text><text x="464" y="86">距离更近（最优配对）</text><text x="464" y="187">N2：有挂出新单</text><text x="464" y="215">距离较远（次优候选）</text></svg><p class="fine">注：上图为配对竞争机制示意，连线代表配对归属而非具体得分。</p></div><div class="inspector"><h3>${old?'如果提前把 N1 踢出候选池，配对就会错位':'先保留完整竞争关系完成配对，再按公开规则计分'}</h3><p>${old?'若在配对前直接删掉纯成交单 N1，原本排第二的 N2 就会递补配中，凭空多算出一笔原本不该存在的排队优先度变差得分。':'让 N1 正常参与竞争并胜出配中；随后在计分环节按纯成交单的公开规则将其排队优先度变差的贡献记为 0，不再把配对机会转手让给 N2。'}</p><div class="equation">${old?'O 错配给 N2 → 凭空多算得分':'O 正常配给 N1 → 该项贡献记 0'}</div><p class="fine">这是 v5 专门收紧的配对边界，先影响排队优先度分量所在的 P 行为组，再影响综合得分（union）及使用综合得分的下游指标。</p></div></div>${definitionImpact()}`;}

function definitionImpact(){
 const d=DATA.definition_impact, direct=d.rows.slice(0,2), downstream=d.rows.slice(2);
 return `<div class="visual" style="margin-top:22px"><h3>这次配对修正，实际影响了哪些因子？</h3><p>先看修正前的问题：对照深市原定义，旧版公开定义在 22 只诊断股票中有 <strong>16,194 笔旧单的匹配对象不同</strong>；其中 15,055 笔在深市匹配的是纯成交新单，旧版公开定义却改配到有挂出余量的新单。先完成配对、再按规则计零的离线诊断，使这组样本的订单绝对分差减少 99.8914%。这个归因比例只属于这 22 只样本。</p><table class="book"><caption>直接分量：与深市原定义有差异的股票占比明显缩小</caption><thead><tr><th>排队优先度变差分量</th><th>修正前</th><th>修正后</th></tr></thead><tbody>${direct.map(x=>`<tr><td>${x.name.includes('买')?'买侧':'卖侧'}：差异股票占比</td><td><span style="white-space:nowrap">${pct(x.before.affected_share,4)}</span></td><td><span style="white-space:nowrap">${pct(x.after.affected_share,4)}</span></td></tr><tr><td>${x.name.includes('买')?'买侧':'卖侧'}：股票排序相关</td><td><span style="white-space:nowrap">${x.before.rank_correlation.toFixed(6)}</span></td><td><span style="white-space:nowrap">${x.after.rank_correlation.toFixed(6)}</span></td></tr>`).join('')}</tbody></table><p style="margin-top:15px">修正后买侧仍有 743 / 2,888 只股票、卖侧仍有 740 / 2,888 只与深市原定义不同。因此，这个分量更接近深市了，但没有变成完全相同。</p><table class="book"><caption>下游指标：直接分量改善，不代表所有汇总指标也更接近深市</caption><thead><tr><th>指标</th><th>修正前<br>相对差中位数</th><th>修正后<br>相对差中位数</th></tr></thead><tbody>${downstream.map(x=>`<tr><td>${x.name}</td><td><span style="white-space:nowrap">${num(x.before.median)}</span></td><td><span style="white-space:nowrap">${num(x.after.median)}</span></td></tr>`).join('')}</tbody></table><p style="margin-top:15px">f54 汇总综合行为得分，f55 反映四类行为的平均强度。上面两项的相对差中位数反而略增。配对归属和组内最大得分会继续影响综合结果，因此不能把“修正了配对机制”写成“所有因子都更接近深市”。</p><p class="fine">样本：2026-06-30，同一批 2,888 只股票。表中直接分量两版相同，下游示例为价格版 px。这里比较公开定义与深市原定义，沿用该次验收的相对差口径；第 9 页比较的是消息时钟，误差分母不同，不直接横比。</p>${detailButton('definition','查看定义、影响范围与原始数值报告')}</div>`;
}

function definitionDiagram(){return `<div class="family-map">${families.map((f,i)=>btn('family',i,`<strong>${f[0]} 列</strong><span>${f[1]}</span>`,state.family===i,'family')).join('')}</div><p class="readout" aria-live="polite">${families[state.family][2]} 这里的“列”指一项具体的因子计算。原有 352 列中，164 列由两版共用，188 列分别按价格版和可成交性版计算，共得到 164 + 188 × 2 = 540 项候选结果；它们仍需验证后才能作为正式生产因子。</p><div class="union-output"><div><b>px 分支：看公开成交价</b><p>用实际打出的最深成交价衡量追价幅度</p></div><div class="connector">≠</div><div><b>act 分支：看实际可成交性</b><p>用入场时相对对手盘最优价的侵入程度衡量主动性</p></div></div>${matchingDiagram()}<p class="scope-note">综合得分使用 57 种核心行为证据，分为四组；另有 6 个公开信息替代指标单独保留。综合得分反映行为证据的强度，并不是“这笔订单有多大概率来自算法交易”的校准概率。成员清单与分组见详细依据。</p>`;}
const proofs=[
 ['内部守恒检验','事件流与订单数量是否自洽','覆盖 13 个交易日 · 29,622 个股票日','共核验 180,519,830 条标准化动作记录；31,372,036 组订单入场时的连续成交记录都发生在同一时点；29,620 个完整开盘五分钟样本的数量守恒差异全部为 0。','数量检查用来发现漏合并、重复计数或数量错误。所检查的守恒关系通过，并不能证明所有订单身份都正确，也不能证明隐藏的原始报单属性。'],
 ['外部盘口对账','盘口价量与排队队列能否对上外部快照','29,135 组开盘竞价成交价 / 量全等','每个整数秒上可唯一确定的盘口状态有 268,421 / 268,723 帧与外部快照完全一致；前五档队列核对 437,358 帧全部一致（队列数据目前仅覆盖 2 个交易日）。','整秒快照与开盘竞价对账通过，不等于完成了亚秒级快照认证；同时，纯靠外部快照还不足以单独构成同价位订单严格按先到先成交的顺序的强证明。'],
 ['异常样本剔除','哪些股票日不能直接放进计算池','按整只股票日剔除，而非只删异常行','在开盘后 09:30–09:35 内，只要盘口快照的交易阶段码不等于 3，就排除该股票当日的整个样本。4 例阶段码为 8 的样本表现与盘中临停吻合，官方代码含义仍待核实。','同一时间戳下紧挨着的全额撤单仍按普通撤单处理，不靠时间巧合臆测来源；另外，“回放逻辑自洽跑通”与“上游源行情包毫无缺失”是两项不同的检查。']
];
function proofDiagram(){const p=proofs[state.proof];return `<div class="split"><div class="layer-list">${proofs.map((p,i)=>btn('proof',i,`<b>${p[0]}</b><span>${p[1]}</span>`,state.proof===i)).join('')}</div><div class="visual proof-detail">${tags()}<h3 style="margin-top:13px">${p[1]}</h3><div class="result">${p[2]}</div><p>${p[3]}</p><div class="boundary">${p[4]}</div></div></div><div class="metric-line"><div><b>7,477</b><span>已补齐截断处信息的样本</span></div><div><b>6 / 23</b><span>集合竞价模拟价 / 模拟量与快照的差异数</span></div></div>`;}
const fixes=[
 ['残留自动撤单','437 行','0 行','16 只股票中，有些订单既未成交，也未挂出，已不进入公开订单记录；但本应一并排除的 437 条系统自动撤单，仍残留在参照路径 S 的输入里。','按已核实的自动撤单规则，从参照路径的动作、动作前状态和动作后状态中同步排除这些记录；投资者的公开撤单仍按原规则处理。'],
 ['金额基准标签','本侧 / 对手侧最优报价','公开委托价','这些订单已经按公开价格表达为限价单，但金额计算基准的标签仍指向隐藏市价单使用的最优报价，与公开表示不一致。','把整笔订单过程、动作前和动作后状态中的金额基准，统一标为公开委托价（字段值 submit_price），让标签与实际计算一致。'],
 ['档位挂单量','113,500','0','真实样本 000333 / seq 4809671：公开卖单价为 782700，而动作发生前的卖一价是 783800；在比卖一还低的公开价格上，卖方盘口不可能挂着同侧卖单量。','原因是路径 S 换了公开价格后，仍去原始隐藏委托价上取同侧挂单量。修正后，S 与 H 各自按本侧、公开价格及动作前盘口独立重算；此样本上 H 算出的 0 才是对的。'],
 ['后态成交价','101900 / 0','102100','真实样本 000001 / seq 588089：修正前 S 残留了原始价 101900，H 误填为 0，两边都不对；这笔订单自己的公开成交记录明确支持 102100。','修正后，S 与 H 各自从本身的公开成交明细中提取后态 price_tick，绝不互相拷贝（例如另一样本 000333 / seq 590368 上则是 S 正确而 H 原先误记为 0）。'],
 ['即时入场排队量','NA','0','即时主动成交在逻辑入场那一刻并未挂上订单簿等待，前面不存在同价位先到的排队单，因此不能把排队量记成缺失值 NA。','qty_ahead_pre 字段：路径 S 原先填 NA 违背了即时入场定义，路径 H 填 0 符合定义；现统一由入场动作状态独立推导。'],
 ['深市参考回归','旧参考 472 / 1,720 不等','新参考两轮全等','那份旧参考生成于 10-21 三项口径决议（排队余量、f16 即时成交、DM 分母）之前。经核查，472 处差异全部落在这三项决议的影响范围内，范围外差异为 0。','5 只深市代表股各 352 列，在本次 C2 修正前后两轮对 r2 / v5 新参考基准均 100% 逐位一致；旧参考的 472 处差异对应 124 个列标识，全部源于“排队稀释只计挂出余量”及其下游传导。']
];
function fixesDiagram(){const f=fixes[state.fix];return `<div class="segmented">${fixes.map((f,i)=>btn('fix',i,f[0],state.fix===i)).join('')}</div><div class="split"><div class="visual"><h3>${f[0]}：定义决定取值</h3><div class="sample-compare"><div class="sample-value"><span>修正前 / 旧参照</span><b>${f[1]}</b></div><div class="sample-value fixed"><span>独立核对后</span><b>${f[2]}</b></div></div><p class="readout">${f[3]}</p><p class="fine">价格样本均为原始整数价格单位；此处不擅自换算为元。</p></div><div class="inspector"><h3>根因与修正方式</h3><p>${f[4]}</p><div class="boundary"><b>清理这些输入字段后，因子输出变了吗？</b><p>相对于 v5 全市场签收结果，px 与 act 在 2,888 只股票上的变化列数均为 0、受影响股票数均为 0；12 个独立抽检的盘口样本全部符合定义。</p></div></div></div><p class="scope-note">也就是说，这次清理更新的是参照路径 S 的构造方式，把此前“输入表逐字段全等”的证据链彻底补齐；而 v5 已经签收的因子数值在修正前后分毫未动，深市原生默认逻辑也通过了修正前后的新参考回归。</p>`;}
const sortedErrors=DATA.errors.filter(r=>r.scaled_p99!=null).sort((a,b)=>b.scaled_p99-a.scaled_p99);
if(!state.error)state.error=sortedErrors[0].column;
const calibration = [
 [
  "1. 确定样本",
  "先确定哪些数据可以计算",
  "固定公开定义、消息计数方式与样本排除规则，逐日核对股票池和报价数据。股票池名单存在，不等于数据已全部齐备。"
 ],
 [
  "2. 估计相近尺度",
  "多远、多大还算相关",
  "用沪市样本分别估计时间、消息间距、数量、价格及报价距离的尺度。它们决定相隔较远的动作应降低多少权重，不能直接照搬深市参数。"
 ],
 [
  "3. 确定配对门槛",
  "哪些动作应该被连在一起",
  "在基础尺度确定后，估计订单链切分、代表动作选择、配对质量及盘口响应的门槛。这些值会改变哪些候选被计入，从而影响行为得分。"
 ],
 [
  "4. 固定参数与版本",
  "让同一输入可以复算",
  "把样本范围、参数数值、数据与代码版本一起固定，并记录文件校验值。上游参数改变后，依赖它的中间计算也要重算。"
 ],
 [
  "5. 批量计算并研究",
  "先得到因子，再检验收益关系",
  "先验证代表样本和单日全市场，再按准入范围扩展历史计算。正式面板通过核对后，才接收益标签、相关性检验和回测。"
 ]
];
function nextDiagram(){const c=calibration[state.calibration];return `<div class="visual"><h3>真实沪市试运行：成功多少、排除多少？</h3><div class="coverage-strip" aria-label="px 2296成功，14排除，0失败"><span style="flex:2296"></span><span class="excluded" style="flex:14"></span></div><div class="metric-line"><div><b>2,296 / 2,310</b><span>价格版成功 / 股票池；14 只按交易阶段排除</span></div><div><b>29 / 30</b><span>可成交性版成功；1 排除；失败 0</span></div><div><b>456.83 秒</b><span>批次；约 15.96 核 / 46.04 GiB</span></div></div><p class="fine">实测交易日：2026-06-30。本次试运行临时借用了固定版本的深市参数，用于确认订单与盘口重建、输入构造和因子计算能够完整运行。这些试算值尚不能作为正式沪市因子；沪市参数仍需独立估计。</p></div><div class="calibration">${calibration.map((c,i)=>btn('calibration',i,`<span>0${i+1}</span><b>${c[0]}</b><small>${c[1]}</small>`,state.calibration===i)).join('')}</div><div class="inspector"><h3>${c[0]}：${c[1]}</h3><p>${c[2]}</p>${calibrationIllustration()}<p class="fine">目前已有 沪市 601 个交易日（2024-01-02 至 2026-06-30）、共 1,370,521 个股票日的各日股票池名单；但“股票池名单就绪”不代表全部日期的所需行情数据和沪市独立参数已经核验就绪。</p></div>`;}
const history=[["9 月底", "确认能知道什么", "公开盘口和可见数量可以重建；部分原始价格、类型和隐藏余量不能唯一确定。"], ["10-14", "检验隐藏属性估计", "模型的限价点估计没有在三个留出日胜过简单基线，因此不把模型猜测当作生产真值。"], ["10-21", "明确公开信息下怎样评分", "确定如何计算挂出余量、即时成交和订单数量分母，建立公开信息下的因子定义。"], ["10-22", "修正配对并量化因子变化", "排队优先度的差异股票占比明显下降；部分下游汇总因子没有同步更接近深市。"], ["10-23", "跑通真实沪市并完成对照", "真实沪市价格版 2,296 只成功；适配器同条件零差异，消息时钟误差单独列出。"]];
function overviewDiagram(){return `<div class="visual"><h3>三个结果，分别回答三个问题</h3><table class="book"><thead><tr><th>改变了什么</th><th>实测结果</th><th>对因子意味着什么</th></tr></thead><tbody><tr><td>从深市原始属性改为公开可见定义</td><td>1,407.9 万笔共同订单的综合得分相关：价格版 0.962589；可成交性版 0.961794</td><td>信息减少后，行为定义和得分确实会变；不能把公开定义直接当成原定义的等价结果。</td></tr><tr><td>同一定义、同一时钟，走两条适配路径</td><td>价格版 1,016,576 个因子值、可成交性版 10,560 个值，不等项均为 0</td><td>在所测日期和范围中，适配器没有额外引入因子数值差异。</td></tr><tr><td>保持其他条件不变，只换消息时钟</td><td>272 / 352 列至少一股变化；误差最大的列，99% 分位为 0.052425 个全市场尺度</td><td>排序总体稳定，但仍要根据逐列误差决定能否接受。</td></tr></tbody></table><p class="fine" style="margin-top:15px">综合得分是把一笔订单的多种行为证据合在一起的分数（技术名 union）。价格版 px 用公开执行价衡量追价；可成交性版 act 用当时相对对手报价的可成交程度衡量主动性。相关性不代表收益预测能力。</p></div><div class="boundary"><b>真实沪市也已经试跑：2,296 只成功，14 只排除，失败 0。</b><p>这是 2026-06-30 的价格版结果，临时借用深市参数。正式生产还需沪市独立参数和历史面板验收。</p></div><div class="controls">${btn('scene',4,'看定义改动怎样影响因子',false,'secondary')}${btn('scene',6,'看适配器为什么是零差异',false,'secondary')}${btn('scene',8,'看时钟误差的实际数值',false,'secondary')}${btn('scene',9,'看正式生产还差什么',false,'secondary')}</div>`;}
function historyDiagram(){const h=history[state.history];return `<div class="timeline">${history.map((h,i)=>btn('history',i,`<strong>${h[0]}</strong><b>${h[1]}</b><small>${h[2]}</small>`,state.history===i)).join('')}</div><div class="inspector"><h3>${h[0]} · ${h[1]}</h3><p>${h[2]}</p><div class="pending-list"><span>已完成：公开输入与同条件适配器对照</span><span>已量化待决定：公开消息时钟误差</span><span>待落实：正式行情证据与固定版本约定</span><span>待开展：沪市定参、历史面板与收益检验</span></div></div><div class="next-band"><p><b>代码版本与运行留痕</b><br>核心业务验收版本 f6592c06；补充归约 8de2ca87；报告与证据定稿 2a0dac94。本地提交、GitHub 远端、wenjie 服务器同步与实际跑批均留有独立记录。</p><div class="controls"><button class="secondary" data-action="performance">查看耗时、算力边界与存储状态</button>${detailButton('reference','查看原始报告与完整版本记录')}</div></div><p class="fine">注：本汇报完全基于截至 2026-10-23 的实测证据整理；沪市独立定参、全历史因子面板重算与下游 IC 评估均属后续独立阶段工作。</p>`;}
const renderers=[overviewDiagram,orderDiagram,ambiguityDiagram,pipelineDiagram,definitionDiagram,proofDiagram,routeDiagram,fixesDiagram,clockDiagram,nextDiagram,historyDiagram];
