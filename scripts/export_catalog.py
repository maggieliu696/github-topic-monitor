#!/usr/bin/env python3
"""Export the project master as UTF-8 CSV, readable by Excel; standard library only."""
import csv,json,argparse
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser();p.add_argument("--output",type=Path,default=ROOT/"outputs/projects.csv");a=p.parse_args()
 rows=json.loads((ROOT/"Microduck数据采集/selection/项目选择清单.json").read_text())["rows"]
 a.output.parent.mkdir(parents=True,exist_ok=True)
 with a.output.open("w",encoding="utf-8-sig",newline="") as f:
  w=csv.writer(f);w.writerow(["编号","项目","作者","用途","分类","A/B","GitHub Star","链接"])
  for r in rows:
   vals=[r.get("project_id"),r.get("name"),r.get("author"),r.get("plain_purpose"),r.get("direction"),r.get("monitoring_tier"),r.get("github_stars",{}).get("stars"),r.get("url")]
   w.writerow([("'"+v if isinstance(v,str) and v.startswith(("=","+","-","@")) else v) for v in vals])
 print(str(a.output))
if __name__=="__main__":main()
