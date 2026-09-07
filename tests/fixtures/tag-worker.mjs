// Local-only browser fixture. Production uses worker/index.mjs and validates Access JWTs.
import {handleRequest, ReportTags} from '../../worker/index.mjs';
export {ReportTags};
export default {fetch(request,env) {
  if (new URL(request.url).pathname === '/__test/health') return new Response('ready');
  return handleRequest(request,env,async()=>({email:'browser-test@example.test'}));
}};
