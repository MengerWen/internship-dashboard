const {test} = require('node:test');
const assert = require('node:assert/strict');
const {placeCards, placeChainCards, attachment, segmentHits, routeLeader, roundedPath} = require('../site/js/journal-notes.js');

const bounds = {left: 96, right: 1248, top: 10, bottom: 1000};
const cards = [170, 280, 308, 510, 650, 678, 790, 1050, 1194].map((anchorX, i) => ({id: `task-${i}`, anchorX, w: 180 + i % 3 * 17, h: 112 + i % 4 * 13}));
function checkPlacement(result, anchorY) {
  for (const r of result.cards) {
    assert(r.x >= bounds.left && r.x + r.w <= bounds.right);
    assert(r.y >= bounds.top && r.y + r.h <= result.height);
    assert(r.y + r.h < anchorY - 20 || r.y > anchorY + 20, '浮窗不能覆盖当天点位');
  }
  for (const [i, a] of result.cards.entries()) for (const b of result.cards.slice(i + 1)) {
    assert(a.x + a.w <= b.x || b.x + b.w <= a.x || a.y + a.h <= b.y || b.y + b.h <= a.y, `${a.id} / ${b.id} 重叠`);
  }
}

test('九项工作与相邻点位的浮窗均避让，保留原锚点', () => {
  const before = JSON.stringify(cards);
  const result = placeCards(cards, {bounds, anchorY: 860});
  checkPlacement(result, 860);
  assert.equal(JSON.stringify(cards), before);
  assert(new Set(result.cards.map(r => r.y)).size > 3, '不能退回同一排说明');
});

test('最早日期的说明放在下方，短图面通过留白容纳，不移动点位', () => {
  checkPlacement(placeCards(cards, {bounds, anchorY: 18}), 18);
  const small = placeCards(cards.slice(0, 2), {bounds: {...bounds, bottom: 46}, anchorY: 18});
  checkPlacement(small, 18);
  assert(small.height > 46);
  assert.equal(small.cards[0].anchorX, cards[0].anchorX);
});

test('拖动位置被限制在图面内', () => {
  const result = placeCards(cards.slice(0, 1), {bounds, anchorY: 800, manual: new Map([['task-0', {x: -100, y: 2000}]])});
  assert.equal(result.cards[0].x, bounds.left);
  assert.equal(result.cards[0].y + result.cards[0].h, bounds.bottom);
});

test('连接点位于浮窗边界并向内留出角距', () => {
  const rect = {x: 100, y: 100, w: 200, h: 120};
  assert.deepEqual(attachment(rect, 50, 400), {x: 116, y: 220, edge: 'bottom'});
  assert.deepEqual(attachment(rect, 400, 150), {x: 300, y: 150, edge: 'right'});
});

test('引线绕开其他浮窗和相邻点位，不穿过矩形内部', () => {
  const obstacles = [{x: 190, y: 180, w: 180, h: 130}, {x: 280, y: 415, w: 20, h: 20, margin: 0}];
  const start = {x: 220, y: 440}, end = {x: 400, y: 100};
  const route = routeLeader(start, end, obstacles, {right: 600, bottom: 500});
  assert(route && route.length > 2);
  assert.deepEqual(route[0], start); assert.deepEqual(route.at(-1), end);
  for (let i = 1; i < route.length; i++) for (const obstacle of obstacles) assert.equal(segmentHits(route[i - 1], route[i], obstacle), false);
});

test('无可用通路时明确返回 null，不伪造穿窗连线', () => {
  assert.equal(routeLeader({x: 10, y: 10}, {x: 100, y: 100}, [{x: 80, y: 80, w: 40, h: 40}], {right: 200, bottom: 200}), null);
});

test('浮窗间距仅15px时，连接端口仍有可用通路', () => {
  const target = {x: 100, y: 100, w: 200, h: 130};
  const neighbor = {x: 100, y: 245, w: 200, h: 120};
  const port = attachment(target, 220, 440), end = {x: port.x, y: port.y + 7};
  const route = routeLeader({x: 220, y: 440}, end, [target, neighbor], {right: 500, bottom: 500});
  assert(route, '排布留下的间距必须同时容纳引线端口');
  for (let i = 1; i < route.length; i++) for (const rect of [target, neighbor]) assert.equal(segmentHits(route[i - 1], route[i], rect), false);
});

test('圆角路径保留起终点，重复点不产生无效数值', () => {
  const d = roundedPath([{x: 10, y: 20}, {x: 10, y: 80}, {x: 10, y: 80}, {x: 90, y: 80}]);
  assert(d.startsWith('M10,20')); assert(d.endsWith('L90,80')); assert(!/NaN|Infinity/.test(d));
});

test('竖向密集事件分别保留日期锚点，浮窗在链条两侧避让', () => {
  const events = Array.from({length: 19}, (_, i) => ({id: `2026-09-${i + 1}`, anchorX: 600, anchorY: 280 + i * 14, radius: 2, w: 204 + i % 3 * 9, h: 112 + i % 4 * 14}));
  const before = JSON.stringify(events), result = placeChainCards(events, {bounds});
  assert.equal(JSON.stringify(events), before);
  assert(result.cards.some(r => r.x > 600) && result.cards.some(r => r.x + r.w < 600));
  for (const [i, r] of result.cards.entries()) {
    assert.equal(r.anchorY, events[i].anchorY);
    assert(r.x >= bounds.left && r.x + r.w <= bounds.right);
    assert(r.x >= 644 || r.x + r.w <= 556, '链线及事件编号周围保留阅读空间');
    assert(r.y >= bounds.top && r.y + r.h <= result.height);
    for (const b of result.cards.slice(i + 1)) assert(r.x + r.w <= b.x || b.x + b.w <= r.x || r.y + r.h <= b.y || b.y + b.h <= r.y);
  }
});

test('边缘链条使用可用侧，侧边端口朝向自己的真实日期点', () => {
  for (const anchorX of [110, 1220]) {
    const result = placeChainCards(Array.from({length: 4}, (_, i) => ({id: String(i), anchorX, anchorY: 100 + i * 15, w: 210, h: 130})), {bounds});
    for (const r of result.cards) assert(anchorX === 110 ? r.x > anchorX : r.x + r.w < anchorX);
  }
  assert.deepEqual(attachment({x: 300, y: 100, w: 200, h: 120}, 250, 400, true), {x: 300, y: 204, edge: 'left'});
});

test('按日展开保持点与卡片的左右次序，上下仍可错落，输入次序不变', () => {
  const shuffled = [cards[7], cards[1], cards[5], cards[0], cards[8], cards[3], cards[2], cards[6], cards[4]];
  for (const anchorY of [18, 860]) {
    const result = placeCards(shuffled, {bounds, anchorY});
    checkPlacement(result, anchorY);
    assert.deepEqual(result.cards.map(r => r.id), shuffled.map(r => r.id));
    const horizontal = [...result.cards].sort((a, b) => a.anchorX - b.anchorX);
    for (let i = 1; i < horizontal.length; i++) {
      assert(horizontal[i - 1].x + horizontal[i - 1].w / 2 < horizontal[i].x + horizontal[i].w / 2, '左边的点对应的卡片中心应在左边');
    }
    assert(new Set(result.cards.map(r => r.y)).size > 1, '保序不能强制卡片排成同一横行');
  }
});

test('按链条展开在密集及短图面中保持上下次序，左右仍可错落', () => {
  const events = Array.from({length: 19}, (_, i) => ({id: String(i), anchorX: 600, anchorY: 40 + i * 14, w: 204 + i % 3 * 9, h: 100 + i % 4 * 55}));
  for (const bottom of [300, 1000]) {
    const result = placeChainCards([...events].reverse(), {bounds: {...bounds, bottom}});
    assert.deepEqual(result.cards.map(r => r.id), events.map(r => r.id).reverse());
    const vertical = [...result.cards].sort((a, b) => a.anchorY - b.anchorY);
    for (let i = 1; i < vertical.length; i++) {
      assert(vertical[i - 1].y + vertical[i - 1].h / 2 < vertical[i].y + vertical[i].h / 2, '上面的点对应的卡片中心应在上面');
    }
    for (const [i, a] of result.cards.entries()) {
      assert(a.x >= bounds.left && a.x + a.w <= bounds.right);
      assert(a.y >= bounds.top && a.y + a.h <= result.height);
      for (const b of result.cards.slice(i + 1)) assert(a.x + a.w <= b.x || b.x + b.w <= a.x || a.y + a.h <= b.y || b.y + b.h <= a.y);
    }
    assert(result.cards.some(r => r.x > 600) && result.cards.some(r => r.x + r.w < 600));
    assert(new Set(vertical.slice(-6).map(r => r.x)).size > 1, '图底增加留白后仍需利用左右空间，不能把后续事件全部塞进同一列');
  }
});

test('手动摆放可越过自动次序，重新排布后恢复对应轴顺序', () => {
  const manual = new Map([['task-0', {x: 1000, y: 100}]]);
  const moved = placeCards(cards, {bounds, anchorY: 800, manual});
  assert.equal(moved.cards[0].x, 1000);
  assert.equal(moved.cards[0].y, 100);
  const automatic = moved.cards.filter(r => r.id !== 'task-0');
  for (let i = 1; i < automatic.length; i++) assert(automatic[i - 1].x + automatic[i - 1].w / 2 < automatic[i].x + automatic[i].w / 2);
  const reset = placeCards(cards, {bounds, anchorY: 800});
  assert(reset.cards[0].x < moved.cards[0].x);
  const events = [0, 1, 2].map(i => ({id: String(i), anchorX: 600, anchorY: 100 + i * 20, w: 210, h: 130}));
  const chain = placeChainCards(events, {bounds, manual: new Map([['0', {x: 700, y: 800}]])});
  assert.equal(chain.cards[0].y, 800);
  assert(chain.cards[1].y < chain.cards[0].y, '手动位置不强迫其余事件跟随下移');
});

test('同日点集中在一侧时，放得下的四张卡片利用空侧横向展开', () => {
  for (const mirrored of [false, true]) {
    const clustered = [900, 928, 1110, 1240].map((x, i) => ({id: String(i), anchorX: mirrored ? bounds.left + bounds.right - x : x, w: [216, 196, 178, 196][i], h: i === 0 ? 240 : 154}));
    const result = placeCards(clustered, {bounds: {...bounds, bottom: 1900}, anchorY: 1684});
    const horizontal = [...result.cards].sort((a, b) => a.anchorX - b.anchorX);
    for (let i = 1; i < horizontal.length; i++) {
      assert(horizontal[i - 1].x + horizontal[i - 1].w + 13 <= horizontal[i].x, '横向空间足够时，不应在同一侧纵向堆叠卡片');
    }
    const occupiedWidth = horizontal.at(-1).x + horizontal.at(-1).w - horizontal[0].x;
    assert(occupiedWidth >= clustered.reduce((n, c) => n + c.w, 0) + 39, '整组卡片应利用空侧的可用宽度');
    assert(Math.abs(horizontal[0].x - bounds.left - (bounds.right - horizontal.at(-1).x - horizontal.at(-1).w)) < 1, '点集中在一侧时，整组卡片两侧留白应平衡');
  }
});
