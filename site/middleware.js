// Vercel runs this before every request: nothing (not the page, not the zip) is served without the login.
// The login is not in this file. It is in the project's environment variables on Vercel:
//   DOWNLOAD_USER, DOWNLOAD_PASS
// Without them, nobody gets in.

const REALM = 'GORE / Hard-Mode download';

function same(a, b) {
    // (Every character is looked at, whatever the outcome: how long it takes says nothing about where they differ.)
    let differ = a.length ^ b.length;
    const length = Math.max(a.length, b.length);
    for (let i = 0; i < length; i++) {
        differ |= (a.charCodeAt(i) || 0) ^ (b.charCodeAt(i) || 0);
    }
    return differ === 0;
}

function credentials(request) {
    const header = request.headers.get('authorization') ?? '';
    const match = /^Basic\s+([A-Za-z0-9+/=]+)\s*$/i.exec(header);
    if (match === null) return null;
    let text;
    try {
        const bytes = Uint8Array.from(atob(match[1]), (c) => c.charCodeAt(0));
        text = new TextDecoder().decode(bytes);
    } catch {
        return null;
    }
    const colon = text.indexOf(':');
    if (colon < 0) return null;
    return { user: text.slice(0, colon), pass: text.slice(colon + 1) };
}

function refuse() {
    return new Response('Login required.\n', {
        status: 401,
        headers: {
            'WWW-Authenticate': `Basic realm="${REALM}", charset="UTF-8"`,
            'Content-Type': 'text/plain; charset=utf-8',
            'Cache-Control': 'no-store',
            'X-Robots-Tag': 'noindex, nofollow',
        },
    });
}

export default function middleware(request) {
    const user = process.env.DOWNLOAD_USER;
    const pass = process.env.DOWNLOAD_PASS;
    if (!user || !pass) {
        return new Response('The download is not set up: no login has been configured.\n', {
            status: 503,
            headers: { 'Content-Type': 'text/plain; charset=utf-8', 'Cache-Control': 'no-store' },
        });
    }

    const given = credentials(request);
    // (Both are compared, also when the first is already wrong.)
    const userOk = given !== null && same(given.user, user);
    const passOk = given !== null && same(given.pass, pass);
    if (!userOk || !passOk) return refuse();

    // Let the request through. (What `next()` of @vercel/functions returns.)
    return new Response(null, { headers: { 'x-middleware-next': '1' } });
}
