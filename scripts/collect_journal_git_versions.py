"""读取冻结引用中的文本历史版本，保持Git版本日期与实际工作日期分离。"""
import json,subprocess,sys,hashlib,argparse
from pathlib import Path
from datetime import datetime,timezone,timedelta
from collections import Counter
sys.stdout.reconfigure(encoding='utf-8')
ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--materials',type=Path,required=True)
parser.add_argument('--config',type=Path,default=ROOT/'scripts/journal_materials.json')
parser.add_argument('--output',type=Path,required=True)
parser.add_argument('--since',default='2026-06-01')
parser.add_argument('--until',default=datetime.now(timezone(timedelta(hours=8))).date().isoformat())
args=parser.parse_args()
if not args.output.resolve().is_relative_to((ROOT/'data').resolve()):parser.error('历史正文仅写本机data/')
HERE=args.output.resolve().parent;HERE.mkdir(parents=True,exist_ok=True)
read=lambda p:json.loads(p.read_text(encoding='utf-8'))
mat=read(args.materials);cfg=read(args.config)
sourcecfg={s['id']:s for s in cfg['sources']};versions={};blobs={};failures=[]
for snapshot in mat['snapshots']:
 source=sourcecfg[snapshot['source']];base=snapshot['path'];refs=snapshot['refs'];revs={snapshot['revision']}|{r[1] if r[2]=='commit' else r[3] for r in refs if r[2]=='commit' or r[4]=='commit'}
 cmd=['git','-c','core.quotepath=false','-C',base,'log',*sorted(revs),'--raw','--no-abbrev','--no-renames','--diff-merges=first-parent','-z','--format=%x1e%H%x00%aI%x00%cI']
 raw=subprocess.run(cmd,check=True,capture_output=True,encoding='utf-8').stdout
 pending={}
 for block in raw.split('\x1e')[1:]:
  commit,author,committer,*parts=block.split('\0')
  try:day=datetime.fromisoformat(author).astimezone(timezone(timedelta(hours=8))).date().isoformat()
  except ValueError:continue
  if not args.since<=day<=args.until:continue
  parts=[p.strip('\n') for p in parts if p.strip('\n')]
  for j in range(0,len(parts),2):
   fields=parts[j].split();path=parts[j+1]
   if len(fields)!=5:failures.append({'source':source['id'],'commit':commit,'kind':'raw-diff-shape'});continue
   prefix=source.get('git_prefix','')
   if prefix and not path.startswith(prefix):continue
   path=path[len(prefix):]
   if path.split('/')[0] in source.get('exclude_roots',[]):continue
   if Path(path).suffix.lower() not in {'.md','.txt','.org','.ipynb','.rst'}:continue
   oid=fields[3]
   if not oid.strip('0'):continue
   key=source['id']+':'+path+'@'+oid
   if key not in versions:versions[key]={'id':hashlib.sha256(key.encode()).hexdigest()[:24],'source':source['id'],'path':path,'git_blob':oid,'references':[]}
   versions[key]['references'].append({'commit':commit,'author_timestamp':author,'committer_timestamp':committer})
   excluded=any(p in cfg['exclude_directory_names'] or p.startswith(('.pytest_tmp','.codex-vet-')) for p in Path(path).parts)
   versions[key]['kind']='test-or-tool-reference' if excluded else 'historical-text-version'
   if not excluded:pending[oid]=key
 if pending:
  check=subprocess.run(['git','-C',base,'cat-file','--batch-check'],input='\n'.join(pending)+'\n',capture_output=True,encoding='utf-8',check=True).stdout.splitlines()
  for oid,line in zip(pending,check):
   fields=line.split()
   if len(fields)!=3 or fields[1]!='blob':failures.append({'source':source['id'],'oid':oid,'kind':'object-unavailable'});continue
   count=int(fields[2]);blobkey=source['id']+':'+oid
   if blobkey in blobs:continue
   record={'source':source['id'],'git_blob':oid,'bytes':count}
   if count<=8_000_000:
    dest=HERE/'git-text-versions'/source['id']/(oid+'.txt')
    raw=dest.read_bytes() if dest.is_file() else None
    object_hash=lambda b:(hashlib.sha1 if len(oid)==40 else hashlib.sha256)(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
    if raw is None or object_hash(raw)!=oid:
     raw=subprocess.run(['git','-C',base,'cat-file','blob',oid],capture_output=True,check=True).stdout
    if len(raw)!=count or object_hash(raw)!=oid:raise ValueError('Git对象正文与冻结对象身份不符')
    record['sha256']=hashlib.sha256(raw).hexdigest();dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(raw);record['snapshot_file']=str(dest)
   else:record['status']='oversized-text-object-metadata-only'
   blobs[blobkey]=record
out={'scope':'冻结引用中的文本版本；Git时间不是实际工作日；测试副本只保留对象身份。','since':args.since,'until':args.until,'material_snapshots_sha256':hashlib.sha256(json.dumps(mat['snapshots'],ensure_ascii=False,sort_keys=True).encode()).hexdigest(),'versions':list(versions.values()),'blobs':list(blobs.values()),'failures':failures}
args.output.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
print('text path versions',len(versions),'distinct non-test source blobs',len(blobs),'captured bytes',sum(b['bytes'] for b in blobs.values() if b.get('snapshot_file')),'failures',len(failures))
