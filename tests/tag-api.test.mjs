import {test} from 'node:test';
import assert from 'node:assert/strict';
import {generateKeyPair, SignJWT, jwtVerify} from 'jose';
import {identity, handleRequest, updateState} from '../worker/index.mjs';

const M = globalThis.ReportTagModel;
const data = {schemaVersion:1,tags:[{id:'speed',name:'提速',color:'#123456',keywords:[]}],assignments:{}};
function storage() {
  let value; let queue = Promise.resolve();
  return {
    get:async()=>value,
    transaction(fn) {
      const task=queue.then(()=>fn({get:async()=>value,put:async(_key,v)=>{value=M.clone(v);}}));
      queue=task.catch(()=>{}); return task;
    },
  };
}
const body = (revision=0,mutationId='mutation_0001')=>({revision,mutationId,data});
test('atomic updates, stale revisions and retry after lost response', async()=>{
  const s=storage();
  assert.equal((await updateState(s,body())).status,200);
  assert.equal((await updateState(s,body())).status,200);
  assert.equal((await s.get()).revision,1);
  assert.equal((await updateState(s,body(0,'mutation_0002'))).status,409);
  const changed={...body(),data:{...data,assignments:{a:['speed']}}};
  assert.equal((await updateState(s,changed)).status,409);
  const responses=await Promise.all([updateState(s,body(1,'mutation_0003')),updateState(s,body(1,'mutation_0004'))]);
  assert.deepEqual(responses.map(r=>r.status).sort(),[200,409]);
  assert.equal((await s.get()).revision,2);
});
test('reject malformed data before storage write',async()=>{
  const s=storage();
  await assert.rejects(()=>updateState(s,{...body(),revision:-1}));
  await assert.rejects(()=>updateState(s,{...body(),data:{...data,assignments:{a:['missing']}}}));
  assert.equal(await s.get(),undefined);
});
function env(editors='*') {
  const s=storage();
  return {TAG_EDITORS:editors,REPORT_TAGS:{idFromName:()=>1,get:()=>({fetch:async req=>req.method==='GET'?Response.json(await s.get()||{revision:0,data}):updateState(s,await req.json())})},ASSETS:{fetch:()=>new Response('asset')}};
}
const authenticated=async()=>({email:'another@example.com'});
const put = (headers={}) => new Request('https://example.com/api/report-tags',{method:'PUT',headers:{'Content-Type':'application/json',Origin:'https://example.com',...headers},body:JSON.stringify(body())});
test('all authenticated emails can edit; anonymous and forged email headers cannot',async()=>{
  const e=env();
  assert.equal((await handleRequest(put(),e,authenticated)).status,200);
  assert.equal((await handleRequest(put({'Cf-Access-Authenticated-User-Email':'owner@example.com'}),e)).status,401);
  const read=await handleRequest(new Request('https://example.com/api/report-tags'),e,authenticated);
  assert.equal((await read.json()).canEdit,true);
  assert.equal((await handleRequest(put(),env('owner@example.com'),authenticated)).status,403);
});
test('CSRF, methods, unknown endpoints and oversized bodies are rejected',async()=>{
  assert.equal((await handleRequest(put({Origin:'https://evil.test'}),env(),authenticated)).status,403);
  assert.equal((await handleRequest(put({'Sec-Fetch-Site':'cross-site'}),env(),authenticated)).status,403);
  assert.equal((await handleRequest(put({'Content-Type':'text/plain'}),env(),authenticated)).status,400);
  assert.equal((await handleRequest(put({'Content-Length':'999999'}),env(),authenticated)).status,400);
  assert.equal((await handleRequest(new Request('https://example.com/api/report-tags',{method:'DELETE'}),env(),authenticated)).status,405);
  assert.equal((await handleRequest(new Request('https://example.com/api/unknown'),env(),authenticated)).status,404);
  assert.equal(await (await handleRequest(new Request('https://example.com/'),env())).text(),'asset');
});
test('JWT verification requires pinned issuer, audience, expiration and signed email',async()=>{
  const {privateKey,publicKey}=await generateKeyPair('RS256');
  const e={ACCESS_ISSUER:'https://example.cloudflareaccess.com',ACCESS_AUD:'expected'};
  const verify=(token,_keys,options)=>jwtVerify(token,publicKey,options);
  const make=async(aud='expected',issuer=e.ACCESS_ISSUER,exp='2h',email='person@example.com')=>new SignJWT({email}).setProtectedHeader({alg:'RS256'}).setIssuedAt().setSubject('user').setAudience(aud).setIssuer(issuer).setExpirationTime(exp).sign(privateKey);
  const req=token=>new Request('https://example.com/api/report-tags',{headers:{'Cf-Access-Jwt-Assertion':token}});
  assert.deepEqual(await identity(req(await make()),e,verify),{email:'person@example.com'});
  for (const token of [await make('wrong'),await make('expected','https://evil.test'),await make('expected',e.ACCESS_ISSUER,'-2h'),await make('expected',e.ACCESS_ISSUER,'2h',''), 'forged']) assert.equal(await identity(req(token),e,verify),null);
});
