#!/usr/bin/env python3
"""只读环境检查：不访问网络，不发送消息。"""
import json
import os
import platform
from pathlib import Path
import shutil
import sys

ROOT=Path(__file__).resolve().parents[1]

def main():
    checks={
        'project_root':str(ROOT),
        'operating_system':platform.system(),
        'python_version':platform.python_version(),
        'python_supported':sys.version_info>=(3,10),
        'project_writable':os.access(ROOT,os.W_OK),
        'collector_exists':(ROOT/'Microduck数据采集/collector.py').exists(),
        'config_exists':(ROOT/'Microduck数据采集/config.json').exists(),
        'github_token_available':bool(os.getenv('GITHUB_TOKEN') or os.getenv('GH_TOKEN')),
        'feishu_environment_available':bool(os.getenv('FEISHU_BOT_WEBHOOK') and os.getenv('FEISHU_BOT_SECRET')),
        'macos_keychain_available':bool(shutil.which('security')),
    }
    checks['ready_for_offline_tests']=all(checks[x] for x in ('python_supported','project_writable','collector_exists','config_exists'))
    print(json.dumps(checks,ensure_ascii=False,indent=2))
    return 0 if checks['ready_for_offline_tests'] else 2

if __name__=='__main__':raise SystemExit(main())
