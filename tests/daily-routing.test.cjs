const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

const sources = ['tag-model.js', 'report-tags.js', 'daily.js'].map(file => fs.readFileSync('site/js/' + file, 'utf8'));
const HTML = '2026-11-13', MARKDOWN = '2026-11-12', DOC = '2026-11-11';

function fixture() {
  const elements = new Map();
  const get = id => {
    if (!elements.has(id)) elements.set(id, {
      innerHTML: '', hidden: false, classList: {toggle() {}}, setAttribute() {},
      querySelector: selector => get(selector),
    });
    return elements.get(id);
  };
  const location = {hash: ''};
  const history = {replaceState(_state, _title, hash) { location.hash = hash; }};
  const window = {history, location};
  const document = {getElementById: id => id.startsWith('daily-show-html-') ? null : get(id)};
  const context = Object.assign(window, {window, location, document, URLSearchParams});
  for (const source of sources) vm.runInNewContext(source, context);
  window.ReportTagsUI.render = () => {};
  const daily = [HTML, MARKDOWN, DOC].map((date, i) => ({
    date, path: date + '.doc', has_show: i < 2, show_type: ['html', 'md'][i], show_path: date + '.show',
  }));
  const loaded = [];
  const view = Object.assign(window.DailyView, {
    manifest: {daily},
    contentEl: get('doc'), showEl: get('show'), tocEl: get('toc'), mainlineEl: get('main'),
    renderMeta() {}, renderToc() {}, updateTimeline() {}, updateNav() {}, notice() {},
    app: {
      async loadFragment(path) { loaded.push(path); return path; },
      prepareIsolatedHtml: html => html,
      async enhanceContent() {},
    },
  });
  const open = (date, mode, suffix = '') => {
    location.hash = `#/daily/${date}${mode ? '/' + mode : ''}${suffix}`;
    return view.show(date, mode);
  };
  return {view, location, open, loaded, get};
}

test('有 HTML 展示的日期先加载展示，文档标签生成可刷新和分享的链接', async () => {
  const {view, location, open, loaded} = fixture();
  await open(HTML, undefined, '?q=baseline');
  assert.equal(view.currentMode, 'show');
  assert.equal(view.contentEl.hidden, true);
  assert.deepEqual(loaded, [HTML + '.show']);
  assert.equal(location.hash, `#/daily/${HTML}/show?q=baseline`);
  await view.switchMode('doc', true);
  assert.equal(location.hash, `#/daily/${HTML}/doc?q=baseline`);
  await open(HTML, 'doc', '?q=baseline');
  assert.equal(view.currentMode, 'doc');
  assert.equal(view.contentEl.hidden, false);
  assert.deepEqual(loaded, [HTML + '.show', HTML + '.doc']);
});

test('只有文档或 Markdown 展示的日期默认打开文档', async () => {
  const {view, location, open, loaded} = fixture();
  await open(MARKDOWN);
  assert.equal(view.currentMode, 'doc');
  await open(DOC, 'show');
  assert.equal(view.currentMode, 'doc');
  assert.equal(location.hash, `#/daily/${DOC}`);
  assert.deepEqual(loaded, [MARKDOWN + '.doc', DOC + '.doc']);
});

test('晚返回的展示内容不会覆盖后来选中的日期', async () => {
  const {view, location, open, get} = fixture();
  let deliverShow;
  const load = view.app.loadFragment;
  view.app.loadFragment = path => path === HTML + '.show'
    ? new Promise(resolve => { deliverShow = resolve; }) : load(path);
  const first = open(HTML);
  await open(DOC);
  deliverShow('旧展示');
  await first;
  assert.equal(view.currentMode, 'doc');
  assert.equal(view.contentEl.innerHTML, DOC + '.doc');
  assert.equal(get('iframe').srcdoc, undefined);
  assert.equal(location.hash, `#/daily/${DOC}`);
});
