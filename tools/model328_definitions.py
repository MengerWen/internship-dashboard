"""Registry-backed descriptions for the frozen 328 input columns."""
from collections import Counter
from pathlib import Path
import re
import sys
ROOT = Path(__file__).resolve().parents[1]

def metadata(research, manifest, old_data):
    sys.path.insert(0, str(research / '因子/algobench/src'))
    from algobench.cancel_phase_registry import parse_cancel_phase_column, cancel_phase_registry_hash
    from algobench.depth_match_registry import depth_match_contract, depth_match_registry_hash
    from algobench.formal_model328_manifest import load_feature_manifest
    load_feature_manifest(research / '因子/algobench/configs/szse_model328_feature_manifest_v1.json')
    assert cancel_phase_registry_hash() == manifest['registry_hashes']['cancel']
    assert depth_match_registry_hash() == manifest['registry_hashes']['depth']
    from cancel_phase_math import report_equations
    from depth_match_math import formulas
    phase_math, depth_math = report_equations(), formulas()
    depth_specs = {f'{s["name"]}_{s["side"]}': s for s in depth_match_contract()['specs']}
    old_by_id = {f['metadata']['factor_id']: f['metadata'] for f in old_data['factors']}
    phase_titles = ['事件对集中度', '跨周期一致性', '交叉拟合总变差', '全委托归一能量', '跨订单集中度', '尖锐事件对集中度', '尖锐跨订单集中度']
    phase_notes = ['比较撤单年龄余数的事件对集中程度。', '从总配对中去掉同一周期内部配对。', '用不同周期子样本交叉检验相位分布的偏离。', '分子保留事件对能量，分母使用全部有效新委托数的平方。', '扣除同一订单内部的全部消息配对。', '使用20ms与50ms核的尖锐组合比较事件对。', '在跨订单消息对上使用尖锐核组合。']
    depth_js = (ROOT / 'tools/depth_match_report_20260907.js').read_text(encoding='utf8')
    import ast
    depth_notes = ast.literal_eval(re.search(r'const notes=(\[.*?\]);', depth_js, re.S).group(1))
    output = []
    for item in manifest['features']:
        f = dict(item)
        col, source = f['original_column'], f['source']
        if source == 'old':
            m = old_by_id[col]
            key = col.split('__')[0]
            d = old_data['definitions'][key]
            f.update(definition=key, layer=m['layer'], title=d['name'], description=d['description'], formula=d['formula'], denominator=m['denominator'], domain=m.get('domain'), math='')
        elif source.startswith('cancel_'):
            s = parse_cancel_phase_column(col)
            number = int(s.family_id[3:5])
            f.update(definition=col, layer='CPH', title=phase_titles[number-1] + f' · T{s.period_ms} / {s.kernel}', description=phase_notes[number-1], formula=f'年龄带[1,10)秒；T={s.period_ms}ms；核={s.kernel}；分母={s.denominator}', denominator=s.denominator, math=phase_math[f'CPH_{number}'], family=s.family_id)
        else:
            s = depth_specs[col]
            number = int(s['name'][2:4])
            f.update(definition=s['name'], layer='DM', title=s['title'], description=depth_notes[number-1], formula=s['formula'], denominator=s['denominator'], math=depth_math[f'DM{number:02}'], parameters=s['parameters'])
        output.append(f)
    assert Counter(f['layer'] for f in output) == Counter(L1=130, L2=8, L3=56, L4=6, L5=56, CPH=48, DM=24)
    return output
