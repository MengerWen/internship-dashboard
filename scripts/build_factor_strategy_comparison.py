"""从冻结 B0 和签收的版本结果构建 11.16 比较页。"""
from __future__ import annotations

import argparse
import hashlib
from html import escape
import json
from math import isclose, isfinite
from pathlib import Path

from build_20261109_fill_rules import ASSET_LIMIT, encode_data
from build_20261116_g2_comparison import ASSET as HISTORICAL_G2
from frozen_baseline import ROOT, baseline_data, protect_outputs, verify


HERE = Path(__file__).parent
DAILY = ROOT / 'content/daily'
INDEX = ROOT / 'content/assets/factor-strategy-comparison/manifest.json'
ARCHIVE = DAILY / '2026-11-13.show.html'
PAGE = DAILY / '2026-11-16.show.html'
NOTE = DAILY / '2026-11-16.md'
TITLE = '因子评测与策略比较'
REPORT = ('https://github.com/MengerWen/sirui-quant-research/blob/main/reports/2026-11/'
          '2026-11-16-factor-evaluation-and-strategy-comparison.md')


def read(path, expected):
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != expected:
        raise ValueError(f'结果 SHA-256 不符：{path.name}')
    return json.loads(data)


def close(left, right):
    return isclose(left, right, rel_tol=1e-10, abs_tol=6e-13)


def pair(row):
    if len(row) < 2 or not all(isfinite(x) for x in row[:2]):
        raise ValueError('沪深金额不完整')
    return row[:2]


def pack_version(source, base, name, *, baseline_sha, legacy=False):
    dates = source['dates']
    if not dates or dates != sorted(set(dates)) or dates != base['dates'][:len(dates)]:
        raise ValueError('版本日期须对应 B0 已签收的连续区间')
    if source['identity']['baseline_sha256'] != baseline_sha or source['identity']['fees'] != base['fees']:
        raise ValueError('版本采用不同的底仓账簿或成交费用')
    for weight in base['base']:
        if (not all(close(a, b) for a, b in zip(source['initial'][weight], base['initial'][weight], strict=True))
                or len(source['base'][weight]) != len(dates)
                or any(not all(close(a, b) for a, b in zip(pair(r), s, strict=True))
                    for r, s in zip(source['base'][weight], base['base'][weight][:len(dates)], strict=True))):
            raise ValueError('版本底仓路径与 B0 不同')
    keys = set(base['series'])
    original, candidate = source['series']['baseline'], source['series'][name]
    if set(candidate) != keys or set(original) != keys:
        raise ValueError('版本须覆盖 B0 全部 192 个条件')
    for key in keys:
        if len(original[key]) != len(dates) or len(candidate[key]) != len(dates):
            raise ValueError(f'配置的日期数不同：{key}')
        for row, expected in zip(original[key], base['series'][key][:len(dates)], strict=True):
            if not all(close(a, b) for a, b in zip(pair(row), expected[:2], strict=True)):
                raise ValueError(f'配置的 B0 增量不同：{key}')
            if not legacy and row[2:] != expected[2:]:
                raise ValueError(f'配置的 B0 成交计数不同：{key}')
    traded = source.get('trading', {}).get(name)
    if traded is not None:
        if set(traded) != keys or any(len(v) != len(dates) for v in traded.values()):
            raise ValueError('版本交易明细覆盖不同')
        traded = {key: [[m[0], m[2], z[0], z[2]] for m, z in rows] for key, rows in traded.items()}
    return dict(dates=dates, series={k: [pair(row) for row in rows] for k, rows in candidate.items()}, trading=traded)


def baseline_payload(data):
    return dict(dates=data['dates'], series={key: [pair(r) for r in rows] for key, rows in data['series'].items()},
        trading={key: [[m[0],m[2],z[0],z[2]] for m,z in rows] for key,rows in data['trading'].items()})


def research_metadata(research):
    import yaml
    prereg = yaml.safe_load((research / 'PLAN/factor_preregister_high_frequency_increment_v1.yaml').read_bytes())
    families = research / 'research/factor-candidates/families'
    factors = []
    for row in prereg['records']:
        family = yaml.safe_load((families / f'{row["family_id"]}.yaml').read_bytes())
        factors.append(dict(id=row['variant_id'], family=row['family_id'], name=family['name'],
            batch=row['batch'], side=row.get('side','双侧'), scope=family['scope'],
            market='沪市 / 深市', definition=family['logic']['observation'],
            hypothesis=family['logic']['prediction'], input=row['source_contract'],
            nearest=family['overlap']['nearest_existing'].split('。',1)[0],
            variant=row['definition'], state='待审核及数据准入',
            coverage=None, validDays=None, zero=None, constant=None, ic=None, rankIc=None,
            icir=None, hac=None, spread=None, correlation=None, stateReason='尚无通过审核的量化结果'))
    versions = [dict(id='B0', parent=None, label='固定 B0', markets='沪市原模型＋深市原模型',
                     features='沪市 340 列；深市 344 列', coverage=566, status='固定基准')]
    for experiment in prereg['experiments']:
        id_ = experiment['version_id']
        if id_ == 'G2':
            versions.append(dict(id='G2',parent='B0',label='沪市原模型＋深市 G2',
                markets='沪市原模型；深市 G2',features='深市新增 9 族、34 列',coverage=308,
                status='开发 OOF 已签收；历史 Test 尚未签收'))
        else:
            batches = experiment['batches']
            count = sum(row['batch'] in batches for row in prereg['records'])
            versions.append(dict(id=id_,parent='B0',label='高频联合' if id_ == 'HALL' else id_,
                markets='两市分别准入',features=f'预注册 {count} 列',coverage=0,
                status='待分批审核和数据准入' if id_ != 'HALL' else '待独立批次完成'))
    return versions, factors


def build(args):
    lock = verify()
    protect_outputs([INDEX,PAGE,NOTE])
    archive = ARCHIVE.read_text(encoding='utf-8')
    data = baseline_data(archive)
    versions, factors = research_metadata(args.research)
    signed_results = {name: (Path(path), digest) for name, path, digest in args.result}
    if len(signed_results) != len(args.result) or (args.g2 and 'G2' in signed_results):
        raise ValueError('同一个版本只能有一份签收结果')
    if args.g2:
        signed_results['G2'] = args.g2, args.sha256
    version_index = {v['id']: v for v in versions if v['id'] != 'B0'}
    if not set(signed_results) <= version_index.keys():
        raise ValueError('结果须对应已登记的候选版本')
    results = dict(B0=baseline_payload(data))
    for name, (path, digest) in signed_results.items():
        raw = read(path, digest)
        identity = raw['identity']
        binding = next((r for r in identity['versions'] if r['version_id'] == name), None)
        if (identity['schema'] != 'csi2000-versioned-comparison-v1' or len(raw['dates']) != 566
                or binding is None or binding['parent_version_id'] != version_index[name]['parent']):
            raise ValueError(f'{name} 完整结果须绑定已登记父版和 566 日账簿')
        results[name] = pack_version(raw, data, name, baseline_sha=lock['result']['sha256'])
        version_index[name].update(coverage=566,status='开发 OOF 和历史 Test 已签收',result_sha256=digest,
                                   model_source=identity['candidate_model'])
    if 'G2' not in results:
        raw = json.loads(HISTORICAL_G2.read_bytes())
        if len(raw['dates']) != 308 or len(raw['identity']['dates']) != 308:
            raise ValueError('既有 G2 开发期身份不同')
        results['G2'] = pack_version(raw,data,'G2',baseline_sha=lock['result']['sha256'],legacy=True)
        versions[1]['result_sha256'] = raw['source_sha256']
    manifest = dict(schema='factor-strategy-comparison-v1', baseline='B0', default_candidate='G2',
        study_days=566, input_days=683, configurations=192, versions=versions, factors=factors)
    packed = dict(manifest, dates=data['dates'], stages=data['stages'], initial=data['initial'],
        base=data['base'], results=results)
    page = (HERE/'factor_strategy_comparison.html').read_text(encoding='utf-8')
    page = page.replace('__PAYLOAD__', encode_data(packed)).replace('__REPORT__', escape(REPORT, quote=True))
    page = page.replace('__SCRIPT__',(HERE/'factor_strategy_comparison.js').read_text(encoding='utf-8'))
    page = page.replace('__COVERAGE__', str(versions[1]['coverage']))
    if len(page.encode()) > ASSET_LIMIT:
        raise ValueError('比较页超过单份静态资源上限')
    INDEX.parent.mkdir(parents=True, exist_ok=True)
    INDEX.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
    PAGE.write_text(page,encoding='utf-8',newline='\n')
    NOTE.write_text(f'''---
title: "{TITLE}"
date: 2026-11-16
published: "2026-11-16T15:17:43+08:00"
stage: model
show_source: 2026-11-16.show.html
summary: "用固定 B0 比较各批候选的绝对收益、同底仓超额及增量。"
---

# {TITLE}

固定 B0 覆盖 566 个交易日、192 个条件组合。G2 只替换深市模型，沪市沿用原模型，当前已签收 {versions[1]['coverage']} 日。

展示页可用同一组条件比较沪深两市的 11:30、收盘策略，切换沪深合计、绝对收益、同底仓超额与相对 B0 增量。未取得结果的区间保留缺口。新高频批次在因子表中列明定义、审核和准入状态。

[11.13 固定基准档案](2026-11-13.show.html) · [研究记录与统计合同]({REPORT})
''',encoding='utf-8',newline='\n')
    verify()
    print(json.dumps(dict(days=len(data['dates']),g2_days=len(results['G2']['dates']),configurations=len(data['series']),
                          variants=len(factors),page_bytes=PAGE.stat().st_size)))


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--research',type=Path,required=True)
    parser.add_argument('--g2',type=Path)
    parser.add_argument('--sha256')
    parser.add_argument('--result', action='append', nargs=3, default=[], metavar=('VERSION','PATH','SHA256'))
    args=parser.parse_args()
    if bool(args.g2) != bool(args.sha256):
        parser.error('--g2 和 --sha256 必须一起提供')
    build(args)
