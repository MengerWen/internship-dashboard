const { createHash } = require('node:crypto');
const { execFileSync } = require('node:child_process');
const fs = require('node:fs');
const { registerHooks } = require('node:module');
const path = require('node:path');
const { pathToFileURL } = require('node:url');

const ROOT = path.resolve(__dirname, '..');
const CLI = path.join(ROOT, 'node_modules/wrangler/wrangler-dist/cli.js');
const ASSET_SOURCE = 'content/assets/';

function sha256(bytes) {
    return createHash('sha256').update(bytes).digest('hex');
}

function fileSignature(file) {
    const stat = fs.lstatSync(file, { bigint: true });
    if (!stat.isFile()) return null;
    return [stat.dev, stat.ino, stat.size, stat.mtimeNs, stat.ctimeNs].join(':');
}

function writeJson(file, value) {
    const temp = `${file}.${process.pid}.tmp`;
    fs.writeFileSync(temp, JSON.stringify(value));
    fs.renameSync(temp, file);
}

function copyAssets(output, manifestFile) {
    const paths = execFileSync('git', ['ls-files', '-z', '--cached', '--', ASSET_SOURCE], {
        cwd: ROOT, encoding: 'utf8',
    }).split('\0').filter(Boolean);
    const copies = Object.create(null);
    for (const source of paths) {
        const relative = source.slice(ASSET_SOURCE.length);
        const input = path.join(ROOT, source);
        const destination = path.join(output, 'assets', relative);
        const signature = fileSignature(input);
        fs.mkdirSync(path.dirname(destination), { recursive: true });
        fs.copyFileSync(input, destination);
        if (signature && fileSignature(input) === signature) {
            copies[relative] = [fileSignature(destination), signature];
        }
    }
    writeJson(manifestFile, copies);
}

let cache;
let hits = 0;
let misses = 0;

function assetHash(file, calculate) {
    const relative = path.relative(cache.assetRoot, file).split(path.sep).join('/');
    const copy = cache.copies[relative];
    if (!Array.isArray(copy) || !copy[0] || fileSignature(file) !== copy[0]) return calculate();

    // Reuse only a fresh, unchanged copy of the same source file. Wrangler includes the extension in its hash.
    const key = `${copy[1]}:${path.extname(file)}`;
    const saved = cache.previous[key];
    if (typeof saved === 'string' && /^[a-f0-9]{32}$/.test(saved)) {
        hits++;
        cache.next[key] = saved;
        return saved;
    }
    misses++;
    const hash = calculate();
    if (fileSignature(file) === copy[0]) cache.next[key] = hash;
    return hash;
}

function saveHashes() {
    console.log(`静态资源哈希缓存命中 ${hits}，重算 ${misses}。`);
    try {
        writeJson(cache.file, { cli: cache.cliDigest, hashes: cache.next });
    } catch (error) {
        console.warn(`无法保存静态资源哈希缓存 ${error.code ?? error.message}`);
    }
}

function enableCache(manifestFile) {
    if (typeof registerHooks !== 'function') {
        console.warn('当前 Node.js 不支持加载哈希缓存，使用 Wrangler 全量计算。');
        return;
    }
    const cliUrl = pathToFileURL(CLI).href;
    registerHooks({ load(url, context, nextLoad) {
        if (url !== cliUrl) return nextLoad(url, context);
        const source = fs.readFileSync(CLI, 'utf8');
        const hashBody = [
            '      const contents = fs12.readFileSync(filepath);',
            '      const base64Contents = contents.toString("base64");',
            '      const extension2 = path25.extname(filepath).substring(1);',
            '      return blake3Wasm.hash(base64Contents + extension2).toString("hex").slice(0, 32);',
        ].join('\n');
        const manifestEnd = '      return manifest;\n    }, "buildAssetManifest");';
        if ([hashBody, manifestEnd].some(anchor => source.split(anchor).length !== 2)) {
            console.warn('当前 Wrangler 不兼容哈希缓存，使用 Wrangler 全量计算。');
            return nextLoad(url, context);
        }
        const cliDigest = sha256(source);
        const file = path.join(path.dirname(manifestFile), 'dashboard-wrangler-hashes.json');
        let previous = {};
        try {
            const saved = JSON.parse(fs.readFileSync(file, 'utf8'));
            if (saved.cli === cliDigest && saved.hashes) previous = saved.hashes;
        } catch { /* 缓存缺失或损坏时从头计算。 */ }
        let copies;
        try {
            copies = JSON.parse(fs.readFileSync(manifestFile, 'utf8'));
            if (!copies || typeof copies !== 'object') throw new Error('Invalid asset copy manifest');
        } catch {
            console.warn('缺少有效的本次构建文件清单，使用 Wrangler 全量计算。');
            return nextLoad(url, context);
        }
        cache = { assetRoot: path.join(ROOT, 'dist', 'assets'), copies, cliDigest, file, previous, next: Object.create(null) };
        const hook = `require(${JSON.stringify(__filename)})`;
        const patched = source
            .replace(hashBody, `      return ${hook}.assetHash(filepath, () => {\n${hashBody}\n      });`)
            .replace(manifestEnd, `      ${hook}.saveHashes();\n${manifestEnd}`);
        return { format: 'commonjs', source: patched, shortCircuit: true };
    } });
}

if (require.main === module) {
    copyAssets(process.argv[2], process.argv[3]);
} else if (process.env.DASHBOARD_ASSET_COPY_MANIFEST && path.basename(process.argv[1] ?? '') === 'cli.js') {
    enableCache(process.env.DASHBOARD_ASSET_COPY_MANIFEST);
}

module.exports = { assetHash, saveHashes };
