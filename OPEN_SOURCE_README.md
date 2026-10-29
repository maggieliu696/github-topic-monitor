# GitHub Topic Monitor

**v0.2.0-preview · GitHub + Hugging Face · Agent-operated topic monitoring**

[English](#english) · [中文](#中文)

## English

Track an open-source topic across GitHub and Hugging Face. Python retrieves public API data and compares snapshots; a local agent reviews meaningful changes, groups related sources into projects, maintains readable records and writes daily digests. Microduck is the included public-data example, not a fixed requirement.

See a [real daily digest demo (Chinese, 2026-10-29)](examples/daily-digest-2026-10-29.md). It is a dated example, not live news.

### Capabilities

- GitHub discovery and repository metadata, README, issue/comment and release monitoring.
- HF model/dataset/Space discovery, metadata, Tier-A README and discussion-list change queues. New discussion text may require the agent to open the source; this is not exhaustive monitoring of every comment or file.
- Shared project IDs across platforms; version grouping and merges are evidence-based agent decisions, not automatic semantic matching.
- Tier A detailed monitoring, Tier B lightweight tracking, Monday reclassification and Sunday gap review templates.
- One readable record per Tier-A project, a unified project list and plain-language daily digests.
- Feishu cards with a configurable title and collapsed body, readiness checks and duplicate-send prevention.
- Portable CSV export readable in Excel; no private spreadsheet runtime is bundled.

### Quick start

Python 3.10+, network access to both APIs and a local agent are required. Core Python commands use the standard library.

```sh
python3 scripts/check_environment.py
python3 scripts/install.py --mode continue
python3 -m unittest discover -s Microduck数据采集/tests -p 'test_*.py'
```

Configure your own read-only GitHub token, then run through your agent:

```sh
python3 Microduck数据采集/sync_monitoring_tiers.py
python3 Microduck数据采集/collector.py
python3 Microduck数据采集/hf_monitor.py
python3 scripts/export_catalog.py
python3 Microduck数据采集/feishu/send_digest.py --dry-run
```

**Scripts alone do not complete research.** The agent must process pending queues, verify project links, update records, write a current digest and approve the completed batch before delivery. The included catalog/digest are dated examples, not a fresh baseline or ready-to-send report. Schedules must be created in your own agent environment; unzipping does not create scheduled tasks.

See [AGENTS.md](AGENTS.md), [SETUP.md](SETUP.md), and [CHANGELOG.md](CHANGELOG.md). `--mode new-topic` creates a questionnaire only; the agent must also update actual collector queries, categories and example lists. This is a preview framework, not a hosted service or guaranteed exhaustive market monitor.

## 中文

这是一套由本地Agent配合Python运行的主题监控框架，已覆盖GitHub和Hugging Face。程序先取数、比较变化，Agent再判断哪些变化重要，整理成项目记录和日报。

先看[真实日报 Demo（2026年10月29日）](examples/daily-digest-2026-10-29.md)，了解最后收到的内容是什么样。它是历史样例，不是实时资讯。

### 别人拿来可以做什么

1. **继续研究机器鸭。** 用附带的公开Microduck清单作起点，重新建立自己的采集基线，跟踪新项目、开发问题和应用进展。
2. **改成自己的监控主题。** 例如机器人、AI开发工具等。先与Agent确定范围、分类、关键词、读者和推送节奏，再改实际采集配置。不是只改项目名称就完成迁移。
3. **搭建团队资讯日报。** 重点项目保留一篇可读记录，普通项目只维护总表；每天只把值得看的变化发送到自己的飞书群。
4. **借用其中一个环节。** 单独复用GitHub/HF采集、增量筛选、项目归并规则、日报写作要求或折叠卡片发送程序。

### 怎么运行

```text
GitHub / HF官方API → 保存数据、比较变化 → Agent判断和归并
→ 项目总表 / A类项目唯一记录 → 通俗日报 → 飞书折叠卡片
```

安装与命令见上方Quick start和[SETUP.md](SETUP.md)。核心Python程序只用标准库；CSV可用Excel打开。运行仍需要自己的网络、GitHub凭证、Agent和可选的飞书机器人。HF当前使用公开接口，不保证永久免费或额度无限。

### 需要知道的边界

- 不是安装即自动生成结论的软件：相关性、跨平台合并、A/B调整和报告撰写仍需Agent阅读证据。
- HF和GitHub信息深度不同，不保证读取所有讨论正文、代码变动或外部视频。
- 示例快照包含过去收集的公开信息，不代表使用者已完成当日检查，也不能用于推算用户人数或市场份额。
- 新主题初始化脚本只创建草稿，仍需同步真正的config.json和项目清单。定时任务需由新用户重新创建。
- 不包含原使用者的Token、Webhook、数据库、原始运行结果、发送记录或现成自动任务。遇到请求失败要报告缺口，不能当成“没有变化”。

代码为[MIT](LICENSE)，版权署名maggieliu696；Humanizer-zh保留其原有许可证。公开来源中的第三方项目内容仍归其原作者，本框架的MIT许可不替第三方资料重新授权。

仓库与问题反馈：[GitHub Topic Monitor](https://github.com/maggieliu696/github-topic-monitor)。
