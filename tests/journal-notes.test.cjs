const {test} = require('node:test');
const assert = require('node:assert/strict');
const {placeCards, attachment, segmentHits, routeLeader, roundedPath} = require('../site/js/journal-notes.js');

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
