$ErrorActionPreference = 'Stop'
$projectRoot = 'D:\MG\！Internship\BUILD\汇报'
$templatePath = Join-Path $projectRoot 'design-demos\2026-08-19-ml-results\report-template.html'
$targetPath = Join-Path $projectRoot 'content\daily\2026-08-19.show.html'

$preflightScript = @'
set -euo pipefail
cd /home/wenjie/src/sirui-quant-research
git ls-remote --exit-code origin refs/heads/main >/dev/null
test -z "$(git status --porcelain=v1)"
test "$(git branch --show-current)" = main
printf 'SERVER_HEAD=%s\n' "$(git rev-parse HEAD)"
# end
'@
$preflightOutput = [string]::Join("`n", @($preflightScript | ssh sirui-server bash -s))
if ($LASTEXITCODE -ne 0) { throw "Server preflight failed; no report was written." }

$remoteScript = @'
set -euo pipefail
cd /home/wenjie/src/sirui-quant-research
source scripts/server-env.sh
python - <<'PY'
import datetime as dt
import json
import pathlib
import subprocess

import numpy as np
import pandas as pd

from algobench.ml.metrics import daily_rankic
from algobench.ml.portfolio import requested_quantile_portfolio_returns

STUDY = pathlib.Path('/home/wenjie/hdd-store/outputs/sirui/ml-no-rf-development/mlnorf_development_20260819T025951Z_9145ecae')
POST = pathlib.Path('/home/wenjie/hdd-store/outputs/sirui/ml-no-rf-all14-posthoc/mlnorf_all14_posthoc_20260819T162446Z_c7358ee8')
DEV_LABELS = pathlib.Path('/home/wenjie/hdd-store/outputs/sirui/ml-norf-performance-v2/real_dataset/dataset/labels_development')
TEST_LABELS = STUDY / 'capabilities/final_290d9ea94c6ab173/labels'

FAMILIES = [
    'raw_ridge','raw_lasso','raw_elastic_net','adaptive_lasso','sparse_group_lasso',
    'pcr_ridge','weighted_pls','regression_tree','pspline_gam','ae_ridge',
    'raw_plus_ae_ridge','hist_gbrt','lightgbm','xgboost',
]
LABELS = {
    'raw_ridge':'Raw Ridge','raw_lasso':'Raw Lasso','raw_elastic_net':'Raw Elastic Net',
    'adaptive_lasso':'Adaptive Lasso','sparse_group_lasso':'Sparse Group Lasso',
    'pcr_ridge':'PCR Ridge','weighted_pls':'Weighted PLS','regression_tree':'Regression Tree',
    'pspline_gam':'P-spline GAM','ae_ridge':'AE Ridge','raw_plus_ae_ridge':'Raw + AE Ridge',
    'hist_gbrt':'HistGBRT','lightgbm':'LightGBM','xgboost':'XGBoost',
}
COLORS = {
    'raw_ridge':'#315b75','raw_lasso':'#6f5b8c','raw_elastic_net':'#28746a',
    'adaptive_lasso':'#a04d42','sparse_group_lasso':'#8a6a2f','pcr_ridge':'#496d3d',
    'weighted_pls':'#b06e3c','regression_tree':'#7b3f61','pspline_gam':'#477d8f',
    'ae_ridge':'#3f6650','raw_plus_ae_ridge':'#8d5c4c','hist_gbrt':'#55698f',
    'lightgbm':'#9b3f3f','xgboost':'#7c6c2e',
}
FROZEN = {'raw_ridge','raw_elastic_net','regression_tree','lightgbm'}

def read_json(path):
    with open(path, encoding='utf-8') as handle:
        return json.load(handle)

def read_label_dates(root, dates):
    frames = []
    for date in dates:
        frame = pd.read_parquet(root / f'date={date}.parquet')
        if 'label_valid' not in frame.columns:
            frame['label_valid'] = True
        frame = frame[['date','code','raw_return','label_valid']]
        frames.append(frame)
    return pd.concat(frames, ignore_index=True)

def exact_floor_returns(scores, returns):
    order = np.argsort(np.asarray(scores, dtype=np.float64), kind='stable')
    values = np.asarray(returns, dtype=np.float64)
    n = len(order)
    k20 = max(1, int(np.floor(0.20 * n)))
    k10 = max(1, int(np.floor(0.10 * n)))
    return {
        'l': float(values[order[-k20:]].mean()),
        's': float(-values[order[:k20]].mean()),
        'x': float(values[order[-k10:]].mean() - values[order[:k10]].mean()),
    }

def evaluate_predictions(predictions, labels, phase):
    frame = predictions[['date','code','continuous_score','prediction_valid']].copy()
    frame['date'] = frame['date'].astype(str)
    lab = labels.copy()
    lab['date'] = lab['date'].astype(str)
    frame = frame.merge(lab, on=['date','code'], how='inner', validate='one_to_one')
    frame = frame[
        frame['prediction_valid'].astype(bool)
        & frame['label_valid'].astype(bool)
        & np.isfinite(frame['continuous_score'].to_numpy(dtype=np.float64))
        & np.isfinite(frame['raw_return'].to_numpy(dtype=np.float64))
    ]
    points = []
    for date, group in frame.groupby('date', sort=True):
        score = group['continuous_score'].to_numpy(dtype=np.float64)
        ret = group['raw_return'].to_numpy(dtype=np.float64)
        frac = requested_quantile_portfolio_returns(score, ret)
        floor = exact_floor_returns(score, ret)
        points.append([
            str(date)[:10], phase, round(float(daily_rankic(score, ret)), 12),
            round(float(frac['long_top20_return']), 12),
            round(float(frac['short_bottom20_return']), 12),
            round(float(frac['long_short_top10_bottom10_return']), 12),
            round(floor['l'], 12), round(floor['s'], 12), round(floor['x'], 12),
        ])
    return points

def annual_stats(values):
    x = np.asarray(values, dtype=np.float64)
    mean = float(x.mean() * 252.0)
    vol = float(x.std(ddof=1) * np.sqrt(252.0))
    sr = float(mean / vol) if vol > 0 else None
    return {'mean': mean, 'vol': vol, 'sr': sr}

def rows_for_series(series):
    rows = []
    for phase in ('D','T'):
        pts = [p for p in series['points'] if p[1] == phase]
        if not pts:
            continue
        for contract, indices in [('fractional',(3,4,5)),('floor',(6,7,8))]:
            evidence = 'formal' if phase == 'D' else series['test_evidence']
            rows.append({
                'series_id': series['id'], 'family': series['family'], 'label': series['label'],
                'variant': series['variant'], 'phase': phase, 'contract': contract,
                'evidence': evidence, 'n': len(pts),
                'rankic': float(np.mean([p[2] for p in pts])),
                'l': annual_stats([p[indices[0]] for p in pts]),
                's': annual_stats([p[indices[1]] for p in pts]),
                'x': annual_stats([p[indices[2]] for p in pts]),
            })
    return rows

oof_paths = {
    'raw_ridge': STUDY/'runs/raw_linear_20260819T030119Z_9145ecae/output/predictions/RAW_LINEAR_OUTER_OOF.parquet',
    'raw_lasso': STUDY/'runs/raw_linear_20260819T030119Z_9145ecae/output/predictions/RAW_LINEAR_OUTER_OOF.parquet',
    'raw_elastic_net': STUDY/'runs/raw_linear_20260819T030119Z_9145ecae/output/predictions/RAW_LINEAR_OUTER_OOF.parquet',
    'adaptive_lasso': STUDY/'runs/advanced_sparse_20260819T030120Z_9145ecae/output/predictions/ADVANCED_SPARSE_OUTER_OOF.parquet',
    'sparse_group_lasso': STUDY/'runs/advanced_sparse_20260819T030120Z_9145ecae/output/predictions/ADVANCED_SPARSE_OUTER_OOF.parquet',
    'pcr_ridge': STUDY/'runs/structural_predictive_20260819T030119Z_9145ecae/output/predictions/STRUCTURAL_PREDICTIVE_OUTER_OOF.parquet',
    'weighted_pls': STUDY/'runs/structural_predictive_20260819T030119Z_9145ecae/output/predictions/STRUCTURAL_PREDICTIVE_OUTER_OOF.parquet',
    'ae_ridge': STUDY/'runs/autoencoder_20260819T080309Z_9145ecae/output/predictions/AUTOENCODER_OUTER_OOF.parquet',
    'raw_plus_ae_ridge': STUDY/'runs/autoencoder_20260819T080309Z_9145ecae/output/predictions/AUTOENCODER_OUTER_OOF.parquet',
    'regression_tree': STUDY/'runs/nonlinear_20260819T041221Z_9145ecae/output/predictions/NONLINEAR_OUTER_OOF.parquet',
    'pspline_gam': STUDY/'runs/nonlinear_20260819T041221Z_9145ecae/output/predictions/NONLINEAR_OUTER_OOF.parquet',
    'hist_gbrt': STUDY/'runs/nonlinear_20260819T041221Z_9145ecae/output/predictions/NONLINEAR_OUTER_OOF.parquet',
    'lightgbm': STUDY/'runs/nonlinear_20260819T041221Z_9145ecae/output/predictions/NONLINEAR_OUTER_OOF.parquet',
    'xgboost': STUDY/'runs/nonlinear_20260819T041221Z_9145ecae/output/predictions/NONLINEAR_OUTER_OOF.parquet',
}

sample_oof = pd.read_parquet(oof_paths['raw_ridge'], columns=['date'])
dev_dates = sorted(sample_oof['date'].astype(str).unique().tolist())
dev_labels = read_label_dates(DEV_LABELS, dev_dates)
test_dates = sorted(p.name[5:-8] for p in TEST_LABELS.glob('date=*.parquet'))
test_labels = read_label_dates(TEST_LABELS, test_dates)

dev_points = {}
for family in FAMILIES:
    pred = pd.read_parquet(oof_paths[family], filters=[('pipeline_id','=',family)])
    dev_points[family] = evaluate_predictions(pred, dev_labels, 'D')

post_pred_dir = POST/'output/prediction_build/predictions'
test_points = {}
for family in FAMILIES:
    path = next(post_pred_dir.glob(f'{family}__*.parquet'))
    test_points[family] = evaluate_predictions(pd.read_parquet(path), test_labels, 'T')

formal_lgb_path = next((STUDY/'runs/final_prediction_20260819T145042Z_9145ecae/output/predictions').glob('lightgbm__*.parquet'))
formal_lgb_points = evaluate_predictions(pd.read_parquet(formal_lgb_path), test_labels, 'T')

series = []
for family in FAMILIES:
    if family in {'lightgbm','xgboost'}:
        continue
    is_frozen = family in FROZEN
    series.append({
        'id': family, 'family': family, 'label': LABELS[family], 'color': COLORS[family],
        'variant': 'formal frozen · posthoc bitwise equal' if is_frozen else 'all-14 posthoc supplementary',
        'dash': not is_frozen, 'test_evidence': 'formal' if is_frozen else 'audit',
        'points': dev_points[family] + test_points[family],
    })
series.extend([
    {'id':'lightgbm_cuda','family':'lightgbm','label':'LightGBM · CUDA','color':COLORS['lightgbm'],
     'variant':'formal frozen CUDA','dash':False,'test_evidence':'formal','points':dev_points['lightgbm']+formal_lgb_points},
    {'id':'lightgbm_cpu_audit','family':'lightgbm','label':'LightGBM · CPU','color':'#bd655e',
     'variant':'posthoc CPU audit','dash':True,'test_evidence':'audit','points':test_points['lightgbm']},
    {'id':'xgboost_cuda_dev','family':'xgboost','label':'XGBoost · CUDA Dev','color':COLORS['xgboost'],
     'variant':'formal Development CUDA OOF only','dash':False,'test_evidence':'formal','points':dev_points['xgboost']},
    {'id':'xgboost_cpu_audit','family':'xgboost','label':'XGBoost · CPU Test','color':'#9d8c45',
     'variant':'posthoc CPU audit · no formal CUDA Test','dash':True,'test_evidence':'audit','points':test_points['xgboost']},
])

order = {family:i for i,family in enumerate(FAMILIES)}
series.sort(key=lambda s:(order[s['family']], s['id']))
rows = []
for item in series:
    rows.extend(rows_for_series(item))
rows.sort(key=lambda r:(order[r['family']], r['series_id'], 0 if r['phase']=='D' else 1, 0 if r['contract']=='fractional' else 1))

pointer = read_json(STUDY/'FULL_LIFECYCLE_RESULT_POINTER.json')
validation = read_json(STUDY/'runs/validate_20260819T150643Z_9145ecae/output/VALIDATION_RESULT.json')
post_result = read_json(POST/'output/ALL14_FINAL_EVALUATION_RESULT.json')
report = {
    'meta': {
        'generated_at': dt.datetime.now(dt.timezone.utc).isoformat(),
        'formal_business_revision': pointer['formal_business_revision'],
        'operational_overlay_revision': pointer['operational_overlay_revision'],
        'current_server_head': subprocess.check_output(['git','rev-parse','HEAD'], text=True).strip(),
        'freeze_sha256': pointer['freeze_sha256'],
        'freeze_file_sha256': pointer['freeze_file_sha256'],
        'sealed_prediction_sha256': pointer['sealed_prediction_logical_sha256'],
        'validation_sha256': pointer['validation_result_sha256'],
        'posthoc_revision': post_result['business_revision'],
        'dev_dates': dev_dates, 'test_dates': test_dates,
        'dev_date_count': len(dev_dates), 'test_date_count': len(test_dates),
        'full_lifecycle_pointer': str(STUDY/'FULL_LIFECYCLE_RESULT_POINTER.json'),
        'validation_result': pointer['validation_result_path'],
        'formal_final_evaluation': pointer['final_evaluation_path'],
        'sealed_predictions': pointer['sealed_prediction_manifest_path'],
        'posthoc_evaluation': str(POST/'output/ALL14_FINAL_EVALUATION_RESULT.json'),
        'posthoc_validation': str(POST/'output/ALL14_VALIDATION_RESULT.json'),
        'full_lifecycle_complete': pointer['FULL_LIFECYCLE_COMPLETE'],
        'validator_passed': pointer['VALIDATOR_PASSED'],
        'bridge_executed': pointer['BRIDGE_EXECUTED'],
        'refit_scope': pointer['REFIT_SCOPE'],
        'final_evaluation_count': pointer['FINAL_EVALUATION_COUNT'],
        'required_family_count': pointer['required_family_count'],
        'formal_primary_pipeline': 'regression_tree__116bee44195c__selection=2e9aa7865ac0',
        'posthoc_family_count': post_result['family_count'],
        'posthoc_formal_evaluation_count_unchanged': post_result['formal_final_evaluation_count_unchanged'],
        'validation_status': validation['status'],
    },
    'families': FAMILIES,
    'series': series,
    'rows': rows,
}
print(json.dumps(report, ensure_ascii=False, separators=(',',':'), allow_nan=False))
PY
# end
'@

$jsonLines = @($remoteScript | ssh sirui-server bash -s)
if ($LASTEXITCODE -ne 0) { throw "Remote report-data extraction failed; no report was written." }
$jsonRaw = [string]::Join("`n", $jsonLines)
$report = $jsonRaw | ConvertFrom-Json
if ($report.meta.required_family_count -ne 14) { throw "Expected 14 required families." }
if ($report.series.Count -ne 16) { throw "Expected 16 plotted series including backend variants." }
if ($report.rows.Count -ne 58) { throw "Expected 58 phase/implementation/contract result rows." }
if (-not $report.meta.full_lifecycle_complete -or -not $report.meta.validator_passed) { throw "Formal lifecycle is not complete and valid." }

$template = [IO.File]::ReadAllText($templatePath, [Text.Encoding]::UTF8)
if (-not $template.Contains('__REPORT_DATA__')) { throw "Template data placeholder is missing." }
$html = $template.Replace('__REPORT_DATA__', $jsonRaw)
[IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($targetPath)) | Out-Null
[IO.File]::WriteAllText($targetPath, $html, [Text.UTF8Encoding]::new($false))
$sha = (Get-FileHash -LiteralPath $targetPath -Algorithm SHA256).Hash.ToLowerInvariant()
$size = (Get-Item -LiteralPath $targetPath).Length
Write-Output $preflightOutput
Write-Output "TARGET=$targetPath"
Write-Output "SIZE=$size"
Write-Output "SHA256=$sha"
Write-Output "SERIES=$($report.series.Count)"
Write-Output "ROWS=$($report.rows.Count)"
Write-Output "DEV_DATES=$($report.meta.dev_date_count)"
Write-Output "TEST_DATES=$($report.meta.test_date_count)"
