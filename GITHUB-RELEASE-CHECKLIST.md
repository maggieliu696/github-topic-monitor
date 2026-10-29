# v0.2.0-preview发布检查

- 运行scripts/package_for_github.py生成白名单源码包和SHA256。
- 从解压包运行环境检查、完整离线测试、HF基线初始化、CSV导出及卡片预览。
- 扫描真实Token、Webhook、密钥、用户路径、对话ID；不输出匹配到的秘密内容。
- 确认data、runs、huggingface-runs、feishu/state、node_modules和预编译二进制没有进入源码包。
- 保留MIT和第三方许可证；来源示例不改变第三方权利。
- GitHub推送是独立步骤；本地打包完成不表示远端已更新。
