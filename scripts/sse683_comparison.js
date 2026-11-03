(()=>{
 const encoded=document.getElementById('market-comparison-data');if(!encoded)return;
 const names={all:'全部',old:'既有行为',cancel_buy:'买侧撤单相位',cancel_sell:'卖侧撤单相位',depth:'深度匹配'};
 const select=document.getElementById('comparison-context'),summary=document.getElementById('comparison-summary'),columns=document.getElementById('comparison-columns');
 const number=v=>v===null?'—':v.toFixed(5);
 function table(head,rows,identities=1){const t=document.createElement('table'),h=t.createTHead().insertRow(),body=t.createTBody();head.forEach((label,i)=>{const c=document.createElement('th');c.textContent=label;if(i>=identities)c.style.textAlign='right';h.append(c)});for(const row of rows){const tr=body.insertRow();row.forEach((value,i)=>{const c=tr.insertCell();c.textContent=value;if(i>=identities)c.style.textAlign='right'})}return t}
 async function init(){
  const bytes=Uint8Array.from(atob(encoded.textContent),c=>c.charCodeAt(0));
  const data=await new Response(new Blob([bytes]).stream().pipeThrough(new DecompressionStream('gzip'))).json();
  function render(){const context=data.contexts[select.value];summary.replaceChildren(table(['来源','配对列','有效同号比较列','同号比例','Rank IC列间排序相关'],context.groups.map(([source,n,valid,same,rho])=>[names[source],n,valid,valid?`${same}/${valid} (${(same/valid*100).toFixed(2)}%)`:'—',number(rho)])));
   columns.replaceChildren(table(['沪市列','深市列','沪IC','沪Rank IC','沪NW t','沪ICIR','沪G10−G1','深IC','深Rank IC','深NW t','深ICIR','深G10−G1','Rank IC同号'],context.rows.map((r,i)=>[...data.columns[i].slice(0,2),...r.slice(0,10).map(number),r[10]===null?'—':r[10]?'是':'否']),2));
  }
  select.onchange=render;render();
  new MutationObserver(()=>{const key=document.body.dataset.context;if(data.contexts[key]){select.value=key;render()}}).observe(document.body,{attributes:true,attributeFilter:['data-context']});
 }
 init().catch(()=>{summary.textContent='两市对照读取失败，请重新载入本页。'});
})();
