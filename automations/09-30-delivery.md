# 09:30 推送任务模板

每天当地时间 09:30 检查 `Microduck数据采集/pilot/output/日报.md`。只有文件在当天生成、标题日期是当天、格式符合日报模板时，才运行 `python3 Microduck数据采集/feishu/send_digest.py`。

不得发送昨天的日报或中间稿。发送成功时保持安静；日报未就绪、校验失败或飞书拒绝时通知用户。
