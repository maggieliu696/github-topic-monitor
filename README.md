# GitHub Topic Monitor

[English](#english) | [中文](#中文)

## English

GitHub Topic Monitor is an agent-operated framework for discovering and continuously tracking GitHub projects around a chosen topic. A Python collector retrieves and compares public data first; an agent then reads only meaningful changes and turns them into human-readable project records and daily digests.

### What it does

- Discovers new repositories through the official GitHub API.
- Tracks repository metadata, README files, issues, comments, releases, and stars.
- Uses content fingerprints and incremental comparison to skip unchanged material.
- Splits projects into deep-monitoring Tier A and lightweight Tier B to control model usage.
- Maintains one readable dossier for each project.
- Produces concise daily reports from evidence-backed changes.
- Sends signed, deduplicated message cards through a Feishu custom bot.
- Provides `AGENTS.md`, setup checks, automation templates, and beginner-friendly troubleshooting so another local agent can take over the project.

The repository includes the Microduck open-source robotics ecosystem as a working example. The collector itself does not infer sentiment or market conclusions; an agent forms those judgments after reading the linked public evidence.

### Quick start

Python 3.10 or newer is required. The collector uses only the Python standard library.

```sh
python3 scripts/check_environment.py
python3 scripts/install.py --mode continue
python3 -m unittest discover -s Microduck数据采集/tests -p "test_*.py"
```

Configure a read-only `GITHUB_TOKEN`, then run:

```sh
python3 Microduck数据采集/sync_monitoring_tiers.py
python3 Microduck数据采集/collector.py
```

Preview a Feishu card without sending it:

```sh
python3 Microduck数据采集/feishu/send_digest.py --dry-run
```

See [AGENTS.md](AGENTS.md) for agent takeover, [SETUP.md](SETUP.md) for installation, and [BEGINNER-TROUBLESHOOTING.md](BEGINNER-TROUBLESHOOTING.md) for common problems.

### Current scope

- The production collector currently supports GitHub only.
- Report analysis requires a local agent capable of reading files and running scheduled work.
- Feishu delivery requires credentials for the user's own custom bot.
- Local schedules require the computer, network, and agent runtime to be available.

Licensed under the [MIT License](LICENSE). Copyright (c) 2026 `maggieliu696`.

---

## 中文

GitHub Topic Monitor 是一个由 Agent 接管的 GitHub 主题监控框架。用户可以指定一个主题，持续发现相关项目、追踪已有项目变化，并生成给人阅读的项目档案和每日摘要。它先用 Python 通过官方 API 采集和比较变化，再让 Agent 只阅读需要理解的增量。

仓库内附带 Microduck 开源机器鸭生态作为完整示例。它展示了如何监控一个主题、管理 A/B 项目、跟踪变化并推送日报。

## 能做什么

- 使用 GitHub 官方 API 搜索新项目并监控已有项目；
- 保存原始响应、来源链接、采集时间和前后变化；
- 比较仓库更新、README、Issue、评论、Release 和 Star；
- 用内容指纹跳过未变化内容，减少 Agent 阅读量；
- 用 A/B 分级平衡覆盖范围与模型成本；
- 为每个项目保留一份可读档案；
- 将重要变化组织成日报；
- 通过飞书自定义机器人发送消息卡片；
- 通过 `AGENTS.md` 让另一个 Agent 完成环境检查、配置、测试和定时任务创建。

## 工作流程

```text
GitHub API
   ↓
Python 采集、去重和差异比较
   ↓
A 级深检查 / B 级轻量检查
   ↓
Agent 阅读实质变化
   ↓
项目档案 → 日报 → 飞书机器人
```

Python 程序不会自动推断用户态度或市场结论。这些工作由 Agent 在阅读原文后完成。

## 快速开始

需要 Python 3.10 或更高版本。采集器只使用 Python 标准库。

```sh
python3 scripts/check_environment.py
python3 scripts/install.py --mode continue
python3 -m unittest discover -s Microduck数据采集/tests -p "test_*.py"
```

配置 GitHub 只读 Token 后：

```sh
python3 Microduck数据采集/sync_monitoring_tiers.py
python3 Microduck数据采集/collector.py
```

预览飞书卡片，不发送消息：

```sh
python3 Microduck数据采集/feishu/send_digest.py --dry-run
```

完整的 Agent 接管顺序见 [AGENTS.md](AGENTS.md)，安装与凭证配置见 [SETUP.md](SETUP.md)，小白故障处理见 [BEGINNER-TROUBLESHOOTING.md](BEGINNER-TROUBLESHOOTING.md)。

## 凭证

项目可读取以下环境变量：

- `GITHUB_TOKEN` 或 `GH_TOKEN`；
- `FEISHU_BOT_WEBHOOK`；
- `FEISHU_BOT_SECRET`。

macOS 用户也可使用钥匙串辅助脚本。不要将真实凭证写入仓库。

## 目录

```text
AGENTS.md                         Agent 接管规则
SETUP.md                          安装与验收
BEGINNER-TROUBLESHOOTING.md       小白故障处理
automations/                      定时任务模板
scripts/                          环境检查与初始化
Microduck数据采集/collector.py      GitHub 采集器
Microduck数据采集/config.json       Microduck 示例配置
Microduck数据采集/tests/            离线测试
Microduck数据采集/writing-skills/   日报写作模板
```

## 当前边界

- 当前正式采集器只监控 GitHub；
- 日报分析需要一个能执行本地任务的 Agent；
- 飞书发送需要使用者自己的机器人凭证；
- 本地定时任务需要电脑在运行时开机、联网且 Agent 可用；
- Microduck 项目档案是公开 GitHub 信息的研究示例，不代表项目作者对本仓库的认可。

## 安全

发现凭证泄漏或安全问题时，请不要在公开 Issue 中张贴密钥或 Webhook。先撤销已泄漏凭证，再通过仓库维护者公开的私密联系方式报告。

## 许可证

项目代码使用 [MIT License](LICENSE)。`writing-skills/humanizer-zh` 保留其自带许可证。
