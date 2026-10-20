const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const context = {window: {}};
vm.runInNewContext(fs.readFileSync('site/js/journal.js', 'utf8'), context);
const label = date => context.window.JournalView.restDayLabel(date);

test('2026 年七个官方假期的首尾日期均属于休息日', () => {
  // 国办发明电〔2025〕7号，共 33 个放假调休日。
  for (const [start, end, name] of [
    ['2026-01-01', '2026-01-03', '元旦'], ['2026-02-15', '2026-02-23', '春节'],
    ['2026-04-04', '2026-04-06', '清明节'], ['2026-05-01', '2026-05-05', '劳动节'],
    ['2026-06-19', '2026-06-21', '端午节'], ['2026-09-25', '2026-09-27', '中秋节'],
    ['2026-10-01', '2026-10-07', '国庆节']
  ]) {
    for (let n = Date.parse(start); n <= Date.parse(end); n += 86400000) {
      assert.equal(label(new Date(n).toISOString().slice(0, 10)), name);
    }
  }
});

test('六个调休补班周末不标底纹，普通周末仍标底纹', () => {
  for (const date of ['2026-01-04', '2026-02-14', '2026-02-28', '2026-05-09', '2026-09-20', '2026-10-10']) {
    assert.equal(label(date), '', date);
  }
  assert.equal(label('2026-09-19'), '周末');
  assert.equal(label('2026-10-11'), '周末');
});

test('节前节后的普通工作日不标底纹，未收录年份不套用旧节日', () => {
  for (const date of ['2026-09-24', '2026-09-28', '2026-09-30', '2026-10-08', '2027-09-27']) {
    assert.equal(label(date), '', date);
  }
  assert.equal(label('2027-10-09'), '周末');
});
