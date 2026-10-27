#!/usr/bin/env python3
"""初始化本地可写目录，不复制凭证、不创建外部自动任务。"""
import argparse
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'Microduck数据采集'

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--mode',choices=('continue','new-topic'),required=True)
    args=parser.parse_args()
    for path in (DATA/'data',DATA/'runs',DATA/'feishu/state',DATA/'pilot/output/项目记录'):
        path.mkdir(parents=True,exist_ok=True)
    if args.mode=='new-topic':
        target=ROOT/'local-project-config.json'
        if not target.exists():target.write_text((ROOT/'config.example.json').read_text(encoding='utf-8'),encoding='utf-8')
    result={'status':'initialized','mode':args.mode,'project_root':str(ROOT),
        'next_steps':['配置本机凭证','运行离线测试','运行手动采集','预览日报','重新创建自动任务']}
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
