import collections
import hashlib
import json
import pathlib
import re
import subprocess
import sys

sys.stdout.reconfigure(encoding='utf-8')
OUT = pathlib.Path(__file__).parent
ROOTS = {
    'research': pathlib.Path(r'D:\MG\_GitLinked\Quant_Research-Trading\26 Summer\❗思瑞投资\sirui-quant-research'),
    'parent': pathlib.Path(r'D:\MG\_GitLinked\Quant_Research-Trading'),
    'dashboard': pathlib.Path(r'D:\MG\！Internship\BUILD\汇报'),
}
HEADS = json.loads((OUT / 'omissions-inventory-summary.json').read_text(encoding='utf-8'))


def git(repo, *args):
    return subprocess.check_output(['git', '-c', 'core.quotepath=false', '-C', str(ROOTS[repo]), *args], encoding='utf-8', errors='replace')


def write(name, value):
    (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


def classify(repo, path, date='', subject=''):
    p = path.lower()
    s = subject.lower()
    text = p + ' ' + s
    manual = {
        '2026-07-16-formal-panel-pilot-notebooks.md': 'formal-engine',
        '2026-07-16-update-initial-factor-plan.md': 'formal-engine',
        '2026-07-16-vendor-side-cross-validation.md': 'formal-engine',
        '2026-07-17-final-assembly-regression.md': 'formal-engine',
        '2026-07-18-formal-panel-l1-daily-universe.md': 'formal-engine',
        '2026-07-22-2026q2隔日与日内因子正式计算全流程plan.md': 'formal-engine',
        '2026-08-02-2026年固定参数全区间因子评价实施计划.md': 'gates',
        '2026-08-19-open5m-cancel-lag-distribution-design.md': 'cancel-phase',
        '2026-09-07-report-tags.md': 'report-tags',
        '2026-10-12-szse-model328-factor-recompute.md': 'szse-model328',
        '2026-07-16-data-quality-window-split.md': 'formal-engine',
        '2026-07-16-historical-baselines-f08-f09-design.md': 'formal-engine',
        '2026-07-16-unified-event-prestate.md': 'formal-engine',
        '2026-07-19-fixed-production-concurrency-watchdog-design.md': 'formal-engine',
        '2026-07-19-fixed-production-concurrency-watchdog.md': 'formal-engine',
        '2026-10-17-visible-g1-ranks-missingness.md': 'sse-v2',
        'runbook_服务器执行顺序.md': 'formal-engine',
        '单日真实性能测量_服务器执行说明.md': 'formal-engine',
        '服务器内存事故修复与runbook加固计划_2026-07-17.md': 'formal-engine',
        '日内因子表现检验_服务器执行记录模板.md': 'formal-engine',
        'quote_tick_source_decision_v1.md': 'gates',
        'codex_plan_step1_factor_eval_framework.md': 'literature',
    }
    if p.split('/')[-1] in manual:
        return (manual[p.split('/')[-1]], '归入既有', '主代理逐项深读目标和关键章节后确认；执行记录模板仅是模板，不是运行结果')
    if 'lv2_snapshot_workspace/' in p and p.endswith('.md') and re.search(r'(?:fix_plan|/plan)', p):
        return ('lv2-snapshot', '归入既有', '早期LV2快照项目计划；沪市样本也属于该阶段，不移到9月沪市重建链')
    if re.search(r'2026-10-(20|21).*(rule.supported.cancel|limit.terminal.closure|recalibration344|corrected.replay.344)', p):
        return ('candidate-corrected-344-calibration', '建议新链', '10/20—21修正回放后的344定参与闭合准入材料；规则候选仍须逐结果核验')
    if re.search(r'wenjie-ide|wenjie_ide|dating|codex-windows-crash|harness-comparison', text):
        return ('excluded-unrelated', '排除', '其他工具/IDE事项，不是本次思瑞研究目标')
    if re.search(r'\.pytest_tmp/|__pycache__|\.pyc$|node_modules/|package-lock', p):
        return ('technical-maintenance', '维护', '生成物或依赖锁，不单独建研究链')
    if p.endswith(('agents.md', 'agent.md', 'claude.md')) or '/docs/agents/' in '/' + p:
        return ('technical-maintenance', '维护', '工作规约/凭据操作说明，不把规则文字当运行验收')
    if repo == 'dashboard':
        if re.search(r'journal|研究日志', text):
            return ('candidate-research-journal', '建议新链', '研究日志栏目设计、证据整理和图谱交互独立于日常发布')
        if re.search(r'model328|report328|328.*report|328.*报告', text):
            return ('report328', '归入既有', '328列报告制作与交付')
        if re.search(r'model.report|model_report|lightgbm|330.*模型|ml-results', text):
            return ('model-report', '归入既有', '模型报告及诊断口径')
        if re.search(r'report.tags|report_tags|标签|分类', text):
            return ('report-tags', '归入既有', '标签与分类')
        if re.search(r'visual|research.desk|研究编辑台|visual-b', text) or '2026-08-11' in p:
            return ('visual-b', '归入既有', '研究编辑台视觉调整')
        if date and date[:10] <= '2026-07-13':
            return ('dashboard-build', '归入既有', '看板最初建站阶段；日期上下文归类')
        return ('report-publish', '归入既有', '看板报告或站点维护；需从具体内容区分研究与报告')
    rules = [
        (r'a.clean.max|clean_core|clean_raw_nested|max-methodology', 'candidate-clean-algorithm-evidence', '可选边界细分', 'open5m已记方案，清洁算法证据指标可单列待实施目标'),
        (r'c3[._]?3|c33|cross.stock.synchron|跨股票同步', 'candidate-cross-stock-sync', '建议拆链', '跨股票同步与深度匹配的对象和停止结局不同'),
        (r'quantity.distribution|order.quantity|股数分布|quantity_counts', 'candidate-order-quantity', '可选边界细分', 'open5m已记原始委托股数分布，不是完全遗漏'),
        (r'new.factor.mechanism|new_factor_prescreen|new.factor.prescreen|actual.only.new.factor|c[1-7].*(深入研判|文献|深度研判)|新因子机制|proposal.*factor', 'candidate-mechanism-prescreen', '可选边界细分', 'open5m已记C1-C7机制预查，后续分出C3.3和C7.1'),
        (r'机械|mechanical.cancel', 'candidate-mechanical-cancel', '建议拆链', '机械撤单条件收益与估计误差研究；可保留在撤单大链但须补9/11研究归属'),
        (r'trading.window|trading_window|trading.freeze|trading.pause|trading.day.scope|quiet.window|交易.*冻结|早盘限制', 'candidate-trading-window-control', '建议新链', '通用交易窗口冻结/恢复有独立实现、系统集成和生产复验目标'),
        (r'corrected.replay.344|344.recalibration', 'candidate-corrected-344-calibration', '建议新链', '修正回放后的344列重定参，不能写成旧328结果已修正'),
        (r'sse.visible.v3', 'sse-v2', '归入既有', '沪市公开可见因子口径延续；版本升级本身不构成新链'),
        (r'storage|cleanup|retention|retirement|certificate.backfill|s3.inventory|存储|清理|归档', 'storage-cleanup', '归入既有', '存储治理；补早于10/14的实际工作日期'),
        (r'grouped|f40.remaining|f40-remaining|f40.exact.quantile|分组|结构定标|定档预检', 'grouped-calibration', '归入既有', '分组尺度/结构定标及性能验收'),
        (r'szse.model328|model328|old.factor.recompute.prep|szse.old.factor.recompute|重算准备', 'szse-model328', '归入既有', '原328列生产准备/计算验收；与修正344版本分开'),
        (r'sse|沪市|shanghai', 'sse-v2', '归入既有', '沪市观测/还原/可见性合同；v3阶段另候选'),
        (r'foundation.correctness|native.replay|replay.rule|replay.production|replay.and|chinext.snapshot|remediation|server.factor.smoke|full.recompute.admission|frozen.parameter.replay|source.ambiguity|open5m.rejection|成交价格合同', 'replay', '归入既有', '回放正确性、生产入口及重算准入'),
        (r'project.architecture|structure.refactor|io.contract.inventory|script.checkout.bootstrap|forward.arrow.bootstrap', 'technical-maintenance', '维护', '公共接口与项目结构重构；可在replay当天记技术支撑，不另建研究链'),
        (r'general.doris|doris.efficiency|general.compute.efficiency|bounded.*doris|bounded.*page|通用.*效率', 'doris-efficiency', '归入既有', '通用Doris读取效率；计划、实现、实测分开记录'),
        (r'wangly.environment|wangly.to.wenjie|code.readiness|two.server.code|server.environment|结果同步', 'wangly-env', '归入既有', '服务器环境与代码/结果同步；计划不等于同步完成'),
        (r'cancel.phase|cancel.lag|circular.phase|multimodal.*phase|撤单相位|撤单等待', 'cancel-phase', '归入既有', '撤单年龄/相位研究'),
        (r'c7[._]?1|depth.match|depth_match|深度匹配', 'depth-match', '归入既有', 'C7.1盘口深度匹配及正式因子'),
        (r'open5m.330|intraday.ml.*selection|causal.single.fit|ml.330|330.*(候选|模型)|cpu.lightgbm|f97', 'ml-330', '归入既有', '330/328候选模型选择与因果估值复算'),
        (r'old.factor|old_factor|raw.bank|raw_bank|老因子', 'old-factor-bank', '归入既有', '老因子库实现、性能与601日生产'),
        (r'51.*count|count.*结构诊断|全量原始因子lightgbm', 'ml-count', '归入既有', '早期count因子模型计划'),
        (r'intraday.ml|intraday_ml|open5m.ml|open5m_ml|/ml/|no.rf|ml.resource|ml.gpu|raw.linear|boosting.tree|random.forest|pspline|dependency.*audit|python.*运行环境|依赖闭包|gpu.structural|algebra.sparse', 'ml-exec', '归入既有', '多模型执行、资源调度及数值验收'),
        (r'fixed.history|fixed-history|复用2026年131|2026年固定参数', 'fixed-history', '归入既有', '固定参数历史评价'),
        (r'gate|tick.*recalibration|真实报价tick|xq10|硬数量门|开盘前三分钟', 'gates', '归入既有', '数量/价格门及历史评价阶段'),
        (r'open5m|kernel.calibration|kernel_calibration|selected.collection|selected_date_calibration|定标|continuous.kernel|新因子批量', 'open5m', '归入既有', '开盘五分钟因子/尺度研究；未覆盖的独立目标另候选'),
        (r'doris|服务器迁移', 'doris-migration', '归入既有', 'Doris接入与恢复续算；10月通用效率另归doris-efficiency'),
        (r'lv2.snapshot|snapshot/|快照', 'lv2-snapshot', '归入既有', '早期LV2快照工程；后期正确性审计另归replay'),
        (r'lowlat|clusterlob|factor_lab|文献|复现论文|smart.money|聪明钱|short_term_alpha', 'literature', '归入既有', '论文复现与最初因子评价框架'),
        (r'交易规则|米筐ricequant|思瑞投资介绍|开会/', 'onboarding', '归入既有', '上手资料与规则'),
        (r'算法.*关注度|algo.*footprint|sixpaper|ccp_sruns|algobench.fix|algobench_fix', 'algobench', '归入既有', '早期论文指标与关注度面板'),
        (r'formal|scorer|lifecycle|pairing|历史基线|l1参考|l1.daily|q2|step7a|最初构建因子|市场冲击|候选边', 'formal-engine', '归入既有', '正式生命周期、配对和评分工程；必要时依日期转后续阶段'),
    ]
    for pattern, chain, action, why in rules:
        if re.search(pattern, text, re.I):
            return chain, action, why
    if repo == 'parent' and p.endswith(('sirui-quant-research', 'dashboard')):
        return ('technical-maintenance', '维护', '子仓指针更新，实质改动在子仓重复记账不再新建链')
    if re.search(r'\.gitignore|\.gitattributes|readme|pyproject|requirements|environment|pytest|tests/|test_', p):
        return ('technical-maintenance', '维护', '工程维护或测试；主研究归属取同提交实质文件')
    return ('unresolved-content-review', '明确缺口', '路径/主题规则不足以确认归属，保留供内容回查')


journal = {}
for p in (ROOTS['dashboard'] / 'content/journal').glob('*.md'):
    journal[p.stem] = re.findall(r'^- id: (.+)$', p.read_text(encoding='utf-8'), re.M)

all_commits = []
all_plans = []
all_reports = []
untracked = []
for repo in ROOTS:
    sha = HEADS[repo]['head']
    commits = json.loads((OUT / f'omissions-{repo}-commits.json').read_text(encoding='utf-8'))
    tree = (OUT / f'omissions-{repo}-tree.txt').read_text(encoding='utf-8').splitlines()
    for c in commits:
        pathmap = []
        for change in c['changes']:
            for p in change[1:]:
                chain, action, why = classify(repo, p, c['date'], c['subject'])
                pathmap.append({'path': p, 'status': change[0], 'chain': chain, 'action': action, 'reason': why})
        chains = sorted({p['chain'] for p in pathmap if p['chain'] not in ['technical-maintenance', 'excluded-unrelated', 'unresolved-content-review']})
        all_commits.append({**c, 'repo': repo, 'fixed_head': sha, 'candidate_chains': chains,
                            'path_classification': pathmap, 'journal_chains_on_author_date': journal.get(c['date'][:10], []),
                            'review_level': '完整枚举+路径/主题归类；不代表逐字读完全部patch',
                            'explicit_gap': not chains})
    plans = [p for p in tree if p.endswith('.md') and ('PLAN/' in p or 'docs/plans/' in p or '/PLAN_' in p or p.split('/')[-1].startswith(('PLAN', 'FIX_PLAN')))]
    reportpaths = [p for p in tree if p.endswith('.md') and (p.startswith(('reports/', 'decisions/', 'docs/')) or '/benchmark-evidence/' in p)]
    for p in sorted(set(plans + reportpaths)):
        txt = git(repo, 'show', f'{sha}:{p}')
        # Follow rename pairs in the completely enumerated name-status stream.
        # This is bounded by the frozen date interval and does not infer the work date from a filename.
        followed_path = p
        history = []
        for c in commits:
            matches = [x for x in c['changes'] if followed_path in x[1:]]
            if matches:
                history.append(c['sha'] + '\t' + c['date'] + '\t' + c['subject'])
                for change in matches:
                    if change[0].startswith('R') and len(change) == 3 and change[2] == followed_path:
                        followed_path = change[1]
        first = history[-1].split('\t', 2) if history else []
        last = history[0].split('\t', 2) if history else []
        lines = txt.splitlines()
        title = next((l.lstrip('# ') for l in lines if l.startswith('#')), '')
        goal = next((l for l in lines if re.search(r'^\*\*(Goal|目标)', l)), '')
        declared = [dict(line=i, text=l) for i, l in enumerate(lines, 1) if re.search(r'日期|截至|状态|已完成|已停止|待实施|未.*(?:启动|执行)|20(?:26)[-年./]', l)][:30]
        chain, action, why = classify(repo, p, first[1] if first else '', title + ' ' + goal)
        record = {'repo': repo, 'fixed_head': sha, 'path': p, 'line_count': len(lines), 'title': title, 'goal': goal,
                  'first_follow_commit': first[0] if first else None, 'first_follow_author_date': first[1] if first else None,
                  'last_follow_commit': last[0] if last else None, 'last_follow_author_date': last[1] if last else None,
                  'git_history': history, 'history_scope': '固定HEAD的2026-06-01起完整name-status流递归追踪rename；非全部历史git --follow', 'declared_date_status_excerpts': declared, 'chain': chain, 'action': action,
                  'reason': why, 'review_level': '全文读取建立索引；目标/标题/状态提取归类；关键候选另深读',
                  'status_caution': '计划正文的勾选/运行命令不是独立执行验收；证据不足保留未知'}
        if p in plans:
            all_plans.append(record)
        if p in reportpaths:
            all_reports.append(record)
    status = (OUT / f'omissions-{repo}-status.txt').read_text(encoding='utf-8').splitlines()
    for row in status:
        if len(row) < 4:
            continue
        p = row[3:].strip('"')
        if p.endswith(('.md', '.txt', '.json', '.yaml', '.yml')) and re.search(r'(?i)(plan|report|decision|研究|报告|审计|benchmark-evidence)', p):
            chain, action, why = classify(repo, p)
            f = ROOTS[repo] / p
            untracked.append({'repo': repo, 'path': p, 'status': row[:2], 'chain': chain, 'action': action, 'reason': why,
                              'sha256': hashlib.sha256(f.read_bytes()).hexdigest() if f.is_file() else None,
                              'evidence_state': '工作区文件；不冒称固定HEAD已包含'})
write('omissions-commit-destinations.json', all_commits)
write('omissions-plan-destinations.json', all_plans)
write('omissions-report-destinations.json', all_reports)
write('omissions-worktree-documents.json', untracked)
summary = {'commits': len(all_commits), 'plans_including_duplicate_snapshot_copies': len(all_plans),
           'plans_by_repo': dict(collections.Counter(x['repo'] for x in all_plans)), 'reports_docs': len(all_reports),
           'worktree_documents': len(untracked), 'plan_destinations': dict(collections.Counter(x['chain'] for x in all_plans)),
           'plan_missing_git_history': [x['path'] for x in all_plans if not x['first_follow_commit']],
           'unresolved_plan_paths': [x['path'] for x in all_plans if x['chain'] == 'unresolved-content-review']}
write('omissions-manifest-summary.json', summary)
print(json.dumps(summary, ensure_ascii=False, indent=2))
