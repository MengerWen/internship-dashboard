"""在11.16页面保留独立的G2开发期对照。"""
from __future__ import annotations

import argparse
import base64
import gzip
import hashlib
import json
from math import isfinite
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
ASSET = ROOT / 'content/assets/csi2000-g2-20261116/comparison.json'
BEGIN, END = '<!-- G2-COMPARISON-BEGIN -->', '<!-- G2-COMPARISON-END -->'
REPORT_URL = 'https://github.com/MengerWen/sirui-quant-research/blob/190cf4a3/reports/2026-11/2026-11-16-baseline-g2-comparison.md'


def pack(source):
    from build_20261116_base_position import CONFIGURATIONS
    dates = source['dates']
    if (len(dates) != 308 or dates != sorted(set(dates))
            or (dates[0], dates[-1]) != ('2024-07-01', '2025-09-30')
            or source['identity']['fees'] != dict(buy=.9e-4, sell=5.9e-4)):
        raise ValueError('G2 requires the signed 308-day fee contract')
    expected = {key + suffix for key in CONFIGURATIONS for suffix in ('', '-t20', '-t30')}
    if set(source['series']) != {'baseline', 'G2'}:
        raise ValueError('G2 comparison requires both models')
    result = dict(dates=dates, initial=source['initial'], base=source['base'], series={}, identity=source['identity'])
    for weight in ('index', 'equal'):
        if (len(result['base'][weight]) != 308 or len(result['initial'][weight]) != 2
                or any(not isfinite(x) or x <= 0 for x in result['initial'][weight])):
            raise ValueError('Invalid base or market capital')
    for name, schemes in source['series'].items():
        if set(schemes) != expected:
            raise ValueError('Incomplete G2 configuration coverage')
        result['series'][name] = {}
        for key, rows in schemes.items():
            if len(rows) != 308 or any(len(row) != 6 or any(not isfinite(x) for x in row[:2]) for row in rows):
                raise ValueError('Invalid G2 path')
            result['series'][name][key] = [[round(v, 12) for v in row[:2]] for row in rows]
    return result


def append_section(page, asset=ASSET):
    if not asset.exists():
        return page
    data = json.loads(asset.read_bytes())
    encoded = base64.b64encode(gzip.compress(json.dumps(data, separators=(',', ':')).encode(), mtime=0)).decode()
    script = Path(__file__).with_name('csi2000_g2_comparison.js').read_text(encoding='utf-8')
    section = f'''{BEGIN}
<section id="g2-comparison" aria-labelledby="g2-heading">
  <h2 id="g2-heading">加入 G2 后，底仓增强是否改善</h2>
  <p class="hint">开发 OOF 复核：2024-07-01—2025-09-30，共308日。G2仅加入深市，沪市继续使用原模型。这里没有G2测试期结果。</p>
  <p class="chart-foot">沿用上方的底仓、排序、组合、选股比例及做T比例；本区固定共同开发期。买入0.9 bp、卖出5.9 bp，F1–F9成交与顺延规则一致。</p>
  <figure class="chart-plate">
    <div class="chart-tools"><h3 id="g2-unit">累计底仓增强（%）</h3>
      <form id="g2-filters" class="filters" aria-label="G2比较视图">
        <label>市场 <select name="market"><option value="sz">深市</option><option value="sh">沪市</option><option value="all">沪深合计</option></select></label>
        <label>周期 <select name="horizon"><option value="morning">11:30</option><option value="close" selected>收盘</option></select></label>
        <label>收益 <select name="view"><option value="enhancement">底仓增强</option><option value="wealth">研究收益</option></select></label>
      </form>
    </div>
    <div class="legend"><span><svg width="24" height="10" aria-hidden="true"><line x1="0" x2="24" y1="5" y2="5" stroke="var(--blue)" stroke-width="2" stroke-dasharray="6 3"/></svg>baseline</span><span><svg width="24" height="10" aria-hidden="true"><line x1="0" x2="24" y1="5" y2="5" stroke="var(--focus)" stroke-width="2"/></svg>沪市原模型＋深市 G2</span><span id="g2-base-legend" hidden>细点线：共同底仓</span></div>
    <div class="plot"><svg id="g2-main" class="chart" role="img" aria-label="baseline与G2累计收益对照"></svg></div>
    <figcaption id="g2-end" class="chart-foot"></figcaption>
    <div class="chart-tools"><h3>G2 − baseline（百分点）</h3></div>
    <div class="plot"><svg id="g2-delta" class="chart" role="img" aria-label="G2相对baseline的累计增量"></svg></div>
    <div class="chart-foot"><label for="g2-date">查看日期</label> <input id="g2-date" type="range" min="0" max="307" value="307" style="width:min(100%,480px);vertical-align:middle"><p id="g2-readout" aria-live="polite">正在读取比较数据</p></div>
  </figure>
  <p class="chart-foot">累计增强为做T增量金额除以所选市场初始底仓；沪深合计先加金额再归一化。合并排序下，深市分数变化也可能改变沪市入选名单。这是已参与研发样本的同口径复核，不代表独立盲测通过。<a href="{REPORT_URL}" target="_blank" rel="noopener">比较报告与统计口径</a></p>
</section>
<script id="g2-data" type="application/octet-stream">{encoded}</script>
<script type="text/javascript">{script}</script>
{END}'''
    page = re.sub(re.escape(BEGIN) + r'.*?' + re.escape(END) + r'\s*', '', page, flags=re.S)
    anchor = '<section id="contract"'
    if page.count(anchor) != 1:
        raise ValueError('The original contract section must occur once')
    return page.replace(anchor, section + '\n' + anchor, 1)


def append_note(note, asset=ASSET):
    if not asset.exists():
        return note
    begin, end = '<!-- G2-NOTE-BEGIN -->', '<!-- G2-NOTE-END -->'
    text = f'''{begin}
**G2 因子增量对照** 单独比较2024-07-01至2025-09-30的308个共同开发日，深市加入既有G2预测，沪市沿用原模型。支持全部192配置及沪市、深市、合计切换，同时显示新旧累计增强与差额。固定10%做T、5%选股的16项主配置均有小幅改善，但均未通过本轮多重比较校正；这不代表独立测试期验证。新因子仅整理候选，尚未计算。[G2比较报告]({REPORT_URL})
{end}

'''
    note = re.sub(re.escape(begin) + r'.*?' + re.escape(end) + r'\s*', '', note, flags=re.S)
    anchor = '[模型线复盘'
    if note.count(anchor) != 1:
        raise ValueError('The model review link must occur once')
    return note.replace(anchor, text + anchor, 1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--sha256', required=True)
    args = parser.parse_args()
    from frozen_baseline import MANIFEST
    if MANIFEST.exists():
        parser.error('旧 G2 结果已保留；更新版本比较页请使用 build_factor_strategy_comparison.py')
    raw = args.input.read_bytes()
    if hashlib.sha256(raw).hexdigest() != args.sha256:
        raise ValueError('G2 source hash differs')
    data = pack(json.loads(raw))
    data['source_sha256'] = args.sha256
    ASSET.parent.mkdir(parents=True, exist_ok=True)
    ASSET.write_text(json.dumps(data, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    page = ROOT / 'content/daily/2026-11-16.show.html'
    page.write_text(append_section(page.read_text(encoding='utf-8')), encoding='utf-8', newline='\n')
    note = ROOT / 'content/daily/2026-11-16.md'
    note.write_text(append_note(note.read_text(encoding='utf-8')), encoding='utf-8', newline='\n')
    print(json.dumps(dict(days=len(data['dates']), configurations=len(data['series']['G2']), asset_bytes=ASSET.stat().st_size)))


if __name__ == '__main__':
    main()
