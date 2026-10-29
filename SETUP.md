# 安装与首次接管

需要Python 3.10+、能联网读取GitHub/HF的环境，以及可以读写本地文件和执行命令的Agent。核心程序仅使用标准库。不要先开启真实发送。

1. 解压后让Agent阅读AGENTS.md、调研任务书和BEGINNER-TROUBLESHOOTING.md。
2. 执行 `python3 scripts/check_environment.py` 和 `python3 scripts/install.py --mode continue`。安装脚本只创建目录，不建立定时任务。
3. 配置自己的GITHUB_TOKEN或GH_TOKEN。macOS可用Microduck数据采集/configure_github_keychain.sh；不要提供写入权限作为日常采集凭证。HF当前读取公开接口。
4. 运行 `python3 -m unittest discover -s Microduck数据采集/tests -p 'test_*.py'`。
5. 依次运行sync_monitoring_tiers.py、collector.py、hf_monitor.py，由Agent处理持续候选和HF来源队列，建立自己的比较起点。不能将旧示例当作本轮新增。
6. Agent基础识别新项目、归并和分级。A类保存唯一详细记录；B类只更新总表。可运行 `python3 scripts/export_catalog.py` 导出Excel可读的CSV。
7. 按写作要求生成当天日报。全部检查完成后运行 `python3 Microduck数据采集/feishu/send_digest.py --approve --run <本轮GitHub运行目录>`，再用--dry-run检查卡片。
8. 需要飞书推送时配置自己的机器人。默认使用FEISHU_BOT_WEBHOOK、FEISHU_BOT_SECRET或macOS钥匙串。若自己的机器人确实无需签名，可在feishu/state/delivery.json保存 {"destination":"自己的群","webhook":"自己的地址","auth_mode":"none"}，权限必须600；文件不得入库。开启签名的机器人请使用默认签名凭证方式，不沿用别人的密钥。
9. 用户授权后手动发送，再根据automations/模板在自己的Agent里建立8:00研究、9:30发送、周日16:00查漏。确认自己的时区和目录，不沿用原任务ID。

## 改主题

`python3 scripts/install.py --mode new-topic`只会生成local-project-config.json任务书草稿，不会自动切换采集主题。Agent必须与用户确认范围和分类，再同步Microduck数据采集/config.json中的GitHub搜索式、种子仓库和HF搜索词，重建该主题的selection项目清单、来源索引及分级名单。请在新的目录中操作，避免把不同主题混到同一数据库。

## 不随包移交的内容

数据库、原始API结果、所有运行目录、发送状态、真实凭证、私有Excel依赖及现成自动任务均不在包内。初次扫描可能产生较多首次观察事件，先建立基线，再生成真正的日常增量报告。
