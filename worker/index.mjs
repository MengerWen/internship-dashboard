import {createRemoteJWKSet, jwtVerify} from "jose";
import "../site/js/tag-model.js";
import seed from "../content/report-tags.json" with {type: "json"};

const Model = globalThis.ReportTagModel;
const MAX_BODY = 512 * 1024;
const keysets = new Map();
export const json = (body, status = 200) => Response.json(body, {status, headers: {
  "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff", "X-Robots-Tag": "noindex",
}});

export async function identity(request, env, verifier = jwtVerify) {
  const issuer = env.ACCESS_ISSUER;
  if (!/^https:\/\/[a-z0-9-]+\.cloudflareaccess\.com$/.test(issuer || "") || !env.ACCESS_AUD) return null;
  const token = request.headers.get("Cf-Access-Jwt-Assertion");
  if (!token) return null;
  try {
    if (!keysets.has(issuer)) keysets.set(issuer, createRemoteJWKSet(new URL(`${issuer}/cdn-cgi/access/certs`)));
    const {payload} = await verifier(token, keysets.get(issuer), {
      issuer, audience: env.ACCESS_AUD, algorithms: ["RS256"], requiredClaims: ["exp", "iat", "sub", "email"],
    });
    return typeof payload.email === "string" && payload.email.includes("@") ? {email: payload.email} : null;
  } catch { return null; }
}

async function readBody(request) {
  if (!request.headers.get("Content-Type")?.startsWith("application/json")) throw new Error("请使用 JSON 数据");
  if (Number(request.headers.get("Content-Length")) > MAX_BODY) throw new Error("标签数据超过 512 KB");
  const reader = request.body?.getReader();
  if (!reader) throw new Error("缺少标签数据");
  const chunks = []; let size = 0;
  for (;;) {
    const {value, done} = await reader.read();
    if (done) break;
    size += value.byteLength;
    if (size > MAX_BODY) { await reader.cancel(); throw new Error("标签数据超过 512 KB"); }
    chunks.push(value);
  }
  const bytes = new Uint8Array(size); let offset = 0;
  for (const chunk of chunks) { bytes.set(chunk, offset); offset += chunk.byteLength; }
  return JSON.parse(new TextDecoder().decode(bytes));
}

// Version comparison and write share a transaction, including across concurrent requests.
export async function updateState(storage, body) {
  if (!Number.isSafeInteger(body.revision) || body.revision < 0 || typeof body.mutationId !== "string" || !/^[a-zA-Z0-9_-]{8,80}$/.test(body.mutationId)) throw new Error("保存版本或操作 ID 无效");
  const data = Model.validate(body.data);
  return storage.transaction(async (tx) => {
    const current = await tx.get("state") || {revision: 0, data: Model.validate(seed)};
    if (current.mutationId === body.mutationId && JSON.stringify(current.data) === JSON.stringify(data)) return json(current);
    if (current.revision !== body.revision) return json({error: "其他窗口已修改标签。请保留草稿并载入最新版本。", current}, 409);
    const next = {revision: current.revision + 1, data, mutationId: body.mutationId, updatedAt: new Date().toISOString()};
    await tx.put("state", next);
    return json(next);
  });
}

export class ReportTags {
  constructor(ctx) { this.storage = ctx.storage; }
  async fetch(request) {
    if (request.method === "GET") return json(await this.storage.get("state") || {revision: 0, data: Model.validate(seed)});
    try { return await updateState(this.storage, await request.json()); }
    catch (error) { return json({error: error.message}, 400); }
  }
}

export async function handleRequest(request, env, authenticate = identity) {
  const url = new URL(request.url);
  if (!url.pathname.startsWith("/api/")) return env.ASSETS.fetch(request);
  if (url.pathname !== "/api/report-tags") return json({error: "接口不存在"}, 404);
  if (!["GET", "PUT"].includes(request.method)) return json({error: "不支持此操作"}, 405);
  const user = await authenticate(request, env);
  if (!user) return json({error: "登录已失效，请重新登录网站后重试"}, 401);
  if (!env.REPORT_TAGS) return json({error: "在线存储尚未配置"}, 503);
  const editors = (env.TAG_EDITORS || "").split(",").map((s) => s.trim().toLowerCase());
  const canEdit = editors.includes("*") || editors.includes(user.email.toLowerCase());
  const stub = env.REPORT_TAGS.get(env.REPORT_TAGS.idFromName("reports-v1"));
  if (request.method === "GET") {
    const result = await stub.fetch(new Request("https://tags/state"));
    return json({...await result.json(), canEdit});
  }
  if (!canEdit) return json({error: "当前账号只有浏览权限"}, 403);
  if (request.headers.get("Origin") !== url.origin || request.headers.get("Sec-Fetch-Site") === "cross-site") return json({error: "请在本站内保存标签"}, 403);
  try {
    const body = await readBody(request);
    return await stub.fetch(new Request("https://tags/state", {method: "PUT", body: JSON.stringify(body)}));
  } catch (error) { return json({error: error.message}, 400); }
}

export default {async fetch(request, env) {
  try { return await handleRequest(request, env); }
  catch { return json({error: "在线存储暂时不可用，请稍后重试"}, 503); }
}};
