const {test} = require('node:test');
const assert = require('node:assert/strict');
const M = require('../site/js/tag-model.js');
const seed = require('../content/report-tags.json');
const items = [
  {id:'a', date:'2026-09-04', title:'新因子机制预检提速', summary:'单日耗时'},
  {id:'b', date:'2026-08-19', title:'模型结果', summary:'SHAP 与 OOF'},
  {id:'c', date:'2026-07-09', title:'其他', summary:''},
];
test('multi-tag OR/AND, untagged, search and empty filters retain original order', () => {
  let s = M.assign(seed, ['a'], ['speed','precheck'], 'add');
  s = M.assign(s, ['b'], ['speed','model-results'], 'add');
  assert.deepEqual(M.filter(items,s,{tags:['speed']}).map(M.key),['a','b']);
  assert.deepEqual(M.filter(items,s,{tags:['speed','precheck'],mode:'all'}).map(M.key),['a']);
  assert.deepEqual(M.filter(items,s,{tags:['precheck','model-results'],mode:'any'}).map(M.key),['a','b']);
  assert.deepEqual(M.filter(items,s,{tags:['_untagged']}).map(M.key),['c']);
  assert.deepEqual(M.filter(items,s,{tags:['speed'],query:'shap'}).map(M.key),['b']);
  assert.equal(M.filter(items,s,{tags:['deleted']}).length,0);
});
test('bulk add is non-destructive and removing the last tag makes a report untagged', () => {
  const a = M.assign(seed,['a'],['speed'],'add');
  const b = M.assign(a,['a','b'],['precheck'],'add');
  assert.deepEqual(b.assignments.a,['speed','precheck']);
  assert.deepEqual(a.assignments.a,['speed']);
  const c = M.assign(b,['a','b'],['precheck'],'remove');
  assert.deepEqual(c.assignments.a,['speed']);
  assert.equal(c.assignments.b,undefined);
});
test('rename keeps identity, merge deduplicates assignments and delete only removes its tag', () => {
  const s = M.assign(seed,['a'],['speed','precheck'],'add');
  s.tags[0].name = '计算优化';
  assert.deepEqual(M.validate(s).assignments.a,['speed','precheck']);
  const merged = M.remove(s,'precheck','speed');
  assert.deepEqual(merged.assignments.a,['speed']);
  assert(!merged.tags.some(t=>t.id==='precheck'));
  assert(M.remove(merged,'speed').assignments.a === undefined);
  assert.throws(()=>M.remove(s,'speed','speed'));
});
test('input rejects duplicate names, malicious IDs, invalid colors and dangling relations', () => {
  const bad = (fn) => { const s = M.clone(seed); fn(s); assert.throws(()=>M.validate(s)); };
  bad(s=>s.tags[0].name='');
  bad(s=>s.tags[1].name=s.tags[0].name);
  bad(s=>s.tags[0].name='未标记');
  bad(s=>s.tags[0].color='red;position:fixed');
  bad(s=>s.tags[0].id='__proto__');
  bad(s=>s.tags[0].id='_untagged');
  bad(s=>s.assignments.a=['does-not-exist']);
  bad(s=>s.tags[0].keywords=['']);
  assert.throws(()=>M.validate({...seed,assignments:JSON.parse('{"__proto__":["speed"]}')}));
});
test('suggestions explain literal keyword matches and never auto-assign', () => {
  const s = M.clone(seed);
  assert(M.suggest(items[0],s).some(r=>r.id==='speed' && r.hits.includes('提速')));
  assert(M.suggest(items[0],s).some(r=>r.id==='precheck'));
  assert.deepEqual(s.assignments,{});
  assert(!M.suggest(items[0],M.assign(s,['a'],['speed'],'add')).some(r=>r.id==='speed'));
});
test('import unifies equal names without losing existing assignments or duplicating tags', () => {
  const a = M.assign(seed,['a'],['speed'],'add');
  const incoming = {schemaVersion:1,tags:[{id:'new-speed',name:'提速',color:'#123456',keywords:[]}],assignments:{b:['new-speed']}};
  const merged = M.mergeImport(a,incoming);
  assert.equal(merged.tags.length,seed.tags.length);
  assert.deepEqual(merged.assignments,{a:['speed'],b:['speed']});
});
