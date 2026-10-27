#!/usr/bin/env python3
"""生成 GitHub 开源候选包，排除凭证、运行状态、内部交付物和预编译二进制。"""
import argparse,hashlib,json,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
TOP={'AGENTS.md','SETUP.md','BEGINNER-TROUBLESHOOTING.md','GITHUB-RELEASE-CHECKLIST.md','LICENSE','config.example.json','credentials.example.env','automations','scripts','Microduck数据采集','Microduck项目候选清单.md'}
SKIP_PARTS={'.git','.DS_Store','__pycache__','data','data-demo','runs','archive','audit','initialization','workbook-history','star-snapshots','annotations','input','projects'}
SKIP_NAMES={'.env','credentials.json','发送记录.jsonl','最后发送.json','collector.lock','feishu_keychain_helper','执行状态.json','最新运行.json','weekly-tier-review.json'}
SKIP_SUFFIX={'.key','.pyc','.zip','.xlsx'}
def include(path):
    rel=path.relative_to(ROOT)
    if not path.is_file() or rel.parts[0] not in TOP:return False
    if any(x in SKIP_PARTS for x in rel.parts) or path.name in SKIP_NAMES or path.suffix in SKIP_SUFFIX:return False
    if 'pilot' in rel.parts and 'output' in rel.parts:
        allowed={'日报.md','项目记录'}
        output_index=rel.parts.index('output')
        if len(rel.parts)<=output_index+1 or rel.parts[output_index+1] not in allowed:return False
    return True
def scrub(path,data):
    if path.suffix.lower() not in {'.md','.json','.jsonl','.py','.sh','.txt','.toml','.swift'}:return data
    return data.decode('utf-8').replace(str(ROOT)+'/','${PROJECT_ROOT}/').encode('utf-8')
def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,default=ROOT/'交付包/github-topic-monitor-source.zip')
    args=p.parse_args();files=sorted(x for x in ROOT.rglob('*') if include(x));manifest=[]
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(args.output,'w',zipfile.ZIP_DEFLATED) as z:
        readme=(ROOT/'OPEN_SOURCE_README.md').read_bytes()
        z.writestr('github-topic-monitor/README.md',readme)
        manifest.append({'path':'README.md','sha256':hashlib.sha256(readme).hexdigest(),'bytes':len(readme)})
        for path in files:
            rel=path.relative_to(ROOT);data=scrub(path,path.read_bytes())
            manifest.append({'path':str(rel),'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)})
            z.writestr(str(Path('github-topic-monitor')/rel),data)
        z.writestr('github-topic-monitor/SOURCE-MANIFEST.json',json.dumps({'files':manifest},ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'output':str(args.output),'files':len(manifest)+1,'bytes':args.output.stat().st_size},ensure_ascii=False))
if __name__=='__main__':main()
