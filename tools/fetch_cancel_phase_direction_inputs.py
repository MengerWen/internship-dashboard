"""Stage verified immutable directional shards, then require sealed complete inputs for reporting."""
import argparse
import json
from pathlib import Path
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-root', required=True)
    parser.add_argument('--complete', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    query = '''import hashlib,json,pathlib
r=pathlib.Path(RUN_ROOT)
identity=json.loads((r/'direction_run_identity.json').read_text())
result_path=r/'DIRECTION_RESULT.json'
result=json.loads(result_path.read_text()) if result_path.exists() else None
seal=r/'RUN_SEAL.json'
if REQUIRE_COMPLETE and (not result or result['status']!='complete' or not seal.exists()):
 raise ValueError('report inputs require a sealed complete run')
snapshots={}
for side in ('buy','sell'):
 files=[]
 for p in sorted((r/side/'panel/days').glob('????-??-??/manifest.json')):
  manifest=json.loads(p.read_text()); marker=p.parent/'COMPLETE.json'
  if not marker.exists(): continue
  if json.loads(marker.read_text())['manifest_sha256']!=hashlib.sha256(p.read_bytes()).hexdigest():
   raise ValueError('day manifest completion mismatch')
  if manifest['identity']['direction']!=side: raise ValueError('side mismatch')
  for item in manifest['components']:
   if item['path']=='factors.parquet':
    files.append({**item,'path':str((p.parent/item['path']).relative_to(r/side))})
 if REQUIRE_COMPLETE:
  if len(files)!=601: raise ValueError('direction needs 601 immutable shards')
  for p in sorted((r/side/'evaluation').iterdir()):
   if p.suffix in ('.json','.parquet'):
    files.append({'path':str(p.relative_to(r/side)),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
 snapshots[side]={'run_root':str(r/side),'parent_run_root':str(r),'direction':side,'files':files,
  'business_revision':identity['revision'],'evaluation_revision':identity['revision'],
  'execution':result,'result_sha256':hashlib.sha256(result_path.read_bytes()).hexdigest() if result else None}
print(json.dumps(snapshots))
'''.replace('RUN_ROOT', repr(args.run_root)).replace('REQUIRE_COMPLETE', repr(args.complete))
    response = subprocess.run(['ssh', 'sirui-server-wangly', 'python3', '-'], input=query,
                              text=True, encoding='utf-8', capture_output=True, check=True, timeout=60)
    snapshots = json.loads(response.stdout)
    for side, manifest in snapshots.items():
        directory = root / 'data/cancel-phase-2026-09-06/raw' / side
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / 'source-inventory.json'
        path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
        subprocess.run([sys.executable, str(root / 'tools/fetch_cancel_phase_report_inputs.py'),
                        '--manifest', str(path), '--destination', str(directory)], check=True)
    print('Sealed report inputs verified' if args.complete else 'Available immutable panels staged; full report is pending', flush=True)


if __name__ == '__main__':
    main()
