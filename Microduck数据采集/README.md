# robotic harness 调研项目

> 项目已接通 GitHub 增量采集、A/B 分级、09:00 研究任务和 09:30 飞书推送。迁移请从根目录 [AGENTS.md](../AGENTS.md) 和 [SETUP.md](../SETUP.md) 开始。

当前只监控GitHub。先读[项目流程与检查结果](../项目流程与检查结果.md)，研究规则见[任务书](调研任务书.md)。Hugging Face和Hacker News的旧试取资料保留为历史记录，后续用其他工具监控。

已有125项候选、41份项目记录；现有 41 个 A 级、80 个 B 级和 2 个官方背景仓库。每日采集、Agent 分析、日报和飞书发送已串联启用。

## 阅读入口

- [候选清单](../Microduck项目候选清单.md)：主要浏览入口，包含Star与项目记录链接。
- [最新日报](pilot/output/日报.md)：已固定的推送样式。
- `pilot/output/项目记录/`：每个项目只有一份可读记录。
- [飞书群推送](feishu/README.md)：日报卡片、签名、去重和发送记录；待接入目标群凭证。

## 程序与数据

`collector.py` 当前入口只接受 GitHub；主配置 `config.json` 已启用。`config-demo.json` 和 `clean_demo.py` 只是历史 demo，不是每日流程。

`selection/update_stars.py` 读取GitHub Star并更新选择JSON与Markdown清单；Excel目前是辅助快照，未自动同步。凭证只通过环境变量提供，不能写进文件或聊天。

`pilot/pipeline.py` 是三个项目的离线试点，默认输出 `pilot/replay-output/`，不能覆盖正式批次的日报目录。具体限制和未接通项见流程文档。

本目录运行离线检查：

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s pilot/tests -v
python3 audit/check_consistency.py
```

这些检查不联网、不启动监控、不发送消息。三平台历史连接和数据数量见[历史连接记录](连接流程.md)。
