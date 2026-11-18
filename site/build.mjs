
import { createHash } from 'node:crypto';
import { execFileSync } from 'node:child_process';
import { mkdirSync, readdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import zlib from 'node:zlib';

const SITE = dirname(fileURLToPath(import.meta.url));
const MOD = resolve(SITE, '..');
const OUT = resolve(process.argv[2] ?? join(SITE, 'public'));

const FOLDER = 'Gore-Hardmode';
const ZIP_NAME = 'Gore-Hardmode.zip';
const SKIP_AT_TOP = new Set(['site', 'fork', 'release', 'dist', 'node_modules', 'Untitled.png', 'WiiU', 'PC', 'VR', 'Android']);

function collect(dir, prefix, list) {
    for (const entry of readdirSync(dir, { withFileTypes: true })) {
        if (entry.name.startsWith('.')) continue;
        if (prefix === '' && SKIP_AT_TOP.has(entry.name)) continue;
        const path = prefix + entry.name;
        if (entry.isDirectory()) collect(join(dir, entry.name), path + '/', list);
        else if (entry.isFile()) list.push(path);
    }
    return list;
}

let crcTable = null;
function crc32(data) {
    if (typeof zlib.crc32 === 'function') return zlib.crc32(data) >>> 0;
    if (crcTable === null) {
        crcTable = new Uint32Array(256);
        for (let n = 0; n < 256; n++) {
            let c = n;
            for (let k = 0; k < 8; k++) c = (c & 1) ? (0xedb88320 ^ (c >>> 1)) : (c >>> 1);
            crcTable[n] = c >>> 0;
        }
    }
    let crc = 0xffffffff;
    for (let i = 0; i < data.length; i++) crc = crcTable[(crc ^ data[i]) & 0xff] ^ (crc >>> 8);
    return (crc ^ 0xffffffff) >>> 0;
}

function dosTime(date) {
    const time = (date.getUTCHours() << 11) | (date.getUTCMinutes() << 5) | (date.getUTCSeconds() >> 1);
    const day = ((date.getUTCFullYear() - 1980) << 9) | ((date.getUTCMonth() + 1) << 5) | date.getUTCDate();
    return { time, day };
}

function zip(files, date) {
    const { time, day } = dosTime(date);
    const parts = [];
    const central = [];
    let offset = 0;

    for (const file of files) {
        const name = Buffer.from(file.name, 'utf8');
        const packed = zlib.deflateRawSync(file.data, { level: 9 });
        const stored = packed.length >= file.data.length;
        const body = stored ? file.data : packed;
        const crc = crc32(file.data);

        const local = Buffer.alloc(30);
        local.writeUInt32LE(0x04034b50, 0);
        local.writeUInt16LE(20, 4);
        local.writeUInt16LE(0x0800, 6);
        local.writeUInt16LE(stored ? 0 : 8, 8);
        local.writeUInt16LE(time, 10);
        local.writeUInt16LE(day, 12);
        local.writeUInt32LE(crc, 14);
        local.writeUInt32LE(body.length, 18);
        local.writeUInt32LE(file.data.length, 22);
        local.writeUInt16LE(name.length, 26);
        local.writeUInt16LE(0, 28);

        const entry = Buffer.alloc(46);
        entry.writeUInt32LE(0x02014b50, 0);
        entry.writeUInt16LE((3 << 8) | 20, 4);
        entry.writeUInt16LE(20, 6);
        entry.writeUInt16LE(0x0800, 8);
        entry.writeUInt16LE(stored ? 0 : 8, 10);
        entry.writeUInt16LE(time, 12);
        entry.writeUInt16LE(day, 14);
        entry.writeUInt32LE(crc, 16);
        entry.writeUInt32LE(body.length, 20);
        entry.writeUInt32LE(file.data.length, 24);
        entry.writeUInt16LE(name.length, 28);
        entry.writeUInt32LE((0o100644 << 16) >>> 0, 38);
        entry.writeUInt32LE(offset, 42);

        parts.push(local, name, body);
        central.push(entry, name);
        offset += local.length + name.length + body.length;
    }

    const directory = Buffer.concat(central);
    const end = Buffer.alloc(22);
    end.writeUInt32LE(0x06054b50, 0);
    end.writeUInt16LE(files.length, 8);
    end.writeUInt16LE(files.length, 10);
    end.writeUInt32LE(directory.length, 12);
    end.writeUInt32LE(offset, 16);
    return Buffer.concat([...parts, directory, end]);
}

function git(...args) {
    try {
        return execFileSync('git', args, { cwd: MOD, stdio: ['ignore', 'pipe', 'ignore'] }).toString().trim();
    } catch {
        return '';
    }
}

function version() {
    const sha = process.env.VERCEL_GIT_COMMIT_SHA || git('rev-parse', 'HEAD');
    return /^[0-9a-f]{7,40}$/.test(sha) ? sha.slice(0, 7) : 'unknown';
}

function buildTime() {
    const seconds = Number(process.env.SOURCE_DATE_EPOCH || git('log', '-1', '--format=%ct'));
    return Number.isFinite(seconds) && seconds > 0 ? new Date(seconds * 1000) : new Date();
}

function megabytes(bytes) {
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

const paths = collect(MOD, '', []).sort();
if (!paths.includes('main.lua')) {
    console.error(`No main.lua in ${MOD}: this is not the mod. Nothing built.`);
    process.exit(1);
}
if (paths.length > 60000) {
    console.error(`${paths.length} files: more than this zip writer does.`);
    process.exit(1);
}

const now = buildTime();
const archive = zip(paths.map((path) => ({ name: `${FOLDER}/${path}`, data: readFileSync(join(MOD, path)) })), now);
if (archive.length >= 0xffffffff) {
    console.error('The zip is over 4 GB: more than this zip writer does.');
    process.exit(1);
}

const values = {
    ZIP: ZIP_NAME,
    FOLDER,
    SIZE: megabytes(archive.length),
    FILES: String(paths.length),
    VERSION: version(),
    DATE: now.toISOString().slice(0, 10),
    SHA256: createHash('sha256').update(archive).digest('hex'),
};
const page = readFileSync(join(SITE, 'index.html'), 'utf8')
    .replace(/\{\{([A-Z0-9]+)\}\}/g, (whole, key) => (key in values ? values[key] : whole));

rmSync(OUT, { recursive: true, force: true });
mkdirSync(OUT, { recursive: true });
writeFileSync(join(OUT, ZIP_NAME), archive);
writeFileSync(join(OUT, 'index.html'), page);
console.log(`${ZIP_NAME}: ${paths.length} files, ${values.SIZE}, version ${values.VERSION}, sha256 ${values.SHA256}`);
console.log(`written to ${OUT}`);
