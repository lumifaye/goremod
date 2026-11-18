// Supabase Edge Function "gore-hardmode-download": the download link of the mod.
//
//   https://abbvdidkxhdrzapvbidf.supabase.co/functions/v1/gore-hardmode-download
//
// The zip lies in a private storage bucket. This asks for the login (the browser's own user/password box) and
// sends whoever knows it on to a link to the file that is good for two minutes.
// The login is not in this file: it is in the project's secrets, DOWNLOAD_USER and DOWNLOAD_PASS.
// (Deployed with "verify JWT" off, so that a browser can open it.)

const PROJECT = "https://abbvdidkxhdrzapvbidf.supabase.co";
const BUCKET = "mod-transfer-48bfea945611a69b";
const OBJECT = "067c0c1bfe4e5f11d3e171bf651a4790/Gore-Hardmode.zip";
const FILE_NAME = "Gore-Hardmode.zip";
const REALM = "GORE / Hard-Mode download";
const LINK_SECONDS = 120;

function text(status: number, body: string, headers: Record<string, string> = {}) {
  return new Response(body, {
    status,
    headers: { "Content-Type": "text/plain; charset=utf-8", "Cache-Control": "no-store", ...headers },
  });
}

function same(a: string, b: string) {
  // (Every character is looked at, whatever the outcome.)
  let differ = a.length ^ b.length;
  const length = Math.max(a.length, b.length);
  for (let i = 0; i < length; i++) differ |= (a.charCodeAt(i) || 0) ^ (b.charCodeAt(i) || 0);
  return differ === 0;
}

function credentials(request: Request) {
  const match = /^Basic\s+([A-Za-z0-9+/=]+)\s*$/i.exec(request.headers.get("authorization") ?? "");
  if (match === null) return null;
  let decoded: string;
  try {
    decoded = new TextDecoder().decode(Uint8Array.from(atob(match[1]), (c) => c.charCodeAt(0)));
  } catch {
    return null;
  }
  const colon = decoded.indexOf(":");
  if (colon < 0) return null;
  return { user: decoded.slice(0, colon), pass: decoded.slice(colon + 1) };
}

async function signedLink() {
  const key = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") ?? "";
  const response = await fetch(`${PROJECT}/storage/v1/object/sign/${BUCKET}/${OBJECT}`, {
    method: "POST",
    headers: { Authorization: `Bearer ${key}`, apikey: key, "Content-Type": "application/json" },
    body: JSON.stringify({ expiresIn: LINK_SECONDS }),
  });
  if (!response.ok) {
    console.error(`signing failed: ${response.status} ${await response.text()}`);
    return null;
  }
  const { signedURL } = await response.json();
  if (typeof signedURL !== "string") return null;
  return `${PROJECT}/storage/v1${signedURL}&download=${encodeURIComponent(FILE_NAME)}`;
}

Deno.serve(async (request: Request) => {
  if (request.method !== "GET" && request.method !== "HEAD") {
    return text(405, "Method not allowed.\n", { Allow: "GET, HEAD" });
  }
  const user = Deno.env.get("DOWNLOAD_USER");
  const pass = Deno.env.get("DOWNLOAD_PASS");
  if (!user || !pass) return text(503, "The download is not set up: no login has been configured.\n");

  const given = credentials(request);
  const userOk = given !== null && same(given.user, user);
  const passOk = given !== null && same(given.pass, pass);
  if (!userOk || !passOk) {
    if (given !== null) await new Promise((resolve) => setTimeout(resolve, 500)); // (guessing is slow)
    return text(401, "Login required.\n", { "WWW-Authenticate": `Basic realm="${REALM}", charset="UTF-8"` });
  }

  const link = await signedLink();
  if (link === null) return text(502, "The file is not available right now. Try again in a moment.\n");
  return new Response(null, { status: 302, headers: { Location: link, "Cache-Control": "no-store" } });
});
