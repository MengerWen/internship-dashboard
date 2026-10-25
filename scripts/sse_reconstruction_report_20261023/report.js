(() => {
'use strict';
const DATA = JSON.parse(document.getElementById('report-data').textContent);
const app = document.getElementById('app');
const dialog = document.getElementById('evidence-dialog');
const state = {scene:0, view:'story', order:'partial', step:0, reveal:false, pipe:0, family:0, match:'v5', proof:0, route:'input', fix:0, clock:'q', error:'', calibration:0, history:6, case:0};
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
  "输入已验收，单日定参试算已通过",
  "第六核方法已批准，工程接线与代表日试算已通过；601 日正式定参仍未启动。",
  "position"
 ],
 [
  "先把订单记对",
  "600 股成交＋400 股挂单，应合成一笔 1,000 股委托",
  "先看一个数量示意，理解为什么行情里的每条消息不等于一笔新委托。",
  "observable"
 ],
 [
  "哪些能知道",
  "公开事实能确定，部分原始报单属性仍有多解",
  "同样的成交记录可能来自不同原始报单。先分清可核验事实与模型估计。",
  "observable"
 ],
 [
  "怎样接到因子",
  "动作前后状态对齐后，同一套程序才能正确评分",
  "四类信息分别记录动作、订单过程、前态和后态，供不同因子按需使用。",
  "replay"
 ],
 [
  "定义怎样影响因子",
  "配对修正改善了直接分量，下游因子并非一起改善",
  "保留同一批股票上的改前、改后对照，理解公开定义会怎样改变数值。",
  "definition"
 ],
 [
  "早期回放核验",
  "数量守恒通过；外部整秒盘口曾有 302 帧未全等",
  "本页保留早期证据。新增真实沪市适配层验收在第 10 页，二者不能混算。",
  "replay"
 ],
 [
  "三种比较分开",
  "改定义会改分数；适配器同条件对照为零差异",
  "分开比较定义、适配路径和消息时钟，才能知道变化来自哪里。",
  "evidence"
 ],
 [
  "输入修正的影响",
  "修正输入问题后，已验收的因子值没有变化",
  "输入更可靠不等于因子收益表现改善；这里报告实际数值核对。",
  "evidence"
 ],
 [
  "换时钟影响多少",
  "单日多数排序稳定，跨日仍有阈值附近的尾部",
  "下面是 2026-06-30 的 352 列历史对照；f26 的跨日例子在第 13 页。",
  "clock"
 ],
 [
  "真实沪市输入验收",
  "13 日分层验收，支持输入工程收尾",
  "能进入下一阶段，是因为公开输入有明确含义、独立核对和逐日准入规则。",
  "status"
 ],
 [
  "剩余差异怎样处理",
  "查清原因后，分别修复、约束和保留差异",
  "公开记录能确定的继续核准；原始信息多解时，明确使用哪个公开定义。",
  "gap"
 ],
 [
  "340 列独立定参",
  "复用最近深市流程，用沪市样本重新定参数",
  "340 列、八组结构参数；第六核绑定本期沪市 θ_bbo 已获批准。",
  "next"
 ],
 [
  "f26 门槛与尾部",
  "小幅跨过门槛，也可能让整组失去观察资格",
  "用一笔真实诊断案例解释为何总体稳定仍需检查尾部，以及报告怎样交付。",
  "f26"
 ],
 [
  "交付与待办",
  "单日工程试算已通过，全期参数仍待后续签收",
  "输入验收、参数签收、正式因子计算分别登记，不能相互替代。",
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
 ['方法已定','批准范围与第六核绑定','340 列及 f26 诊断用途已确认；第六核绑定本期沪市 θ_bbo 已获批准；实施授权限定代码修复、小样本和 P75 试算。'],
 ['核与输入','已有接线与单日取样验证','按最近深市的全局候选与三级中位数流程取样。五项独立估计、一个派生字段；不借深市数值。'],
 ['单日试算','结构支持与 F40 已核对','F40 继续四阶段、一次匹配；七组共享，λ42 按 px/act 各自公开动作分开估。'],
 ['全期定参','尚未获准启动','来源错误报错，空正样本停下；运行包、代码与数据身份可复核，f26 随包交付诊断。'],
 ['正式因子','参数签收之后再推进','先核对代表样本和单日全市场，再按另行确认的范围计算历史面板；收益与 IC 属于下游研究。']
];
function nextDiagram(){return `<div class="visual"><h3>三种检查，合起来支持输入交付</h3><div class="table-wrap"><table class="book report-comparison"><thead><tr><th>检查</th><th>结果</th><th>能够说明什么</th></tr></thead><tbody><tr><td>真实沪市分层接入</td><td>13 日 · 1,335 股票日通过<br>4 个阶段排除 · 0 适配错误</td><td>主板与科创板、不同活跃度和时期，均能按公开合同构造输入。</td></tr><tr><td>另写账本独立核对</td><td>104 股票日<br>67,862,452 次字段比较，0 差异</td><td>直接从原始字段复算，核对价量、前后态与生命周期，避免程序自己证明自己。</td></tr><tr><td>每笔订单的交付检查</td><td>6,614,949 笔窗口订单<br>未闭合订单 0</td><td>可见数量、首次公开时间和初始段闭合，能作为下游一致的输入。</td></tr></tbody></table></div></div><div class="boundary"><b>为什么现在可以推进？</b><p>独立定参需要一套含义固定、来源可查、能够复核的输入。当前输入已满足这项前提；原始限价或类型仍有多解，不妨碍按公开定义估计参数。</p><p>但 13 日样本没有验过整个 601 日全市场。后续每个日期仍须过同样的来源和输入检查；新错误必须报错，不能算作排除项。</p></div><div class="controls">${btn('scene',10,'看还有哪些取舍',false,'secondary')}${btn('scene',11,'看 340 列定参计划',false,'secondary')}</div>`;}
const history=[['9 月底','划清公开信息边界','盘口与可见数量可以重建；部分原始限价、类型和隐藏余量不能唯一确定。'],['10-14','核对隐藏属性估计','留出比较未支持把模型猜出的限价当成真值，继续使用可核验公开事实。'],['10-21','固定公开定义','明确挂出余量、即时执行、公开数量和价格分别怎样进入因子。'],['10-22','修正配对并量化变化','直接分量改善，下游并非同步接近原定义；分别保留差异证据。'],['10-23','接通路径并拆分误差','真实沪市借参冒烟跑通；同条件适配器零差异，消息时钟另行对照。'],['10-24','完成差异归因与输入交付','残差有具体解释；真实沪市 13 日分层输入验收通过，前置项目收尾。'],['10-25','审阅单日工程试算与优化','按最近深市流程准备 340 列、八组方案。f26 交诊断；第六核绑定已批准，P75 工程试算已通过，正式计算未启动。']];
function overviewDiagram(){return `<div class="visual"><h3>现在完成到哪里</h3><div class="table-wrap"><table class="book report-comparison"><thead><tr><th>阶段</th><th>当前状态</th><th>下一步所需条件</th></tr></thead><tbody><tr><td>公开委托与盘口输入</td><td><b>已完成约定范围验收</b><br>13 日、1,335 股票日；独立账本 104 股票日</td><td>把固定定义、来源和逐日检查一起交给下游。</td></tr><tr><td>沪市定参工程试算</td><td><b>单日工程试算已通过</b><br>340 列、八组；第六核方法已批准</td><td>接线与单日试算已有结果；601 日全期来源、空间和执行方案验收后，另行申请正式运行。</td></tr><tr><td>601 日正式定参与因子研究</td><td><b>尚未启动</b></td><td>全期参数签收后再推进正式面板；收益和 IC 不参与此次定参。</td></tr></tbody></table></div></div><div class="boundary"><b>可以推进的理由：所需输入已经定下来了。</b><p>公开成交、挂出量、订单身份和动作前后盘口都有核验依据。无法唯一恢复的原始限价与类型，改用明确的公开行为定义，并保留与深市原定义的差异。</p><p>“输入正确”不等于“沪深分数相同”，也不等于“因子已有预测能力”。后两件事分别属于定义比较和下游研究。</p></div><div class="controls">${btn('scene',9,'查看真实沪市验收',false,'primary')}${btn('scene',10,'查看差异与取舍',false,'secondary')}${btn('scene',11,'查看定参计划',false,'secondary')}${btn('scene',12,'查看 f26 尾部案例',false,'secondary')}</div><p class="fine">保留 10 月 23 日原有图表与六个案例；交付证据补充至 10 月 24 日，授权与工程试算状态核对至 10 月 25 日。</p>`;}
function historyDiagram(){const h=history[state.history];return `<div class="timeline">${history.map((h,i)=>btn('history',i,`<strong>${h[0]}</strong><b>${h[1]}</b><small>${h[2]}</small>`,state.history===i)).join('')}</div><div class="inspector"><h3>${h[0]} · ${h[1]}</h3><p>${h[2]}</p><div class="pending-list"><span>已交付：公开输入合同、多日独立核对、残差归因</span><span>已决定：340 列；f26 交诊断，不单独阻断参数签收</span><span>已批准并实施：第六核绑定、代码修复、小样本及 P75 工程试算</span><span>待授权：601 日正式定参；参数签收后再推进正式因子面板</span></div></div><div class="next-band"><p><b>验收与版本身份</b><br>真实沪市输入验收运行版本 8b73fa72，交付报告 ca151e45；差异归因报告 4dd76371。最近深市方法以 601 日核和 10 月 24 日 F40 完整签收为基准，旧版本仅作历史参考。</p><div class="controls"><button class="secondary" data-action="performance">查看历史耗时与工程边界</button>${detailButton('reference','查看原始报告与版本身份')}${detailButton('next','查看参数方法与验收细节')}</div></div><p class="fine">本次审阅只读核对了会话、源码、持久结果和原始计时凭证；没有启动取数、回放、正式定参或因子计算。</p>`;}
function gapDiagram(){return `<div class="visual"><h3>困难对应三种处理方式</h3><div class="table-wrap"><table class="book report-comparison"><thead><tr><th>遇到的问题</th><th>当前处理</th><th>接受的边界</th></tr></thead><tbody><tr><td>行情拆成成交与余量；前后盘口、价格或数量可能接错</td><td>合并逻辑订单，核对守恒；用独立账本、同条件回环检查</td><td>可核验的错误要修复，不能靠放宽容差消掉。</td></tr><tr><td>多个原始限价或类型能生成同一公开记录</td><td>按显示价、初始执行价代理、可见量和首公开时间计算</td><td>接受公开定义与原定义的数值差异，不把代理当成隐藏真值。</td></tr><tr><td>消息距离近似、硬门槛与窗口尾部互相作用</td><td>保留正式观察规则，单独检查门槛附近和尾部</td><td>已解释的敏感性仍需报告；不为了追平分数越过观察窗口。</td></tr></tbody></table></div></div><p>排队分量的 5,439 条贡献记录已全部归因；f76/f78 的 11 笔订单也已定位。这里的“归因完成”指知道变化从哪里来，数值差异仍然存在。</p><div class="boundary"><b>零分、未知、不适用、观察不足、来源错误分开记录。</b><p>单侧盘口可能合法；某个因子需要双侧报价时，再按该因子的资格规则处理。没有依据的值不能统一补零，来源错误也不能统一改成缺失。</p></div><p class="fine">特定重股的四条公开路径由约 1,573 / 1,313 秒降至约 44 / 45 秒，逐位结果不变。说明已修复重复扫描；不把它当成全市场速度。</p>`;}
function pilotReviewDiagram(){return `<div class="visual"><h3>本次审阅核对的单日试算</h3><p><b>2026-06-30 · 2,296 股 · 100.234 秒 · 执行版本 143d9bb8</b></p><p>逐股核统计、结构支持及 px/act 支持身份与已验收基准一致；F40 事实哈希和四阶段分位数一致。持久恢复凭证确认 41,328 个支持数组、2,296 份 F40 事实恢复通过。</p><p>本日 θ_bbo 与派生 θ_mkt 均为 5.770780…，只是工程试算值。结果明确标为“仅工程验证”，601 日正式定参未启动，正式因子计算为 0。</p><p class="fine">P75 来自 13 个认证日期的事件量排序；不是 601 日耗时分位数。100.234 秒使用认证热页、同源频道索引和已准备的编译缓存，保留热输入供连续试跑；包含完整持久回读，未包含首次冷准备与最终热输入退役。60 秒目标在本次审阅版本尚未达到。</p></div>`;}
function methodDiagram(){const c=calibration[state.calibration];return `${pilotReviewDiagram()}<div class="visual"><h3>340 列怎样与深市对齐</h3><p>深市当前 344 列，减去沪市停用的 dm03/dm04 四列，得到 340 列。原 352 列能力清单中的 12 列不进入此次定参：六列仅由 Z12 服务，另六个方向结构恒零，因此 Z12 整组退出。</p><p>基准是最近的 601 日全局核、八组结构参数、F40 四阶段且只匹配一次。采样期为 2024-01-02 至 2026-06-30；全市场共用尺度，不读取收益或 IC。</p></div><div class="calibration">${calibration.map((c,i)=>btn('calibration',i,`<span>0${i+1}</span><b>${c[0]}</b><small>${c[1]}</small>`,state.calibration===i)).join('')}</div><div class="inspector"><h3>${c[0]}：${c[1]}</h3><p>${c[2]}</p>${calibrationIllustration()}</div><div class="boundary"><b>第六核已批准：θ_mkt = 同一沪市包的 θ_bbo。</b><p>深市特殊通道在公开沪市输入里没有正距离样本，不能照搬。以当前公开报价距离作共同标尺，明确登记“五项独立估计＋一项派生”，而不是声称第六项已独立估出。</p><p>这个尺度同时服务 px 与 act。只用旧单在新动作前的距离，更贴近 act 的一个分支，却不能代表全部消费者。最新深市两个值恰好相等，也不是采用绑定的充分理由。</p></div><details class="method-details"><summary>展开八组参数的样本、算法与验收要点</summary><p>P50 为中位数；P05、P99 分别描述分布低端与高端。各组沿用自己的资格与权重。</p><div class="table-wrap"><table class="book report-comparison"><thead><tr><th>参数</th><th>怎样定</th><th>怎样验收</th></tr></thead><tbody>${DATA.calibration_groups.map(row=>`<tr>${row.map(c=>`<td>${esc(c)}</td>`).join('')}</tr>`).join('')}</tbody></table></div></details><p class="fine">沪市输入入口、λ42 公开动作、尺度与版本缓存键、报价单位及响应模板接线已在工程试算中核对。后续优化版本仍须各自通过精确对照。单日试算不是全期参数；正式运行前继续核对来源、空间与跨期两遍输入方案。</p>`;}
function f26Diagram(){return `<div class="visual"><h3>300187 · 2024-10-08：变化发生在哪里</h3><ol class="diagnostic-flow"><li>消息距离<br>114,216 → 114,125</li><li>跨过连接门槛<br>约 114,141</li><li>两组订单<br>合并为一组</li><li>组结束移到<br>09:34:57.94</li><li>只剩 2.06 秒<br>不足所需 8.97 秒</li></ol><p>合并后的组仍有正的聚类分数，但已没有足够后续观察；按正式窗口规则排除后，股票因子从约 0.0015053 变为 0。</p><p class="fine">这是深市模拟公开对照的诊断案例，使用当时冻结参数；不是真实沪市定参结果。消息差约 0.08%，不能因为很小就认定不会改变分组。</p></div><div class="visual"><h3>拟交付的诊断，先做这三件事</h3><div class="table-wrap"><table class="book report-comparison"><thead><tr><th>检查</th><th>怎样做</th><th>为什么这样做</th></tr></thead><tbody><tr><td>基准余量</td><td>统计连接边离门槛多近、组结束离观察截止点多近；列尾部 5/10/20/30 秒</td><td>直接找出容易翻转的样本，不只看全市场相关。</td></tr><tr><td>四次扰动</td><td>时间核 ±5%，消息核 ±5%；每次只改一项，复用输入，只重算聚类与 f26</td><td>测参数敏感性；不把 ±5% 冒充实际时钟误差。</td></tr><tr><td>深市对照</td><td>用最近深市冻结参数做同样检查</td><td>区分定义本身的敏感性与沪市移植额外引入的问题。</td></tr></tbody></table></div></div><div class="boundary"><b>用户已确定：随参数交付诊断，不单独阻断参数签收。</b><p>若发现实现错误、读取未来信息或参数没有生效，仍须修复；若只是正式定义固有的敏感性，则如实披露，供后续使用 f26 时判断。</p></div>`;}
const renderers=[overviewDiagram,orderDiagram,ambiguityDiagram,pipelineDiagram,definitionDiagram,proofDiagram,routeDiagram,fixesDiagram,clockDiagram,nextDiagram,gapDiagram,methodDiagram,f26Diagram,historyDiagram];
