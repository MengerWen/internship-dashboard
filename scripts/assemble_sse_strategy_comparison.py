"""Package the signed Shanghai strategy result for the 11.16 report."""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from math import isclose, isfinite
from pathlib import Path
import re

from assemble_sse_candidate_atlas import ASSETS, REPORT, encode
from pack_factor_comparison_data import read_market_data

LONG_VERSION = 'SSE+'
LEDGER_STAGES = [('oof', 'development', 308), ('test_seen', 'seen', 176), ('test_unseen', 'unseen', 82)]


def close(left, right):
    return isclose(left, right, rel_tol=1e-10, abs_tol=1e-12)


def compare(signed, baseline):
    identity = signed['identity']
    dates = signed['dates']
    completed = identity['sse_model']
    if (identity['schema'] != 'csi2000-versioned-comparison-v1' or completed['version_id'] != LONG_VERSION
            or completed['status'] != 'complete' or completed['models'] != 50
            or dates != baseline['dates'] or len(dates) != 566
            or signed['initial'] != baseline['initial'] or signed['base'].keys() != baseline['base'].keys()
            or signed['stages'] != [phase for phase, _, days in LEDGER_STAGES for _ in range(days)]
            or baseline['stages'] != [phase for _, phase, days in LEDGER_STAGES for _ in range(days)]):
        raise ValueError('The Shanghai replay is not paired to the report baseline')
    for weight, path in signed['base'].items():
        archived = baseline['base'][weight]
        # The display archive stores base balances rounded to 12 decimal places.
        if len(path) != 566 or len(archived) != len(path) or any(
                len(day) != 2 or len(old) != 2 or any(abs(a-b) > 1e-12 for a,b in zip(day,old,strict=True))
                for day,old in zip(path,archived,strict=True)):
            raise ValueError(f'Signed baseline balances differ: {weight}')
    curves = signed['series'][LONG_VERSION]
    same = set(baseline['series'])
    if len(same) != 192 or set(curves) != same or set(signed['trading'][LONG_VERSION]) != same:
        raise ValueError('Shanghai replay configuration coverage differs')
    returns = {}
    for key in sorted(same):
        reference = signed['series']['baseline'][key]
        expected = baseline['series'][key]
        candidate = curves[key]
        trades = signed['trading'][LONG_VERSION][key]
        if any(len(rows) != 566 for rows in (reference, expected, candidate, trades)):
            raise ValueError(f'Shanghai replay calendar differs: {key}')
        for lhs, rhs in zip(reference, expected, strict=True):
            if any(not close(a, b) for a, b in zip(lhs[:2], rhs[:2], strict=True)) or lhs[2:] != rhs[2:]:
                raise ValueError(f'Baseline replay values differ: {key}')
        if any(len(row) != 6 or not all(isfinite(x) for x in row) for row in candidate):
            raise ValueError(f'Invalid candidate replay values: {key}')
        if any(len(row) != 2 or any(len(trade) != 3 or not all(isfinite(x) for x in trade)
                                   or trade[0] < 0 for trade in row) for row in trades):
            raise ValueError(f'Invalid entry-day batch accounting: {key}')
        returns[key] = [[(gross - fees) / entry if entry > 0 else None for entry, gross, fees in day]
                        for day in trades]
    signal = signed['paired_signal']
    matched = {version: {} for version in ['B0', LONG_VERSION]}
    for horizon in ('morning', 'close'):
        left, right = (signal[version][horizon] for version in matched)
        if len(left) != 566 or len(right) != len(left) or not all(
                len(a) == len(b) == 4 and a[2:] == b[2:] for a, b in zip(left, right, strict=True)):
            raise ValueError('Shanghai signal pairings differ')
    at = 0
    for _, phase, length in LEDGER_STAGES:
        for version in matched:
            matched[version][phase] = [signal[version][h][at:at+length] for h in ('morning', 'close')] + [[], []]
        at += length
    return dict(dates=dates, retained=completed['retained'], series=curves, tradeReturns=returns,
                pairedSignal=matched)


def assemble(template, ledger, expected, output):
    raw = ledger.read_bytes()
    actual = sha256(raw).hexdigest()
    if actual != expected:
        raise ValueError('Shanghai strategy receipt checksum differs')
    page = template.read_text(encoding='utf-8')
    baseline = read_market_data(page)
    signed = json.loads(raw)
    packet = compare(signed, baseline)
    packed = encode(packet)
    buffer = f'window.csi2000SseStrategy="{packed}";\n'.encode('ascii')
    digest = sha256(buffer).hexdigest()
    name = 'sse-strategy-' + digest[:12] + '.js'
    result = re.sub(r'(?:__SSE_STRATEGY_ASSET__|sse-strategy-[0-9a-f]{12}\.js)', name, page, count=1)
    if result.count(name) != 1 or len(buffer) > 24 << 20:
        raise ValueError('Shanghai strategy loader or asset size differs')
    (ASSETS / name).write_bytes(buffer)
    identity = signed['identity']
    receipt = dict(schema='sse-strategy-sidecar-v1', file=name, sha256=digest, days=566, configurations=192,
                   retained=packet['retained'], ledger_sha256=actual, ledger_revision=identity['revision'],
                   model_revision=identity['sse_model']['revision'],
                   frozen_hash=identity['sse_model']['frozen_hash'])
    (ASSETS / 'sse-strategy.json').write_text(json.dumps(receipt, indent=2)+'\n', encoding='utf-8')
    output.write_text(result, encoding='utf-8', newline='\n')
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ledger', type=Path, required=True)
    parser.add_argument('--sha256', required=True)
    parser.add_argument('--template', type=Path, default=REPORT)
    parser.add_argument('--output', type=Path, default=REPORT)
    args = parser.parse_args()
    result = assemble(args.template, args.ledger, args.sha256, args.output)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
