"""Fetch immutable report inputs over SSH and verify every manifest hash."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import subprocess
import tarfile


def selected(path):
    return (path.endswith('/factors.parquet') or
            (path.startswith('labels/intraday_labels/') and path.endswith('.parquet')) or
            (path.startswith('evaluation/') and path.endswith(('.json', '.parquet'))))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--destination', type=Path, required=True)
    parser.add_argument('--host', default='sirui-server-wangly')
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding='utf-8'))
    items = [f for f in manifest['files'] if selected(f['path'])]
    root = args.destination.resolve()
    root.mkdir(parents=True, exist_ok=True)
    pending = []
    for item in items:
        path = root / item['path']
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != item['sha256']:
            pending.append(item['path'])
    if pending:
        print(f'Fetching {len(pending)} of {len(items)} verified inputs', flush=True)
        proc = subprocess.Popen(['ssh', args.host, 'tar', '-cf', '-', '-C', manifest['run_root'], '-T', '-'],
                                stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        # The file list is smaller than the SSH input pipe; communicate separately
        # so archive output is streamed without buffering hundreds of megabytes.
        import threading
        def send():
            proc.stdin.write(('\n'.join(pending) + '\n').encode())
            proc.stdin.close()
        writer = threading.Thread(target=send)
        writer.start()
        allowed = set(pending)
        with tarfile.open(fileobj=proc.stdout, mode='r|') as archive:
            for index, member in enumerate(archive):
                name = str(PurePosixPath(member.name))
                target = (root / name).resolve()
                if name not in allowed or not member.isfile() or not target.is_relative_to(root):
                    raise ValueError(f'Unexpected archive member: {name}')
                target.parent.mkdir(parents=True, exist_ok=True)
                with archive.extractfile(member) as source, target.open('wb') as out:
                    import shutil
                    shutil.copyfileobj(source, out)
                if index % 100 == 0:
                    print(f'Received {index + 1}/{len(pending)}', flush=True)
        writer.join()
        if proc.wait() != 0:
            raise RuntimeError('SSH archive transfer failed')
    for item in items:
        path = root / item['path']
        if hashlib.sha256(path.read_bytes()).hexdigest() != item['sha256']:
            raise ValueError(f'Input hash mismatch: {path}')
    (root / 'input-manifest.json').write_text(json.dumps({
        'run_root': manifest['run_root'], 'files': items,
        'result_sha256': manifest.get('result_sha256', hashlib.sha256(args.manifest.read_bytes()).hexdigest()),
        'business_revision': manifest['business_revision'],
        'evaluation_revision': manifest['evaluation_revision'],
        **{key: manifest[key] for key in ('direction', 'execution', 'parent_run_root') if key in manifest},
    }, indent=2), encoding='utf-8')
    print(f'Verified {len(items)} inputs ({sum(f["bytes"] for f in items):,} bytes)', flush=True)


if __name__ == '__main__':
    main()
