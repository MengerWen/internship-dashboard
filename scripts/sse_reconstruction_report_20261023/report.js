(() => {
'use strict';
const DATA = JSON.parse(document.getElementById('report-data').textContent);
const app = document.getElementById('app');
const dialog = document.getElementById('evidence-dialog');
const state = {scene:0, view:'story', order:'partial', step:0, reveal:false, pipe:0, family:0, match:'v5', proof:0, route:'input', fix:0, clock:'q', error:'', calibration:0, history:4, case:0};
const esc = value => String(value).replace(/[&<>"']/g, c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const pct = (n,d=3) => n==null?'未定义':(n*100).toFixed(d)+'%';
const num = n => n==null?'未定义':n!==0&&Math.abs(n)<1e-5?Number(n).toExponential(5):Number(n).toLocaleString('en-US',{maximumFractionDigits:7});
const short = column => column.split('__')[0]+' · '+(column.includes('__side_buy')?'买侧':'卖侧');
const btn = (action,value,label,active=false,cls='') => `<button type="button" class="${cls}" data-action="${action}" data-value="${value}"${['scene','case-link','return-story'].includes(action)?'':` aria-pressed="${active}"`}>${label}</button>`;
const detailButton = (key,label='展开字段、限制与原始证据') => `<button type="button" class="secondary" data-action="evidence" data-value="${key}">${label}</button>`;
const tags = label => `<span class="tag real">${label||'实测'}</span>`;
const scenes = [
 ['项目的位置','先看全景：这项工作给下一步交付什么？','把沪市公开消息整理成因子引擎可理解的订单事实，并分清哪些能够还原、哪些只能定义。','position','给后续沪市定参交付经过验收的公开口径、适配器与输入契约。定参和正式因子生产仍是下一阶段。'],
 ['一笔订单的发布','一笔订单，为什么会出现多条消息？','点“下一条消息”，观察成交、挂单和盘口。公开挂单数量不能直接当作原始委托总量。','observable','先明确交易所实际公开了什么，才能判断还原目标是否有唯一答案，也才能避免把残余挂单算成第二笔订单。'],
 ['能还原的边界','同一组公开消息，可能对应几种原始委托？','纯成交订单往往缺少原始价格、类型或未公开余量。回放能对上，不代表隐藏属性猜对了。','observable','研究上的隐藏属性推断，与生产中的公开事实适配分开验收；后续因子使用明确、可复核的公开定义。'],
 ['接入因子引擎','从消息到因子，中间有哪些接口？','点击每个节点，查看它产出什么、为什么需要它。沪深共用引擎，沪市适配器负责输入语义。','replay','输出 FactorInput 的事件、生命周期、前态和后态；统一事实接口后，才能把同一套因子公式在沪市重算。'],
 ['公开因子定义','输入少了隐藏属性，因子怎样保持含义？','352 个源列按可见性分流；匹配、排队、金额与 union 的规则也要一起明确。','definition','把“公式能运行”推进到“数值有明确含义”。这是冻结沪市定参口径之前必须完成的步骤。'],
 ['底座证据','怎样证明盘口与订单事实可靠？','验收分层进行：内部守恒、外部逐档核对、边界例外分别说明。每层证据有自己的覆盖范围。','replay','底座认证说明输入可信到哪一层；既不能用单日冒烟替代多日验证，也不能把逐秒快照核对扩大成亚秒级真值。'],
 ['S / H 回环','怎样把“公开口径改变”和“适配器出错”分开？','同一份深市真值走两条路；先固定时钟验收适配器，再单独更换可用时钟测量误差。','evidence','真值时钟下证明同一公开定义可被适配器完整表达。Q_equity 的误差另行交付，不能混入适配器正确性结论。'],
 ['收尾修正','参照路径本身也要经得起检查','自动撤单、金额标签、价格档位与即时排队位置都回到公开定义独立重算。','evidence','消除参照路径残留的深市隐藏信息。修正输入不等于改深市原生逻辑；原生回归和 v5 输出回归各自验证。'],
 ['消息时钟误差','顺序没变，为什么因子还会变化？','序号之间的距离进入衰减和窗口。切换时钟后，订单价格数量不变，距离却可能变化。','clock','给后续沪市定参提供真实误差表与时钟契约。这里只展示误差，不替用户判断能否接受，也不把高相关当作预测效果。'],
 ['接到定参与生产','下一步不是再“还原一次”，而是独立定参','先冻结输入与时钟，再在沪市样本上估计核参数和结构尺度，签收后才能正式计算因子面板。','next','复用深市已经明确的计算逻辑和执行步骤；沪市参数、样本资格、报价凭证与产出签收独立完成。'],
 ['里程碑与未结项','哪些已经结束，哪些仍要接着做？','把研究探索、公开定义、底座认证、适配器收尾与生产准备放在同一条时间线上。','reference','到 26.10.23，公开输入与真值回环已有证据；独立定参、正式面板和后续 IC 不能提前算作已完成。']
];

const orderCases = {
 partial:{label:'先成交、再挂单', submit:'买入限价 10.03 × 1,000 股', max:2, tokens:[['T','10.00 × 600','首次可见成交'],['A','10.03 × 400','成交后的剩余挂出']], notes:['订单尚未产生公开效果。原始提交只在演示的内部视角可见。','卖一 600 股被吃掉；逻辑订单已出生，不能等 A 消息再算一次出生。','剩余 400 股挂出。公开数量 Qᵥ = 600 + 400 = 1,000；A 是同一订单的余量。']},
 rest:{label:'直接挂出',submit:'买入限价 9.98 × 1,000 股',max:1,tokens:[['A','9.98 × 1,000','未即时成交，直接入簿']],notes:['尚无公开效果。','公开挂单直接建立订单事实；公开挂出价为 9.98。']},
 pure:{label:'只有成交',submit:'隐藏的原始提交：有多个兼容解释',max:1,tokens:[['T','10.00 × 600','公开消息中没有残余 A']],notes:['先隐藏原始属性，只看公开证据。','公开可见数量为 600 股；原始类型、限价及未公开余量仍可能不唯一。']},
 zero:{label:'完全不可见',submit:'无成交、无剩余挂出',max:1,tokens:[],notes:['此处演示没有公开成交，也没有公开挂单的订单。','公开事实表中不凭空建立这笔订单；系统自动取消也不能伪装成投资者公开撤单。']}
};
function orderDiagram(){
 const c=orderCases[state.order],step=Math.min(state.step,c.max),filled=step>0&&(state.order==='partial'||state.order==='pure');
 const newTop=state.order==='partial'&&step===2;
 const newSecond=state.order==='rest'&&step===1;
 const rows=[[filled?'卖一':'卖二','10.05','400',false],[filled?'原卖一 · 已成交':'卖一','10.00',filled?'0':'600',filled],[newTop?'买二':'买一','9.99','500',false],[newTop||newSecond?'买三':'买二','9.97','800',false]];
 if(newTop)rows.splice(2,0,['买一 · 新增','10.03','400',true]);
 if(newSecond)rows.splice(3,0,['买二 · 新增','9.98','1,000',true]);
 return `<div class="segmented" aria-label="订单情形">${Object.entries(orderCases).map(([k,v])=>btn('order',k,v.label,state.order===k)).join('')}</div><div class="split"><div class="visual"><div class="scenario-title"><h3>内部动作与公开消息</h3><span class="tag">示意 · 非真实行情</span></div><div class="trace-lanes"><div class="trace-lane"><span class="label">原始动作</span><div class="trace-stream"><div class="event-empty">${c.submit}</div></div></div><div class="trace-lane"><span class="label">公开消息</span><div class="trace-stream">${c.tokens.length?c.tokens.map((t,i)=>`<div class="event-token ${step===i+1?'current':step<i+1?'future':''}"><b>${t[0]}</b><span>${t[1]}</span><span>${t[2]}</span><span>${step<i+1?'待发布':'已发布'}</span></div>`).join(''):'<div class="event-empty">T：无　　A：无</div>'}</div></div></div><div class="story-control"><button class="secondary" data-action="step" data-value="-1" ${step===0?'disabled':''}>上一步</button><button class="primary" data-action="step" data-value="1" ${step===c.max?'disabled':''}>${step===c.max?'已到最后一步':'下一条消息'}</button><span class="stage-count">${step} / ${c.max}</span></div><p class="readout" aria-live="polite">${c.notes[step]}</p></div><div class="visual"><table class="book"><caption>公开盘口 · 当前步骤</caption><thead><tr><th>档位</th><th>价格</th><th>股数</th></tr></thead><tbody>${rows.map(r=>`<tr class="${r[0].includes('卖')?'ask':'bid'} ${r[3]?'changed':''}"><td>${r[0]}</td><td>${r[1]}</td><td>${r[2]}</td></tr>`).join('')}</tbody></table><div class="property-row"><div class="property"><b>t₀ 的含义</b>首次公开效果的位置</div><div class="property"><b>Qᵥ 的含义</b>首次成交 + 剩余挂出</div></div><p class="fine">T = 成交；A = 公开挂单。价格与数量仅用于解释消息机制。</p></div></div>`;
}
function ambiguityDiagram(){
 return `<div class="visual"><div class="same-evidence"><span>只看到这组证据</span><span class="print">T：10.00 × 600 股</span><span>没有 A 消息</span></div><div class="hypotheses">${[['限价 10.00','委托 600 股','全量成交'],['限价 10.02','委托 600 股','同样在 10.00 成交'],['带保护价的即时成交剩余撤销','委托 1,000 股','成交 600，未公开余量取消']].map((r,i)=>`<div class="hypothesis ${state.reveal?'reveal':''}"><b>兼容解释 ${i+1}</b><p>${state.reveal?r[0]:'隐藏的原始类型 / 价格'}</p><p>${state.reveal?r[1]:'隐藏的原始数量'}</p><div class="value">${state.reveal?r[2]:'？'}</div></div>`).join('')}</div><div class="controls">${btn('reveal','',state.reveal?'重新隐藏原始解释':'揭开三个兼容解释',state.reveal,'primary')}<span class="fine">机制示意；具体委托类型与资格仍受交易规则约束。</span></div></div><div class="fork" style="margin-top:22px"><div class="branch"><span class="tag">研究线 · 隐藏属性推断</span><h3>能猜到多少，要独立实测</h3><div class="path-step">v2 加入约束与正则，并未优于 v1</div><p>深市留出日价格准确率：82.7566% → 82.5314%；误差：2.8604 → 2.9208 ticks。</p></div><div class="branch selected"><span class="tag">实施线 · 公开事实</span><h3>定义公开可复核的替代量</h3><div class="path-step">公开数量、首次效果、挂出价、成交深度</div><p>不要求猜对每一项隐藏属性，转而检查输入定义和因子含义是否一致。</p></div></div>`;
}
const pipes=[
 ['原生回放','sse-native-resting-v2','按原生 A / T / D 语义更新订单簿，合并首次成交与残余挂出，保持同一订单身份。','公开消息 → 订单与盘口状态'],
 ['公开订单事实','public_order_facts','只根据公开效果确定 Qᵥ、t₀、公开价格与动作；零可见量订单不进入事实表。','盘口状态 → 公开订单事实'],
 ['统一输入','FactorInput','事件、生命周期、动作前态、动作后态同时表达同一公开口径。生产入口直接使用显式输入。','四张语义一致的表 → 引擎接口'],
 ['共享因子引擎','px / act','复用因子公式、窗口、匹配与聚合。市场差异留在公开输入和独立定参中。','统一输入 + 冻结参数 → 因子向量']
];
function pipelineDiagram(){const p=pipes[state.pipe];return `<div class="pipeline">${pipes.map((p,i)=>btn('pipe',i,`<strong>${p[0]}</strong><small>${p[1]}</small>`,state.pipe===i,'pipe-node')).join('')}</div><div class="split"><div class="inspector"><h3>${p[0]}：为什么需要这一层</h3><p>${p[2]}</p><div class="boundary">${p[3]}</div><p class="fine" style="margin-top:15px">历史上的 sse_to_szse_tables 是转换试验路径；当前正式适配器直接构造 FactorInput。</p></div><div class="visual"><h3>同一输入的四个切面</h3><div class="schema">${[['events','何时发生何种公开动作'],['lifecycle','这一订单的一生与公开属性'],['event_prestate','动作发生前的盘口、排队与参考量'],['event_poststate','动作更新后的价格与状态']].map(r=>`<div class="schema-row"><b>${r[0]}</b><span>${r[1]}</span></div>`).join('')}</div></div></div>`;}
const families=[['46','直接可比','公开信息足以支撑原定义，仍需通过统一输入和逐列验收。'],['40','定义调整','缺少原始隐藏属性时，明确改用公开价格、数量或可观察行为。'],['254','公开替代','形成公开候选量；名称与身份区分原始口径，不能自动当作原因子真值。'],['12','停止 / 排除','包括不满足公开定义或既定禁用规则的列；禁用身份不能借迁移自动恢复。']];
function matchingDiagram(){const old=state.match==='v4';return `<div class="segmented">${btn('match','v4','匹配前排除纯成交订单',old)}${btn('match','v5','先匹配，再计算公开贡献',!old)}</div><div class="split"><div class="visual"><h3>同一旧单，两个候选新单</h3><svg class="matching-graph" viewBox="0 0 680 260" role="img" aria-label="旧单 O 优先选择纯成交 N1；预先删除 N1 会错误转配给 N2"><path d="M200 130 L440 65" class="${old?'discarded':'chosen'}"/><path d="M200 130 L440 195" class="${old?'chosen':'inactive'}"/><rect x="25" y="93" width="175" height="75" rx="2" class="focus-node"/><rect x="440" y="25" width="215" height="80" rx="2" class="node"/><rect x="440" y="155" width="215" height="80" rx="2" class="node"/><text x="58" y="136">旧单 O</text><text x="464" y="58">N1：纯成交</text><text x="464" y="86">更优候选</text><text x="464" y="187">N2：有挂出</text><text x="464" y="215">次优候选</text></svg><p class="fine">机制示意：线条表示匹配选择，不表示实测得分。</p></div><div class="inspector"><h3>${old?'候选集变了，匹配结果也会变':'保留竞争关系，再落实公开口径'}</h3><p>${old?'先删 N1，会让原本输掉的 N2 获得匹配，进而生成原本不应出现的 priority-worse 贡献。':'N1 参与匹配并胜出；随后按纯成交订单的公开规则给出零贡献，不能再把匹配转给 N2。'}</p><div class="equation">${old?'O → N2 → 额外贡献':'O → N1 → 公开贡献 0'}</div><p class="fine">这是 v5 收紧的匹配边界，影响响应族及 union 中依赖这些候选的列。</p></div></div>`;}
function definitionDiagram(){return `<div class="family-map">${families.map((f,i)=>btn('family',i,`<strong>${f[0]} 列</strong><span>${f[1]}</span>`,state.family===i,'family')).join('')}</div><p class="readout" aria-live="polite">${families[state.family][2]} 164 个共用身份 + 188 × px / act = 540 个候选身份，不能据此称为 540 个正式生产因子。</p><div class="union-output"><div><b>px：公开成交价格</b><p>按公开执行价判断追价等行为</p></div><div class="connector">≠</div><div><b>act：实际可成交性</b><p>按动作时对手最优价判断侵入</p></div></div>${matchingDiagram()}<p class="scope-note">union A 共 57 个成员，分为 L5 / P10 / C13 / R29 四族；f14、f15、f16 的价格优先代理及 f32、f35、f51 等独立处理。union 分数不是算法交易概率。</p>`;}
const proofs=[
 ['内部一致性','事件与数量是否自洽','13 个交易日 · 29,622 股票日','180,519,830 条事件；31,372,036 个初始段的时间跨度全部为 0；29,620 个完整 W5 样本的守恒差异为 0。','内部不变量可以排除漏合并、双计与数量不守恒；它自身不提供隐藏属性的交易所真值。'],
 ['外部盘口','价格、数量、队列能否对上','29,135 组开盘价格 / 数量全等','逐秒唯一状态有 268,421 / 268,723 帧一致；队列核对 437,358 组全部一致，但队列仅覆盖两个交易日。','逐秒与开盘签收不等于亚秒级快照认证；纯 FIFO 的外部证据仍较弱。'],
 ['边界资格','哪些股票日不能直接纳入','全股票日排除，不只删异常行','前 5 分钟出现 phase ≠ 3 时排除该股票日。四组 phase=8 现象暂按临停理解，官方代码含义仍未完全核实。','同时间戳相邻全撤仍按普通撤单处理；“股票内回放完整”与“源消息没有缺失”是两项不同检查。']
];
function proofDiagram(){const p=proofs[state.proof];return `<div class="split"><div class="layer-list">${proofs.map((p,i)=>btn('proof',i,`<b>${p[0]}</b><span>${p[1]}</span>`,state.proof===i)).join('')}</div><div class="visual proof-detail">${tags()}<h3 style="margin-top:13px">${p[1]}</h3><div class="result">${p[2]}</div><p>${p[3]}</p><div class="boundary">${p[4]}</div></div></div><div class="metric-line"><div><b>7,477</b><span>截断边界已闭合的样本</span></div><div><b>6 / 23</b><span>虚拟集合竞价价格 / 数量差异数</span></div></div>`;}
const fixes=[
 ['自动撤单','437 行','0 行','16 只股票中的零可见量订单不在公开事实表，却因 removed_cancel_seq 未生效，留下自动撤单。','按 v6 自动撤单判断，从 S 的事件、前态、后态一起删除；不删除真实投资者公开撤单。'],
 ['金额标签','same_side_bbo / opponent_bbo','submit_price','被替换订单已统一为公开价格上的 L，但标签仍沿用原始隐藏类型。','生命周期、前态和后态一并改为公开提交价标签，使标签与真实使用的价格一致。'],
 ['价格档数量','113,500','0','实样 000333 / seq 4809671：公开卖单价 782700，动作前最优卖价 783800；该公开价格上不可能挂着卖量。','S 在原始价格上取量，违反公开定义。按本侧、公开价格和动作前状态独立重算；H 的 0 符合这一实样。'],
 ['后态价格','101900 / 0','102100','实样 000001 / seq 588089：S 与 H 原先都可能错误；该订单自己的执行记录支持 102100。','两条路径分别根据自己的成交记录确定后态 price_tick，不能拷贝对方数值。000333 / seq 590368 则是 S 正确、H 的 0 错误。'],
 ['即时排队量','NA','0','即时动作尚未形成在簿等待位置，不能把不存在的先到订单量记为缺失。','qty_ahead_pre：S 的 NA 违反即时出生定义，H 的 0 正确；统一由动作状态推导。'],
 ['新参考回归','旧参考 472 / 1,720 不等','新参考两次全等','旧参考早于 10-21 排队余量、f16 即时成交、DM 分母三项决定。472 项均落在决定影响范围，范围外为 0。','五只股票各 352 列，对 r2 / v5 在 C2 前后均逐位一致。472 项对应 124 个不同列身份，均在排队余量决定的传播范围内。']
];
function fixesDiagram(){const f=fixes[state.fix];return `<div class="segmented">${fixes.map((f,i)=>btn('fix',i,f[0],state.fix===i)).join('')}</div><div class="split"><div class="visual"><h3>${f[0]}：定义决定取值</h3><div class="sample-compare"><div class="sample-value"><span>修正前 / 旧参照</span><b>${f[1]}</b></div><div class="sample-value fixed"><span>独立核对后</span><b>${f[2]}</b></div></div><p class="readout">${f[3]}</p><p class="fine">价格样本均为原始整数价格单位；此处不擅自换算为元。</p></div><div class="inspector"><h3>根因与修正方式</h3><p>${f[4]}</p><div class="boundary"><b>输入修正后，输出有没有变？</b><p>相对 v5 全市场签收，px / act 各在 2,888 只股票上变化列数 0、受影响股票数 0。12 个独立盘口样本全部符合定义。</p></div></div></div><p class="scope-note">需要更新的是此前“输入层一致”的陈述与参照构造方式；v5 数值签收在这次修正后未改变。深市原生默认也通过修正前后的新参考回归。</p>`;}
const sortedErrors=DATA.errors.filter(r=>r.scaled_p99!=null).sort((a,b)=>b.scaled_p99-a.scaled_p99);
if(!state.error)state.error=sortedErrors[0].column;
const calibration=[
 ['冻结输入','先固定“在什么上面算”','冻结公开定义、Q_equity 契约、股票日资格与报价 / universe 凭证。旧六组报价契约已有签收，当前正式路径仍须绑定可用凭证。'],
 ['六类核参数','分别量出沪市尺度','wall_seconds、events、qty、price_ticks、bbo_ticks、marketability_ticks；沪市独立估计，不把深市参数冒充沪市结果。'],
 ['结构尺度','匹配窗口与行为锚点','九组结构尺度：f16、f31、f40、λ40、λ42、f85、λRV、z12、p03。结构 / F40 的独立任务进展应另行核实，不并入本项成果。'],
 ['冻结签收','把参数变成可复现契约','发布带代码版本、样本资格、统计口径与来源的参数工件；XSHG 的结构、核参数、报价及 universe 必须形成完整凭证链。'],
 ['正式因子面板','再接标签与 IC','按冻结输入与参数正式批量计算、检查覆盖率 / 缺失 / 性能，签收面板后再接标签、IC 与研究评估。当前尚未完成这些步骤。']
];
function nextDiagram(){const c=calibration[state.calibration];return `<div class="visual"><h3>真实沪市冒烟：已经证明了哪一层？</h3><div class="coverage-strip" aria-label="px 2296成功，14排除，0失败"><span style="flex:2296"></span><span class="excluded" style="flex:14"></span></div><div class="metric-line"><div><b>2,296 / 2,310</b><span>px 成功 / 股票池；14 因 phase 排除</span></div><div><b>29 / 30</b><span>act 成功；1 排除；失败 0</span></div><div><b>456.83 秒</b><span>批次；约 15.96 核 / 46.04 GiB</span></div></div><p class="fine">实测日期 2026-06-30。冒烟借用了冻结深市 R19 参数，只证明流程能跑；不能充当沪市定参签收或正式生产。输入已退役，本次仅引用既有证据。</p></div><div class="calibration">${calibration.map((c,i)=>btn('calibration',i,`<span>0${i+1}</span><b>${c[0]}</b><small>${c[1]}</small>`,state.calibration===i)).join('')}</div><div class="inspector"><h3>${c[0]}：${c[1]}</h3><p>${c[2]}</p>${calibrationIllustration()}${state.calibration===2?'<p class="fine">例如 f40：episode P99、anchor P99.9、path P50；f85 和 z12 为正值加权中位数，不再除 ln 2。旧 10-10 计划的输入版本与部分统计口径已过时。</p>':''}<p class="fine">已有 XSHG 601 个交易日（2024-01-02 至 2026-06-30）、1,370,521 股票日 universe。样本范围存在，不等于所有正式凭证和参数已签收。</p></div>`;}
const history=[['9 月底','划定可识别边界','确认公开事实与隐藏原始属性的边界；研究推断与公开方案分别推进。'],['10-14','独立研究 v2','建立规则可行集、概率模型与独立留出；点估计未优于简单基线。'],['10-21','公开 v3 与深市修订','形成公开候选与替换层；排队余量、f16 即时成交、DM 分母三项决定落地。'],['10-22','原生 v2 与公开 v5','推进原生认证，明确优先 / 响应 / union 的匹配和贡献次序。'],['10-23','冒烟与适配器收尾','清理参照、证明白名单，完成全市场真值回环，量出 Q_equity 误差。']];
function overviewDiagram(){return `<div class="stage-road"><div class="road-node"><small>前序 · 深市</small><strong>规则、公式、引擎</strong><p>先确定订单生命周期、排队与因子公式，再通过深市默认向量回归保护既有结果。</p><div class="node-links">${btn('scene',3,'看共享接口')}${btn('scene',7,'看默认回归')}</div></div><div class="road-node current"><small>当前 · 沪市原始委托还原</small><strong>公开事实 → 统一输入</strong><p>承认隐藏原始属性不总能唯一恢复；对公开可见的订单事实、适配器与时钟分别验收。</p><div class="node-links">${btn('scene',1,'用一笔订单理解')}${btn('scene',6,'看 S / H 回环')}</div></div><div class="road-node"><small>后续 · 沪市因子重算</small><strong>独立定参 → 正式面板</strong><p>固定公开口径和样本资格，在沪市独立估计参数，签收后再做因子计算与研究评估。</p><div class="node-links">${btn('scene',9,'看下一阶段五步')}</div></div></div><div class="status-grid"><div class="status-item"><b>输入 / 引擎适配已有签收</b><p>真值时钟：2,888 只股票公开输入全等；px 全市场、act 30 只数值全等。</p></div><div class="status-item"><b>时钟误差已单独量出</b><p>272 列变化；误差表、尺度与秩相关已给出，接受与否仍待决定。</p></div><div class="status-item"><b>沪市正式定参尚待推进</b><p>冒烟使用借用参数；正式参数、面板与 IC 还没有由本项工作完成。</p></div></div>`;}
function historyDiagram(){const h=history[state.history];return `<div class="timeline">${history.map((h,i)=>btn('history',i,`<strong>${h[0]}</strong><b>${h[1]}</b><small>${h[2]}</small>`,state.history===i)).join('')}</div><div class="inspector"><h3>${h[0]} · ${h[1]}</h3><p>${h[2]}</p><div class="pending-list"><span>已完成：公开输入、适配器真值回环</span><span>已量化待决定：Q_equity 时钟误差</span><span>待落实：正式报价凭证与冻结契约</span><span>待开展：沪市独立定参、面板与 IC</span></div></div><div class="next-band"><p><b>版本与运行状态</b><br>业务 f6592c06；补充 8de2ca87；报告定稿 2a0dac94。既有记录分别核实本地提交、GitHub、wenjie 同步与业务运行。</p><div class="controls"><button class="secondary" data-action="performance">性能、运行边界与存储</button>${detailButton('reference','报告、证据与完整版本')}</div></div><p class="fine">本页以截至 2026-10-23 的既有项目证据为准；正式沪市定参、因子面板和 IC 属于后续独立工作。</p>`;}
const renderers=[overviewDiagram,orderDiagram,ambiguityDiagram,pipelineDiagram,definitionDiagram,proofDiagram,routeDiagram,fixesDiagram,clockDiagram,nextDiagram,historyDiagram];
