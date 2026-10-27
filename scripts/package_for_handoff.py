#!/usr/bin/env python3
"""生成不含凭证和本机运行状态的 Agent 接管包。"""
import argparse,hashlib,json,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SKIP_PARTS={'.git','.DS_Store','__pycache__','data','data-demo','runs','archive','star-snapshots','workbook-history'}
SKIP_NAMES={'.env','credentials.json','发送记录.jsonl','最后发送.json','collector.lock'}
TOP_LEVEL={'AGENTS.md','SETUP.md','BEGINNER-TROUBLESHOOTING.md','config.example.json','credentials.example.env','automations','scripts','Microduck数据采集','交付包','Microduck项目候选清单.md','项目流程与检查结果.md'}
def included(path):
    rel=path.relative_to(ROOT)
    return (rel.parts[0] in TOP_LEVEL and not any(x in SKIP_PARTS for x in rel.parts)
        and path.name not in SKIP_NAMES and path.suffix not in {'.key','.pyc','.zip'} and path.is_file())
def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,default=ROOT.parent/'robotic-harness-agent-handoff.zip')
    args=p.parse_args();files=sorted(x for x in ROOT.rglob('*') if included(x));manifest=[]
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(args.output,'w',zipfile.ZIP_DEFLATED) as z:
        for path in files:
            rel=path.relative_to(ROOT);data=path.read_bytes()
            if path.suffix.lower() in {'.md','.json','.jsonl','.py','.sh','.txt','.toml'}:
                text=data.decode('utf-8',errors='strict').replace(str(ROOT)+'/','${PROJECT_ROOT}/')
                data=text.encode('utf-8')
            manifest.append({'path':str(rel),'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)})
            z.writestr(str(Path(ROOT.name)/rel),data)
        z.writestr(str(Path(ROOT.name)/'HANDOFF-MANIFEST.json'),json.dumps({'files':manifest},ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'output':str(args.output),'files':len(files),'bytes':args.output.stat().st_size},ensure_ascii=False))
if __name__=='__main__':main()
