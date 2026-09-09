"""Record read-only wangly process, cgroup and business progress snapshots."""
import argparse
import json
from pathlib import Path
import subprocess
import time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-root', required=True)
    parser.add_argument('--log', type=Path, required=True)
    args = parser.parse_args()
    script = '''import json,pathlib,subprocess,time
root=pathlib.Path(RUN_ROOT)
def read(name):
 p=root/name
 return json.loads(p.read_text()) if p.exists() else None
pid=int((root/'launcher.pid').read_text())
snapshot={'time':time.time(),'launcher_pid':pid,'alive':pathlib.Path(f'/proc/{pid}').exists(),'progress':read('progress.json')}
snapshot['processes']=subprocess.check_output(['ps','-u','wangly','-o','pid,ppid,pcpu,rss,comm'],text=True)
snapshot['log_tail']=(root/'formal.log').read_text(errors='replace').splitlines()[-3:] if (root/'formal.log').exists() else []
guard=read('guard_manifest.json')
snapshot['guard']=guard
snapshot['result_status']=(read('DIRECTION_RESULT.json') or {}).get('status')
print(json.dumps(snapshot))
'''.replace('RUN_ROOT', repr(args.run_root))
    args.log.parent.mkdir(parents=True, exist_ok=True)
    while True:
        result = subprocess.run(['ssh', 'sirui-server-wangly', 'python3', '-'], input=script,
                                text=True, capture_output=True, timeout=30)
        if result.returncode:
            print(json.dumps({'monitor_error': result.stderr[-1000:]}), flush=True)
        else:
            snapshot = json.loads(result.stdout)
            with args.log.open('a', encoding='utf-8') as stream:
                stream.write(json.dumps(snapshot, ensure_ascii=False) + '\n')
            print(json.dumps({k: snapshot[k] for k in ('time', 'alive', 'progress', 'result_status')}, ensure_ascii=False), flush=True)
            if snapshot['guard'] is not None and not snapshot['alive']:
                break
        time.sleep(40)


if __name__ == '__main__':
    main()
