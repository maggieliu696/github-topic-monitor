# 每日08:00研究任务模板

在使用者确认的时区每天08:00执行。先读AGENTS.md、SETUP.md和Microduck数据采集/调研任务书.md，按当前项目目录定位文件。

运行sync_monitoring_tiers.py、collector.py和hf_monitor.py，读取各平台最新批次及持续待办。只让Agent阅读实质变化，不通读未变化档案。新来源先去重、归并、基础入表、分类与A/B分级；A类建立唯一详细记录，B类不要求档案。指标不等于用户人数。周一先读取周日查漏记录，再复核两平台分级。

更新总表和受影响记录；需要Excel时运行python3 scripts/export_catalog.py。按writing-skills/日报语言要求.md和日报推送_飞书群版.md写当日日报，统计必须来自当前完成批次及真实入表记录。HF队列和GitHub候选未处理完、平台失败或必要A类档案未完成时说明缺口，不生成虚假完成凭证。完成后使用send_digest.py --approve --run <GitHub最新运行目录>建立成稿凭证。本任务不发送。失败或需人判断时通知，其余保持安静。
