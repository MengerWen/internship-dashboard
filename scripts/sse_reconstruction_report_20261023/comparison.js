const routes = {
  semantics:['1. 改因子定义','深市原始属性 vs 公开可见信息：定义改变后，得分差多少？','综合行为得分相关：价格版 0.962589，可成交性版 0.961794','在 14,079,004 笔共同订单上计算。每笔订单得分最高的行为组，分别有 8.7054% / 8.8362% 与深市原定义不同。','这说明公开信息替代隐藏属性后，分数和行为判断会变。这些是当前公开定义的总体差异，包含此前多项定义调整，不能全部归因于第 5 页的配对修正；相关性也不是收益预测能力。'],
  input:['2a. 查输入是否一致','保持定义、消息时钟和参数相同：两条路径送进程序的信息一样吗？','2,888 只股票：参与业务计算的输入字段全部一致','发生的动作共 28,770,858 行，整笔订单过程共 14,079,004 行，动作前和动作后状态各 34,545,742 行。它们保证程序拿到的是同一批订单、价格、数量和状态。','按约定排除股票 302132。仅放行已证明不影响本次因子输出的 3 个表示字段及 7 个来源标记；消息序号和本次修正的业务字段都必须严格相同。'],
  engine:['2b. 查因子是否一致','输入条件相同：经过适配器，会不会把因子额外算出差异？','价格版 1,016,576 个值、可成交性版 10,560 个值，差异均为 0','价格版覆盖 2,888 只股票 × 352 列；可成交性版覆盖分层抽样的 30 只股票 × 352 列。两边有限数值的二进制表示完全相同，双方同为缺失也按合同视为一致。','这证明适配器在所测日期和样本中正确实现了同一套公开定义。真实沪市行情的核验、其他交易日是否准入，仍需要各自的证据。'],
  clock:['3. 只换消息时钟','价格、数量、盘口、实际时间和参数不变：公开消息间距会让因子变多少？','272 / 352 列至少一股变化，80 列逐位不变','最明显的例子是买侧排队稀释响应 f43：99% 分位误差为 0.052425 个全市场尺度，最大为 0.170156。所有列的有限 / 缺失状态变化均为 0。','改变的是两次动作相隔多少条消息。这个间距进入衰减权重、配对窗口和响应选择，所以顺序相同仍可能改变分数。此处保持原参数不变，并关闭额外的间距缩放；是否接受误差还需结合业务要求。']
};

function routeDiagram() {
  const r=routes[state.route];
  const controls=`<div class="segmented" aria-label="比较条件">${Object.entries(routes).map(([k,v])=>btn('route',k,v[0],state.route===k)).join('')}</div>`;
  const picture=state.route==='semantics'?`<div class="definition-compare"><div><span>深市原定义</span><b>原始类型、报单价和委托量</b><p>用深市可取得的原始信息计算，作为定义比较的参照。</p></div><span class="big-arrow">→</span><div><span>公开信息下的定义</span><b>公开成交价、挂出价和可见总量</b><p>无法看到的属性由公开事实替代，配对资格和得分规则也随之明确。</p></div></div>`:
    `<div class="route-graph"><div class="route-start">同一份深市数据<br><small>原始信息已知</small></div><div class="route-lanes"><div class="route-lane"><button data-action="evidence" data-value="evidence" class="${state.route==='input'?'active':''}">参照路径 S<br>直接整理公开信息</button><button data-action="evidence" data-value="clock">原始消息间距<br>作为对照</button></div><div class="route-lane"><button data-action="evidence" data-value="replay" class="${state.route==='input'?'active':''}">适配路径 H<br>模拟沪市消息后重建</button><button class="${state.route==='clock'?'active':''}" data-action="route" data-value="${state.route==='clock'?'engine':'clock'}">${state.route==='clock'?'公开消息间距':'原始消息间距'}<br>点击切换比较</button></div></div><div class="route-end">同一因子程序<br><small>同一组参数</small></div></div>`;
  return `${controls}<p class="comparison-purpose">${r[1]}</p>${picture}<div class="route-result" aria-live="polite"><h3>${r[2]}</h3><p>${r[3]}</p><p class="fine">${r[4]}</p>${state.route==='input'||state.route==='engine'?'<button class="secondary" data-action="whitelist">哪些字段允许不同？查看依据</button>':''}${state.route==='clock'?btn('scene',8,'看逐列误差与实际数值',false,'secondary'):''}</div><p class="scope-note">两条路径都来自同一份深市数据，方便控制变量、逐项找差异；真实沪市试运行的结果见第 10 页。</p>`;
}
