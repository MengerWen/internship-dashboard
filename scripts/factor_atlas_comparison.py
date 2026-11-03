"""把两个市场的已验收汇总配成一对一列对照，不读取逐股票日数据。"""
import base64
from collections import defaultdict
import gzip
import json
from pathlib import Path
import re

import numpy as np


METRICS = ('pearson_ic', 'rank_ic', 'rank_nw_t', 'rank_icir', 'g10_g1')


def decode_summary(path):
    match = re.fullmatch(r'window\.szseAtlasLoaded\(("[^"]+"),("[^"]+")\);', Path(path).read_text(encoding='utf-8'))
    if not match:
        raise ValueError(f'汇总封装格式不符：{path}')
    return json.loads(match[1]), json.loads(gzip.decompress(base64.b64decode(json.loads(match[2]), validate=True)))


def pair_columns(sse, szse):
    """先精确列名，再按唯一定义和方向补配；任何歧义都拒绝。"""
    def index(rows, identity):
        result = defaultdict(list)
        for i, row in enumerate(rows):
            result[identity(row['metadata'])].append(i)
        return result

    name = lambda m: m['factor_id']
    definition = lambda m: (m['definition_key'], m['projection'])
    for rows in (sse, szse):
        if any(len(v) != 1 for v in index(rows, name).values()):
            raise ValueError('市场内列名重复')
    exact, logical = index(szse, name), index(szse, definition)
    pairs, used = [], set()
    for i, row in enumerate(sse):
        m = row['metadata']
        candidates = exact.get(name(m), [])
        method = 'factor_id'
        if not candidates:
            candidates = logical.get(definition(m), [])
            method = 'definition_projection'
        if len(candidates) > 1:
            raise ValueError(f'定义配对有歧义：{name(m)}')
        if not candidates:
            continue
        j = candidates[0]
        if j in used:
            raise ValueError('一个深市列被重复配对')
        if definition(m) != definition(szse[j]['metadata']) or m['source'] != szse[j]['metadata']['source']:
            raise ValueError('同名列的定义、方向或来源不符')
        used.add(j)
        pairs.append((i, j, method))
    paired_sse = {i for i, _, _ in pairs}
    return pairs, [name(r['metadata']) for i, r in enumerate(sse) if i not in paired_sse], [name(r['metadata']) for j, r in enumerate(szse) if j not in used]


def metrics(factor):
    period = factor['periods'][0]
    values = [period['ic'][0][0], period['ic'][1][0], period['ic'][1][3], period['ic'][1][5], period['spread'][0][0]]
    return [float(v) if v is not None and np.isfinite(v) else None for v in values]


def rank_correlation(pairs):
    finite = [(a, b) for a, b in pairs if a is not None and b is not None]
    if len(finite) < 2:
        return None
    def ranks(values):
        order = np.argsort(values, kind='stable')
        result = np.empty(len(values), dtype=float)
        start = 0
        while start < len(order):
            stop = start + 1
            while stop < len(order) and values[order[stop]] == values[order[start]]:
                stop += 1
            result[order[start:stop]] = (start + stop - 1) / 2
            start = stop
        return result
    x, y = (ranks(np.array(v)) for v in zip(*finite))
    if not np.ptp(x) or not np.ptp(y):
        return None
    return float(np.corrcoef(x, y)[0, 1])


def compare_contexts(sse, szse):
    first = next(iter(sse))
    pairs, sse_only, szse_only = pair_columns(sse[first]['factors'], szse[first]['factors'])
    columns = []
    for i, j, method in pairs:
        a, b = sse[first]['factors'][i]['metadata'], szse[first]['factors'][j]['metadata']
        columns.append([a['factor_id'], b['factor_id'], a['source'], method])
    contexts = {}
    for key, data in sse.items():
        other = szse[key]
        if data['dates'] != other['dates']:
            raise ValueError(f'两市对照日期不一致：{key}')
        current, left, right = pair_columns(data['factors'], other['factors'])
        if current != pairs or left != sse_only or right != szse_only:
            raise ValueError('不同上下文的列身份或顺序变化')
        rows = []
        for i, j, _ in pairs:
            a, b = metrics(data['factors'][i]), metrics(other['factors'][j])
            same = bool(np.sign(a[1]) == np.sign(b[1])) if a[1] is not None and b[1] is not None else None
            rows.append([*a, *b, same])
        groups = []
        for source in ('all', 'old', 'cancel_buy', 'cancel_sell', 'depth'):
            selected = [r for c, r in zip(columns, rows) if source == 'all' or c[2] == source]
            valid = [r for r in selected if r[10] is not None]
            groups.append([source, len(selected), len(valid), sum(r[10] for r in valid), rank_correlation([(r[1], r[6]) for r in selected])])
        contexts[key] = dict(rows=rows, groups=groups)
    return dict(schema='sse-szse-atlas-comparison-v1', metrics=list(METRICS), columns=columns,
                sse_only=sse_only, szse_only=szse_only, contexts=contexts)
