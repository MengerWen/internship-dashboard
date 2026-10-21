const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const context = {window: {}};
vm.runInNewContext(fs.readFileSync('site/js/journal.js', 'utf8'), context);
const journal = context.window.JournalView;

test('人工核实的链成果不会混入同日其他链的报告', () => {
  const view = {reports: new Map([['2026-09-04', {}], ['2026-09-16', {}]])};
  const days = [{reports_covering: ['2026-09-04']}];
  assert.deepEqual(Array.from(journal.chainReports.call(view, {report_coverage: 'curated', closes_into: {daily: []}}, days)), []);
  assert.deepEqual(Array.from(journal.chainReports.call(view, {report_coverage: 'curated', closes_into: {daily: ['2026-09-16']}}, days)), ['2026-09-16']);
});

test('交接曲线采用已登记来源阶段，缺失日期不悄悄换成相邻日', () => {
  const from = ['2026-08-27', '2026-09-18'].map(date => ({date}));
  const to = ['2026-10-07', '2026-10-08'].map(date => ({date}));
  const dates = journal.handoffDates({source_date: '2026-08-27', date: '2026-10-08'}, from, to);
  assert.equal(dates.source, '2026-08-27');
  assert.equal(dates.target, '2026-10-08');
  assert.equal(journal.handoffDates({source_date: '2026-08-26', date: '2026-10-08'}, from, to), null);
  assert.equal(journal.handoffDates({source_date: '2026-08-27', date: '2026-10-09'}, from, to), null);
  assert.equal(journal.handoffDates({source_date: '2026-10-08', date: '2026-08-27'}, to, from), null);
});

test('原始依据只接受 GitHub HTTPS 链接并转义标题和属性', () => {
  const html = journal.sourceLinks([{url: 'javascript:alert(1)', title: 'bad'}, {url: 'https://github.com/a/b/commit/abc"', title: '<源文件>'}]);
  assert.ok(!html.includes('javascript:'));
  assert.ok(html.includes('&lt;源文件&gt;'));
  assert.ok(html.includes('abc&quot;'));
});
