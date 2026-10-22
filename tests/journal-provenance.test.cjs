const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const context = {window: {}};
vm.runInNewContext(fs.readFileSync('site/js/journal.js', 'utf8'), context);
const journal = context.window.JournalView;

test('点大小只读取对应任务的归属量，同日总量及其他任务不影响它', () => {
  const day = {total_commits: 140, chain_weights: {a: {value: 4, direct: 4, shared: 0}, b: {value: 40, direct: 40, shared: 0}}};
  const radius = journal.pointRadius(day, 'a');
  assert(journal.pointRadius(day, 'b') > radius);
  day.total_commits = 10000;
  day.chain_weights.b.value = 9000;
  assert.equal(journal.pointRadius(day, 'a'), radius);
  assert.equal(journal.pointWeight(day, 'missing'), null);
  assert.equal(journal.pointRadius(day, 'missing'), journal.pointRadius({chain_weights: {zero: {value: 0}}}, 'zero'));
  assert.match(journal.weightLabel(day, 'missing'), /待核/);
});

test('跨链份额显示精确计量，缺少提交证据不冒充当天总量', () => {
  const day = {total_commits: 100, chain_weights: {a: {value: 1.5, direct: 1, shared: 1}, zero: {value: 0, direct: 0, shared: 0}}};
  assert.match(journal.weightLabel(day, 'a'), /1\.5.*1 条跨链/);
  assert.match(journal.weightLabel(day, 'zero'), /无已归属提交/);
  assert(journal.pointRadius(day, 'a') < journal.pointRadius({chain_weights: {a: {value: 100}}}, 'a'));
  assert(journal.pointRadius({chain_weights: {a: {value: 20.5}}}, 'a') > journal.pointRadius({chain_weights: {a: {value: 20}}}, 'a'));
});

test('旧密度按比例迁移，保存后再次打开不重复放大', () => {
  const stored = new Map();
  const scoped = {window: {}, localStorage: {setItem: (key, value) => stored.set(key, value)}};
  vm.runInNewContext(fs.readFileSync('site/js/journal.js', 'utf8'), scoped);
  const view = Object.assign({}, scoped.window.JournalView, {window: '3m'});
  view.density = view.densityFromPreferences({density: 11});
  assert.equal(view.density, 14);
  assert.equal(view.densityFromPreferences({density: 7}), 7 * 14 / 11);
  assert.equal(view.densityFromPreferences({density: 44}), 44);
  view.savePreferences();
  const saved = JSON.parse(stored.get('journal-atlas-preferences'));
  assert.equal(saved.window, '3m');
  assert.equal(view.densityFromPreferences(saved), 14);
  for (const density of [7, 11, 14, 23, 36]) {
    assert.equal(view.densityFromPreferences({...saved, density}), density);
  }
});

test('缺少或无效的密度偏好回到新标准间距', () => {
  for (const value of [undefined, null, {}, {density: '11'}, {density: 0}, {density: 45}]) {
    assert.equal(journal.densityFromPreferences(value), 14);
  }
});

test('完整归属明细将提交标题、理由、路径和依据层级作为文本显示', () => {
  const day = {date:'2026-10-20',chains:['a'],chain_weights:{a:{value:1,direct:1,shared:0}},attribution_summary:{statuses:{assigned:1}}};
  const view = Object.assign({}, journal, {days:[day],chains:new Map([['a',{short:'任务'}]])});
  const html = view.attributionHtml({date:day.date,repos:[{repo:'r',commit_url:'https://github.com/org/r/commit/{sha}'}],attribution:{items:[{
    repo:'r',sha:'a'.repeat(40),subject:'<script>标题</script>',reason:'<img src=x>',basis:'<svg onload=x>',paths:['<script>路径</script>'],shares:{a:{numerator:1,denominator:1}}
  }]}});
  assert(!html.includes('<script>'));
  assert(!html.includes('<svg onload'));
  assert(html.includes('&lt;svg onload=x&gt;'));
  assert(html.includes('&lt;script&gt;路径&lt;/script&gt;'));
});

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

test('证据空实与汇报和提交量分开，零提交文档仍有产物', () => {
  const day = {report: '2026-10-21', reports_covering: ['2026-10-21'], chain_weights: {a: {value: 0}},
    chain_evidence: {a: {status: 'artifact', kinds: ['文档'], document_count: 1, artifacts: [{title: '<计划>', label: '文档写入记录', url: 'https://github.com/org/repo/blob/main/plan.md'}], discussions: []}}};
  assert.equal(journal.pointEvidence(day, 'a').status, 'artifact');
  assert.equal(journal.pointEvidence(day, 'missing').status, 'pending');
  assert.match(journal.evidenceLabel(day, 'a'), /可查产物/);
  const html = journal.pointEvidenceHtml(day, 'a');
  assert(html.includes('is-artifact'));
  assert(html.includes('&lt;计划&gt;'));
  assert(html.includes('产物'));
  assert(!html.includes('<计划>'));
  day.chain_evidence.a = {status: 'discussion', kinds: ['会话'], artifacts: [], discussions: [{title: '比较方案', url: 'https://github.com/org/repo/blob/main/sources.md'}]};
  assert.match(journal.evidenceLabel(day, 'a'), /仅见交流/);
  assert(journal.pointEvidenceHtml(day, 'a').includes('比较方案'));
  assert(!journal.weightLegendHtml().includes('未关联汇报'));
});
