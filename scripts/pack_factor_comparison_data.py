"""Split the stable 11.16 market data into content-addressed upload assets."""
from __future__ import annotations

from base64 import b64decode
from gzip import decompress
from hashlib import sha256
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / 'content/daily/2026-11-16.show.html'
ASSETS = ROOT / 'content/assets/factor-strategy-comparison'
PACKET = re.compile(r'(<script\b[^>]*\bid="csi2000-market-data"[^>]*>)([^<]+)(</script>)')
PART = re.compile(r'window\.(csi2000MarketPart[0-9]+)="([A-Za-z0-9+/=]+)";\n?')
MAX_BASE64_BYTES = 4 << 20


def read_encoded(page):
    match = PACKET.search(page)
    if match is None:
        raise ValueError('The 11.16 report has no market packet')
    if 'data-encoding="multipart"' not in match[1]:
        return match[2].strip()
    index = json.loads(match[2])
    parts = []
    for part in index['parts']:
        source = ASSETS / part['file']
        raw = source.read_bytes().replace(b"\r\n", b"\n")
        if sha256(raw).hexdigest() != part['sha256']:
            raise ValueError(f'Market packet part hash differs: {source.name}')
        parsed = PART.fullmatch(raw.decode('ascii'))
        if parsed is None or parsed[1] != part['key']:
            raise ValueError(f'Market packet part identity differs: {source.name}')
        parts.append(parsed[2])
    encoded = ''.join(parts)
    if sha256(encoded.encode('ascii')).hexdigest() != index['sha256']:
        raise ValueError('Complete market packet hash differs')
    return encoded


def read_market_data(page):
    return json.loads(decompress(b64decode(read_encoded(page), validate=True)))


def pack(page):
    match = PACKET.search(page)
    if match is None or 'data-encoding="multipart"' in match[1]:
        raise ValueError('Expected the original embedded market packet')
    encoded = read_encoded(page)
    part_index = []
    for index, i in enumerate(range(0, len(encoded), MAX_BASE64_BYTES)):
        key = f'csi2000MarketPart{index}'
        raw = f'window.{key}="{encoded[i:i+MAX_BASE64_BYTES]}";\n'.encode('ascii')
        digest = sha256(raw).hexdigest()
        name = f'market-packet-{digest[:12]}.js'
        (ASSETS / name).write_bytes(raw)
        part_index.append(dict(file=name, key=key, sha256=digest))
    metadata = json.dumps(dict(parts=part_index, sha256=sha256(encoded.encode('ascii')).hexdigest()),
                          separators=(',', ':'))
    markup = '<script id="csi2000-market-data" type="application/json" data-encoding="multipart">'
    result = page[:match.start()] + markup + metadata + match[3] + page[match.end():]
    if read_encoded(result) != encoded:
        raise ValueError('Round-trip market packet mismatch')
    return result


if __name__ == '__main__':
    page = REPORT.read_text(encoding='utf-8')
    REPORT.write_text(pack(page), encoding='utf-8', newline='\n')
