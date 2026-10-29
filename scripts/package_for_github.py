#!/usr/bin/env python3
"""Build a portable public source archive from an explicit allowlist; never ship live state."""
import argparse, hashlib, json, os, re, zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
VERSION="0.2.0-preview"
TOP={"AGENTS.md","SETUP.md","BEGINNER-TROUBLESHOOTING.md","GITHUB-RELEASE-CHECKLIST.md","LICENSE","config.example.json","credentials.example.env","CHANGELOG.md",".gitignore","OPEN_SOURCE_README.md","PUBLIC_TASKBOOK.md"}
CORE={"collector.py","hf_monitor.py","project_review.py","sync_monitoring_tiers.py","weekly_tier_review.py","clean_demo.py","config.json","monitoring-tiers.json","configure_github_keychain.sh","configure_github_keychain_gui.sh","A-B分级监控规则.md","增量筛选说明.md"}
PRUNE={".git","__pycache__","node_modules","state","data","runs","huggingface-runs","backups","archive","audit","initialization","workbook-history"}
def include(path):
 rel=path.relative_to(ROOT); parts=rel.parts
 if path.is_symlink() or not path.is_file() or any(x in PRUNE for x in parts):return False
 if len(parts)==1:return path.name in TOP
 if parts[0]=="scripts":return path.name in {"package_for_github.py","check_environment.py","install.py","export_catalog.py"}
 if parts[0] in {"automations", "examples"}:return path.suffix==".md"
 if parts[0]!="Microduck数据采集":return False
 if len(parts)==2:return path.name in CORE
 if parts[1]=="feishu":return len(parts)==3 and path.suffix in {".py",".sh",".swift",".md",".json"} and path.name!="credentials.json"
 if parts[1]=="tests":return path.suffix==".py"
 if parts[1]=="writing-skills":return path.suffix in {".md",".json",".txt"} or path.name=="LICENSE"
 if parts[1]=="selection":return len(parts)==3 and path.name in {"项目选择清单.json","平台来源索引.json"}
 if parts[1:3]==("pilot","output"):return path.suffix==".md" and (path.name=="日报.md" or "项目记录" in parts)
 return False

def scrub(path,data):
 if path.suffix.lower() in {".md",".json",".jsonl",".py",".sh",".txt",".toml",".swift"}:
  text=data.decode("utf-8").replace(str(ROOT)+"/", "").replace(str(ROOT),".")
  # Personal runtime paths are documentation only; no live platform paths are exported.
  if path.suffix.lower() in {".md", ".json", ".txt"}: text=re.sub(r"/Users/[^\s\"'<>）)]+", "<LOCAL_PATH>", text)
  return text.encode("utf-8")
 return data

def main():
 parser=argparse.ArgumentParser();parser.add_argument("--output",type=Path,default=ROOT/"交付包"/f"github-topic-monitor-v{VERSION}.zip");args=parser.parse_args()
 entries={"README.md":(ROOT/"OPEN_SOURCE_README.md").read_bytes()}
 for base,dirs,files in os.walk(ROOT):
  dirs[:]=[d for d in dirs if d not in PRUNE and not (Path(base)/d).is_symlink()]
  for name in files:
   p=Path(base)/name
   if include(p):entries[str(p.relative_to(ROOT))]=scrub(p,p.read_bytes())
 # Runtime integration instructions are authored separately from the local taskbook.
 entries["Microduck数据采集/调研任务书.md"]=(ROOT/"PUBLIC_TASKBOOK.md").read_bytes()
 entries["Microduck数据采集/README.md"]=b"See ../README.md and ../SETUP.md.\n"
 entries[".gitignore"]=("__pycache__/\n*.pyc\n.env\nlocal-project-config.json\nMicroduck数据采集/data/\nMicroduck数据采集/runs/\nMicroduck数据采集/huggingface-runs/\nMicroduck数据采集/feishu/state/\noutputs/\n").encode()
 config=json.loads(entries["Microduck数据采集/config.json"])
 config["research"]["active_platforms"]=["github","huggingface"]
 for k in ("tracked_project_count","candidate_project_count"):config["research"].pop(k,None)
 config["execution"]["status"]="github_hf_agent_workflow"
 entries["Microduck数据采集/config.json"]=(json.dumps(config,ensure_ascii=False,indent=2)+"\n").encode()
 patterns=[r"https://open\.feishu\.cn/open-apis/bot/v2/hook/(?!example|YOUR|<)[0-9a-fA-F-]{30,}",r"github_pat_[A-Za-z0-9_]{20,}",r"gh[pousr]_[A-Za-z0-9]{20,}",r"-----BEGIN (?:RSA |OPENSSH )?PRIVATE KEY-----",r"/Users/"+"ll/",r"01a[0-9a-f]{5}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"]
 for name,data in entries.items():
  text=data.decode("utf-8",errors="ignore")
  if any(re.search(p,text) for p in patterns):raise SystemExit("Sensitive/local data found in "+name)
 manifest={"version":VERSION,"scope":"portable-source-with-public-Microduck-example","live_state_included":False,"files":[{"path":n,"sha256":hashlib.sha256(d).hexdigest(),"bytes":len(d)} for n,d in sorted(entries.items())]}
 entries["SOURCE-MANIFEST.json"]=(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n").encode()
 args.output.parent.mkdir(parents=True,exist_ok=True)
 with zipfile.ZipFile(args.output,"w",zipfile.ZIP_DEFLATED) as z:
  for name,data in sorted(entries.items()):z.writestr("github-topic-monitor/"+name,data)
 checksum=hashlib.sha256(args.output.read_bytes()).hexdigest()
 args.output.with_suffix(".sha256").write_text(checksum+"  "+args.output.name+"\n")
 print(json.dumps({"version":VERSION,"output":str(args.output),"files":len(entries),"bytes":args.output.stat().st_size,"sha256":checksum},ensure_ascii=False))
if __name__=="__main__":main()
