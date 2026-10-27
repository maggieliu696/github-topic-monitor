# 首次接管与迁移

> 如果用户不熟悉 Python、Token、Webhook 或定时任务，接管 Agent 应同时阅读 [小白用户故障处理手册](BEGINNER-TROUBLESHOOTING.md)。

## 一、最低环境

- Python 3.10 或更高版本；
- 可访问 GitHub 官方 API；
- 一个只读 GitHub Token；
- 如需推送，准备新使用者自己的飞书自定义机器人。

采集器只使用 Python 标准库。已支持 macOS、Linux 和 Windows 文件锁。macOS 可使用钥匙串；Linux 和 Windows 建议使用环境变量。

## 二、让 Agent 执行初始化

把整个目录交给 Agent，并说：

> 请按照 AGENTS.md 接管这个项目。先检查环境，未经我确认不要真实发送消息。

Agent 应先运行：

```sh
python3 scripts/check_environment.py
python3 scripts/install.py --mode continue
```

`continue` 表示继续当前 Microduck 主题。改成新主题时使用 `--mode new-topic`，Agent 会依据 `config.example.json` 收集新配置。

## 三、配置凭证

### macOS

```sh
bash Microduck数据采集/configure_github_keychain.sh
bash Microduck数据采集/feishu/configure_macos_keychain.sh
```

### Linux 或 Windows

在运行环境中设置 `GITHUB_TOKEN`、`FEISHU_BOT_WEBHOOK` 和 `FEISHU_BOT_SECRET`。名称可参考 `credentials.example.env`，不要将真实值保存进打包文件。

## 四、验收

```sh
python3 -m unittest discover -s Microduck数据采集/tests -p "test_*.py"
python3 Microduck数据采集/sync_monitoring_tiers.py
python3 Microduck数据采集/collector.py
python3 Microduck数据采集/feishu/send_digest.py --dry-run
```

确认以下结果：

- GitHub 认证额度和请求正常；
- `monitoring-tiers.json` 有 A/B 名单；
- 新运行目录中有变化、Agent 阅读、新项目和分级审查队列；
- 飞书卡片预览正常，没有发送真实消息；
- 新的自动任务使用当前路径、当前 chat 和新的推送群。

## 五、打包边界

打包时不包含 `Microduck数据采集/data/`、`Microduck数据采集/runs/`、`__pycache__/`、`.env`、真实凭证和飞书发送日志。如果希望继承历史基线，可单独加密移交 SQLite 数据库，不应默认放进通用安装包。
