const assert=require('node:assert/strict');
const fs=require('node:fs');
const zlib=require('node:zlib');
const {paths,interval,configKey,linePath,panels,csvRows}=require('../scripts/factor_strategy_comparison.js');

const key='equal-combined-close-L-5';
const dates=['2024-07-01','2025-09-30','2025-10-09'];
const fixture={dates,stages:['development','development','seen'],initial:{equal:[20,80]},base:{equal:[[21,81],[22,83],[23,82]]},results:{
  B0:{dates,series:{[key]:[[0,0],[2,-1],[3,1]]},trading:{[key]:[[0,0,0,0],[1,.001,2,.002],[3,.003,4,.004]]}},
  G2:{dates:dates.slice(0,2),series:{[key]:[[0,0],[2,3]]}}
}};
const p=paths(fixture,key,'all',['B0','G2']);
const close=(a,b)=>assert.ok(Math.abs(a-b)<1e-10,`${a} vs ${b}`);
assert.deepEqual(p.versions.G2.excess,[0,5,null]);
assert.deepEqual(p.versions.G2.delta,[0,4,null]);
close(p.versions.G2.wealth[1],10);
close(p.versions.B0.wealth[2],9);
assert.equal(p.versions.G2.amount[2],null);
assert.equal(linePath([0,1,null,0],i=>i,v=>v),'M0.00,0.00L1.00,1.00M3.00,0.00');
const segment=interval(fixture,key,'all',p,'B0',null,2,2);
close(segment.excess,3/105*100);
close(segment.wealth,(109/106-1)*100);
close(segment.fee,.007/105*10000);
close(segment.turnover,7/105*100);
assert.deepEqual(interval(fixture,key,'all',p,'G2','B0',0,2),{covered:2});
const s={weight:'equal',sorting:'combined',strategy:'L',q:'5',trade:'10',start:1,stop:2,market:'split',candidate:'G2',focus:'all/close'};
assert.equal(configKey({...s,trade:30},'close'),key+'-t30');
assert.equal(panels({...s,focus:null}).length,4);
assert.equal(panels({...s,focus:null,market:'all'}).length,2);
const rows=csvRows(fixture,s);
assert.equal(rows.length,4);
assert.deepEqual(rows.at(-1).slice(0,6),[dates[2],'seen','all','close',key,'G2']);
assert.deepEqual(rows.at(-1).slice(-4),[null,null,null,null]);

const page=fs.readFileSync(require.resolve('../content/daily/2026-11-16.show.html'),'utf8');
const encoded=page.match(/id="comparison-data"[^>]*>\s*([^<]+)<\/script>/s)[1];
const packed=JSON.parse(zlib.gunzipSync(Buffer.from(encoded,'base64')));
const manifest=JSON.parse(fs.readFileSync(require.resolve('../content/assets/factor-strategy-comparison/manifest.json'),'utf8'));
assert.equal(packed.dates.length,566);
assert.equal(packed.versions.length,7);
assert.equal(packed.factors.length,16);
assert.equal(Object.keys(packed.results.B0.series).length,192);
assert.deepEqual(packed.versions,manifest.versions);
assert.equal(packed.results.G2.dates.length,manifest.versions[1].coverage);
assert.equal(packed.results.G2.series[key].length,manifest.versions[1].coverage);
assert.equal(packed.results.H01,undefined);
assert.match(page,/name="candidate"/);
assert.equal((page.match(/id="comparison-filters"/g)||[]).length,1);
assert.doesNotMatch(page,/id="g2-comparison"/);
console.log(`B0 566 日，G2 ${packed.results.G2.dates.length} 日；192 配置，7 个版本，16 个变体；金额、缺口、区间、导出与嵌入资产检查通过。`);
