/**
 * POST /api/feedback — write one reader complaint into the shared Feishu Bitable.
 *
 * The site is static; this is the only server-side route on it. It is marked
 * `prerender = false`, which makes the Cloudflare adapter emit it as an SSR
 * route and add it to `_routes.json`. A `functions/` directory is not an option
 * here: the adapter already produces `dist/_worker.js`, and Cloudflare refuses
 * to run both.
 *
 * Credentials come from one environment variable, `FEISHU_FEEDBACK`, shaped
 * `<app_id>:<app_secret>:<bitable_app_token>:<table_id>`. It is set in the
 * Cloudflare Pages project, never committed. If it is absent the route answers
 * 503 and the form tells the reader plainly that nothing was sent, rather than
 * faking a thank-you.
 */
import type { APIRoute } from "astro";

export const prerender = false;

const MAX_BODY = 4096;
const MAX_TEXT = 1200;

/** Single-select values must match the options created in the Bitable exactly. */
const SATISFACTION: Record<string, string> = {
  good: "很好 · 直接能用",
  meh: "还行 · 有点绕",
  bad: "难用 · 用不下去",
};
const DEVICE: Record<string, string> = { mobile: "手机", desktop: "桌面" };

type Env = { FEISHU_FEEDBACK?: string };

let cachedToken: { value: string; expires: number } | null = null;

function trim(value: unknown, limit = MAX_TEXT): string {
  return typeof value === "string" ? value.trim().slice(0, limit) : "";
}

async function tenantToken(cred: string[]): Promise<string> {
  const [appId, appSecret] = cred;
  if (cachedToken && cachedToken.expires > Date.now()) return cachedToken.value;

  const res = await fetch("https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ app_id: appId, app_secret: appSecret }),
  });
  const data = (await res.json()) as { code?: number; msg?: string; tenant_access_token?: string; expire?: number };
  if (data.code !== 0 || !data.tenant_access_token) {
    throw new Error(`feishu auth failed: ${data.code} ${data.msg ?? ""}`);
  }
  // renew a minute early so a long-lived isolate never sends an expired token
  cachedToken = { value: data.tenant_access_token, expires: Date.now() + ((data.expire ?? 7200) - 60) * 1000 };
  return cachedToken.value;
}

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json; charset=utf-8", "Cache-Control": "no-store" },
  });
}

export const POST: APIRoute = async ({ request, locals }) => {
  const declared = Number(request.headers.get("content-length") ?? 0);
  if (declared > MAX_BODY) return json({ ok: false, error: "too large" }, 413);

  let raw: string;
  try {
    raw = await request.text();
  } catch {
    return json({ ok: false, error: "unreadable body" }, 400);
  }
  if (raw.length > MAX_BODY) return json({ ok: false, error: "too large" }, 413);

  let payload: Record<string, unknown>;
  try {
    payload = JSON.parse(raw) as Record<string, unknown>;
  } catch {
    return json({ ok: false, error: "bad json" }, 400);
  }

  // A bot fills every input it finds. The honeypot is hidden from people and
  // the minimum dwell time catches scripted posts, both answered with a 200 so
  // the sender learns nothing about why it was dropped.
  if (trim(payload.website)) return json({ ok: true });
  const dwell = Number(payload.dwell ?? 0);
  if (Number.isFinite(dwell) && dwell > 0 && dwell < 1500) return json({ ok: true });

  const complaint = trim(payload.complaint);
  const wanted = trim(payload.wanted);
  const satisfaction = SATISFACTION[trim(payload.satisfaction)];
  if (!complaint && !wanted && !satisfaction) {
    return json({ ok: false, error: "nothing to record" }, 400);
  }

  const env = ((locals as { runtime?: { env?: Env } }).runtime?.env ?? {}) as Env;
  const credential = env.FEISHU_FEEDBACK ?? (globalThis as { process?: { env?: Env } }).process?.env?.FEISHU_FEEDBACK ?? "";
  const cred = credential.split(":");
  if (cred.length !== 4 || !cred[1]) {
    // Deliberately loud in the response body: the reader deserves to know the
    // note did not arrive, and the operator needs to see the cause immediately.
    return json({ ok: false, error: "feedback is not configured yet" }, 503);
  }
  const [, , appToken, tableId] = cred;

  const fields: Record<string, unknown> = {
    提交时间: Date.now(),
    站点: "ctd-guide.wiki",
    页面: trim(payload.page, 200) || "/values/",
    处理状态: "待看",
  };
  if (satisfaction) fields.满意度 = satisfaction;
  if (complaint) fields.吐槽 = complaint;
  if (wanted) fields.想做什么 = wanted;

  const deal = trim(payload.deal, 500);
  if (deal) fields.当前这手牌 = deal;

  const device = DEVICE[trim(payload.device)];
  if (device) fields.设备 = device;

  const viewport = trim(payload.viewport, 40);
  if (viewport) fields.视口 = viewport;

  const referrer = trim(payload.referrer, 300);
  if (referrer) fields.来源页面 = referrer;

  const version = trim(payload.version, 40);
  if (version) fields.版本 = version;

  try {
    const token = await tenantToken(cred);
    const res = await fetch(
      `https://open.feishu.cn/open-apis/bitable/v1/apps/${appToken}/tables/${tableId}/records`,
      {
        method: "POST",
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        body: JSON.stringify({ fields }),
      },
    );
    const data = (await res.json()) as { code?: number; msg?: string };
    if (data.code !== 0) {
      console.error("bitable write rejected", data.code, data.msg);
      return json({ ok: false, error: "could not save" }, 502);
    }
  } catch (err) {
    console.error("feedback failed", err);
    return json({ ok: false, error: "could not save" }, 502);
  }

  return json({ ok: true });
};

export const GET: APIRoute = () => json({ ok: false, error: "POST only" }, 405);
