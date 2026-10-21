"""生成可公开的逐日来源登记；正文和本机绝对路径不进入公开文件。"""
from __future__ import annotations

import argparse
from collections import defaultdict
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def document_stage(path, title):
    if '/PLAN/' in '/' + path or '/prompt/' in path or path.startswith('PLAN/'):
        return '构思（计划文本）'
    if re.search('构思|提案|可行性|研判|研究|文献|证据核查', title):
        return '构思（研究材料）'
    if re.search('验收|核验|验证|审计|审查|复核|诊断', title):
        return '验收（检查记录）'
    if re.search('启动|运行|续跑|续算|暂停|恢复|完成|交付', title):
        return '运行（过程记录）'
    if re.search('实现|实施|修复|提速|优化|重构|整改', title):
        return '实施（工程记录）'
    return '资料整理'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=ROOT / 'data/journal-rebuild-2026-10-21')
    parser.add_argument('--output', type=Path, default=ROOT / 'docs/journal-review/rebuild-2026-10-21')
    args = parser.parse_args()
    read = lambda p: json.loads(p.read_text(encoding='utf-8'))
    ledger = read(args.input / 'dispositions.json')
    documents = read(args.input / 'document-review.json')
    sessions = read(args.input / 'session-review.json')
    titles = read(args.input / 'session-titles.json')
    decisions = read(args.output / 'review-decisions.json')
    files = {x['id']: x for x in ledger['files']}
    names = {x['id']: x['label'] for x in read(ROOT / 'content/chains.json')['chains']}
    names.update({'behavior-design': 'B/C/D/V算法行为构思与可行性研究', 'fund-research': '量化私募与NEXT产品研究',
        'model-methods': '模型协议、标签、损失函数与评价口径', 'strategy-research': '股票池、资金分配与成交假设',
        'mechanism-precheck': 'C系列候选机制的分布预检', 'research-code': '研究仓代码结构审查与整改'})
    days = defaultdict(lambda: {'sessions': [], 'documents': []})
    sources = []
    for doc in documents:
        route = decisions['documents'][doc['id']]
        if route['disposition'] == 'excluded':
            continue
        file = files[doc['id']]
        writes = sorted({e['date'] for e in file['write_evidence']})
        source = {k: doc[k] for k in ['id', 'source', 'path', 'title', 'sha256', 'git_state']}
        source.update(chains=route['chains'], disposition=route['disposition'],
            stage=document_stage(doc['path'], doc['title']), write_dates=writes,
            write_evidence=file['write_evidence'], filename_dates=doc['filename_dates'],
            git_dates=sorted({h['date'] for h in doc['git_history']}),
            date_status='raw-write-receipt' if writes else 'no-verified-write-time')
        sources.append(source)
        for day in writes:
            days[day]['documents'].append(source['id'])
    for session in sessions:
        key = session['platform'] + ':' + session['session_id']
        decision = decisions['sessions'][key]
        if decision['disposition'] != 'research-related':
            continue
        title = titles.get(session['session_id']) or '、'.join(names[c] for c in decision['chains'])
        if re.search(r'密码|password|token|私钥|https?://', title, re.I):
            title = '、'.join(names[c] for c in decision['chains'])
        for day in sorted({m['date'] for m in session['users']}):
            msgs = [m for m in session['users'] if m['date'] == day]
            days[day]['sessions'].append({'id': key, 'title': title, 'chains': decision['chains'],
                'user_lines': [{'line': m['line'], 'sha256': m['line_sha256'], 'time': m['timestamp']} for m in msgs]})
    register = {'schema_version': 1, 'scope': '固定快照内的逐材料、逐会话登记；不代表重新运行研究计算',
        'documents': sources, 'days': dict(sorted(days.items())),
        'counts': {k: len(ledger[k]) for k in ['files', 'sessions', 'messages', 'commits', 'actions']},
        'file_dispositions': dict(__import__('collections').Counter(x['disposition'] for x in ledger['files']))}
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / 'source-register.json').write_text(json.dumps(register, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    out = args.output / 'days'
    out.mkdir(exist_ok=True)
    by_doc = {x['id']: x for x in sources}
    for day, data in sorted(days.items()):
        text = [f'# {day} 原始来源登记', '',
            '日期来自消息自身时间和文件写入回执，均换算为北京时间。材料标题日期、Git入库日期分别保留在 source-register.json。', '',
            '会话表证明当时有这些要求、讨论或决定。阶段栏说明材料用途；“运行记录”“验收记录”不表示已经运行成功或验收通过，具体结论须读对应正文与收据。', '',
            '## 会话', '', '| 会话与内容定位 | 研究去向 | 当日原始用户行号 |', '|---|---|---|']
        for item in data['sessions']:
            text.append(f"| {item['title'].replace('|', '／')} · `{item['id']}` | {'、'.join(names[c] for c in item['chains'])} | {', '.join(str(x['line']) for x in item['user_lines'])} |")
        text += ['', '## 已匹配写入回执的材料', '', '| 材料 | 阶段 | 去向 | 内容SHA-256 |', '|---|---|---|---|']
        for fid in data['documents']:
            item = by_doc[fid]
            text.append(f"| {item['title'].replace('|', '／')} · `{item['source']}:{item['path']}` | {item['stage']} | {'、'.join(names[c] for c in item['chains'])} | `{item['sha256']}` |")
        if not data['documents']:
            text.append('| 本日没有可单独匹配的写入回执；不据此认定没有工作 | — | 见上表原始会话 | — |')
        text += ['', '原始全文和绝对路径保留在本机 data/journal-rebuild-2026-10-21/；公开清单仅保留必要定位和哈希。', '']
        (out / (day + '.md')).write_text('\n'.join(text), encoding='utf-8')
    pending = [x for x in sources if not x['write_dates']]
    (args.output / 'undated-materials.md').write_text('# 缺少独立写入时间的材料\n\n以下材料均已登记研究去向。文件名、正文自述日期和Git入库日期不能单独证明实际写入日；不为此补造日点。相同目标若有原始会话，按会话自身日期入日志。\n\n' +
        '\n'.join(f"- `{x['source']}:{x['path']}` → {', '.join(x['chains'])}；材料ID `{x['id']}`。" for x in pending) + '\n', encoding='utf-8')
    print('逐日来源登记', len(days), '材料', len(sources), '缺独立写入时间', len(pending))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
