(()=>{
 function comparisonCsv(data){
  const cell=v=>{const text=v===null?'':typeof v==='boolean'?(v?'True':'False'):Object.is(v,-0)?'-0':String(v);return /[",\r\n]/.test(text)?'"'+text.replaceAll('"','""')+'"':text};
  const head=['context','sse_column','szse_column','source','match_method',...['sse','szse'].flatMap(m=>data.metrics.map(v=>m+'_'+v)),'rank_same_sign'];
  const rows=[head];for(const [key,context] of Object.entries(data.contexts))context.rows.forEach((row,i)=>rows.push([key,...data.columns[i],...row]));
  return '\ufeff'+rows.map(row=>row.map(cell).join(',')).join('\r\n')+'\r\n';
 }
 if(typeof module!=='undefined'&&module.exports)module.exports={comparisonCsv};
 if(typeof document==='undefined')return;
 const encoded=document.getElementById('market-comparison-data');if(!encoded)return;
 const names={all:'全部',old:'既有行为',cancel_buy:'买侧撤单相位',cancel_sell:'卖侧撤单相位',depth:'深度匹配'};
 const select=document.getElementById('comparison-context'),summary=document.getElementById('comparison-summary'),columns=document.getElementById('comparison-columns');
 const number=v=>v===null?'—':v.toFixed(5);
 function table(head,rows,identities=1){const t=document.createElement('table'),h=t.createTHead().insertRow(),body=t.createTBody();head.forEach((label,i)=>{const c=document.createElement('th');c.textContent=label;if(i>=identities)c.style.textAlign='right';h.append(c)});for(const row of rows){const tr=body.insertRow();row.forEach((value,i)=>{const c=tr.insertCell();c.textContent=value;if(i>=identities)c.style.textAlign='right'})}return t}
 async function init(){
  const bytes=Uint8Array.from(atob(encoded.textContent),c=>c.charCodeAt(0));
  const data=await new Response(new Blob([bytes]).stream().pipeThrough(new DecompressionStream('gzip'))).json();
  const download=document.getElementById('comparison-download');
  download.onclick=async event=>{
   if(typeof CompressionStream==='undefined')return;
   event.preventDefault();if(download.getAttribute('aria-busy')==='true')return;
   download.setAttribute('aria-busy','true');
   try{
    const blob=await new Response(new Blob([comparisonCsv(data)]).stream().pipeThrough(new CompressionStream('gzip'))).blob();
    const url=URL.createObjectURL(blob),link=document.createElement('a');link.href=url;link.download='market-comparison.csv.gz';link.click();setTimeout(()=>URL.revokeObjectURL(url),10000);download.removeAttribute('title');
   }catch{download.title='文件暂时无法读取，请点击重试。'}finally{download.removeAttribute('aria-busy')}
  };
  function render(){const context=data.contexts[select.value];summary.replaceChildren(table(['来源','配对列','有效同号比较列','同号比例','Rank IC列间排序相关'],context.groups.map(([source,n,valid,same,rho])=>[names[source],n,valid,valid?`${same}/${valid} (${(same/valid*100).toFixed(2)}%)`:'—',number(rho)])));
   columns.replaceChildren(table(['沪市列','深市列','沪IC','沪Rank IC','沪NW t','沪ICIR','沪G10−G1','深IC','深Rank IC','深NW t','深ICIR','深G10−G1','Rank IC同号'],context.rows.map((r,i)=>[...data.columns[i].slice(0,2),...r.slice(0,10).map(number),r[10]===null?'—':r[10]?'是':'否']),2));
  }
  select.onchange=render;render();
  new MutationObserver(()=>{const key=document.body.dataset.context;if(data.contexts[key]){select.value=key;render()}}).observe(document.body,{attributes:true,attributeFilter:['data-context']});
 }
 init().catch(()=>{summary.textContent='两市对照读取失败，请重新载入本页。'});
})();
