(()=>{
 const files=new Map();
 window.rawbankFileLoaded=async(name,encoded,type)=>{
  const request=files.get(name);if(!request)return;
  try{
   const compressed=Uint8Array.from(atob(encoded),c=>c.charCodeAt(0));
   const raw=await new Response(new Blob([compressed]).stream().pipeThrough(new DecompressionStream('gzip'))).arrayBuffer();
   request.save(raw,name,type);request.resolve();
  }catch(error){request.reject(error)}finally{files.delete(name)}
 };
 window.bindRawbankDownloads=save=>{
  for(const link of document.querySelectorAll('a[data-file-download]')){
   if(link.dataset.downloadBound)continue;
   link.dataset.downloadBound='true';const label=link.textContent;
   link.onclick=async event=>{
    event.preventDefault();if(link.getAttribute('aria-busy')==='true')return;
    link.setAttribute('aria-busy','true');link.textContent='正在准备下载…';let success=false;
    try{
     const name=link.dataset.fileDownload;
     if(!files.has(name)){
      let resolve,reject;const promise=new Promise((a,b)=>{resolve=a;reject=b});
      files.set(name,{promise,resolve,reject,save});const script=document.createElement('script');
      script.src=link.href+'.js';script.onload=()=>script.remove();
      script.onerror=()=>{script.remove();files.delete(name);reject(new Error('附件加载失败'))};
      document.head.append(script);
     }
     await files.get(name).promise;success=true;link.removeAttribute('title');
    }catch{link.title='文件暂时无法读取，请点击重试。'}
    finally{link.removeAttribute('aria-busy');link.textContent=success?label:'下载失败，点击重试'}
   };
  }
 };
})();
