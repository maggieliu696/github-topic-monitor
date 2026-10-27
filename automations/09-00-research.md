# 09:00 研究任务模板

每天当地时间 09:00 运行本项目的 GitHub 增量监控。从当前 chat 所在项目目录定位文件，不使用原使用者的绝对路径。

1. 运行 `python3 Microduck数据采集/sync_monitoring_tiers.py`和 `python3 Microduck数据采集/collector.py`。
2. A 级变化可阅读 README、Issue、评论和 Release；B 级只在升级队列触发时深读。
3. 将确认相关的新项目去重、编码、归类并分到 A 或 B。
4. 每周一额外运行 `python3 Microduck数据采集/weekly_tier_review.py`并复核分级。
5. 按已确认的中文模板生成当日日报，只写重要变化。
6. 本任务不发送群消息。正常完成时保持安静；失败或需要人工判断时通知用户。
