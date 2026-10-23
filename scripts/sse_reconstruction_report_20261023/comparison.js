const routes = {
  semantics:['定义变化','原定义与公开定义：本来就可能不同','深市原生定义 → 沪市公开定义','历史 v5 全市场订单 union 相关：px 0.962589，act 0.961794；族赢家分别有 8.7054% / 8.8362% 改变。','这是信息可见性与定义变化的比较。它不要求数值全等，也不能拿来证明适配器有错。'],
  input:['适配 · 输入','FactorInput：公开定义与真值时钟相同','2,888 只 · 四张表全等','events 28,770,858 行；lifecycle 14,079,004 行；前态、后态各 34,545,742 行。白名单以外逐位一致。','全市场集合按本轮约定排除 302132，纳入 2,888 只。3 个表示列与 7 个精确来源键豁免；科学 seq 和 C2 修正字段不豁免。'],
  engine:['适配 · 引擎','同一公开定义、同一时钟、同一参数','px 1,016,576 个值，差异 0','px 全市场 2,888 × 352；act 样本 30 × 352 = 10,560，差异也为 0。000725 先单独完整跑完，px / act 各 352 列全等。','这里证明本日深市公开回环的适配器正确性，不代替真实沪市报价认证或跨日准入。'],
  clock:['时钟变化','只改 H 的科学序号，量化近似误差','272 / 352 列至少一股变化','价格、数量、盘口和墙钟保持一致，只把 H 的序号换成 Q_equity。没有重新估计参数；κ 关闭。','变化来自消息间距进入衰减与窗口。误差表已给出，是否可接受仍待用户决定。']
};

function routeDiagram() {
  const r=routes[state.route];
  const controls=`<div class="segmented" aria-label="比较条件">${Object.entries(routes).map(([k,v])=>btn('route',k,v[0],state.route===k)).join('')}</div>`;
  const picture=state.route==='semantics'?`<div class="definition-compare"><div><span>深市原生定义</span><b>原始类型 / 委托价格 / 原始数量</b><p>深市可用的原始消息和规则作为真值基准。</p></div><span class="big-arrow">→</span><div><span>沪市公开定义</span><b>公开价格 / Qᵥ / 首次可见效果</b><p>明确替代隐藏信息；候选资格、匹配与分量含义也随之定义。</p></div></div>`:
    `<div class="route-graph"><div class="route-start">深市认证缓存<br><small>已知真值</small></div><div class="route-lanes"><div class="route-lane"><button data-action="evidence" data-value="evidence" class="${state.route==='input'?'active':''}">S：深市直接回放<br>公开事实替换</button><button data-action="evidence" data-value="clock">真值时钟<br>参照路径</button></div><div class="route-lane"><button data-action="evidence" data-value="replay" class="${state.route==='input'?'active':''}">H：重建沪市消息<br>原生适配器</button><button class="${state.route==='clock'?'active':''}" data-action="route" data-value="${state.route==='clock'?'engine':'clock'}">${state.route==='clock'?'Q_equity':'真值时钟'}<br>点击切换检验</button></div></div><div class="route-end">共享引擎<br><small>同一组参数</small></div></div>`;
  return `${controls}<p class="comparison-purpose">${r[1]}</p>${picture}<div class="route-result" aria-live="polite"><h3>${r[2]}</h3><p>${r[3]}</p><p class="fine">${r[4]}</p>${state.route==='input'||state.route==='engine'?'<button class="secondary" data-action="whitelist">查看白名单及静态 / 动态证明</button>':''}${state.route==='clock'?btn('scene',8,'去误差页看分布与逐列统计',false,'secondary'):''}</div><p class="scope-note">三类问题分别是：定义改变多少、适配器是否正确、可用时钟带来多少误差。适配器一项又分输入层和引擎层检查。</p>`;
}
