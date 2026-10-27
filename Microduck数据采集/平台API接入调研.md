# Microduck 九个平台 API 接入调研

资料核对日期：2026年10月26日

GitHub、Hugging Face、Hacker News、YouTube 可以优先接入；X 适合小预算试接；Reddit 需先确认使用许可；LinkedIn、Discord、Bilibili 暂缓。第一阶段执行范围确定为 GitHub、Hugging Face 和 Hacker News。

费用仅指平台取数费，不含开发、服务器和 AI 分析。Token／API Key 是程序访问平台的凭证。下表的每日更新方式为实施方案；免费额度和公开价格须在实际接入时核对。

| 平台 | 取什么 | 需要什么账号或权限 | 费用多少 | 每天怎样更新 |
|---|---|---|---|---|
| GitHub | 项目说明、问题与回复、版本发布、修复进展 | 免费账号及只读 Token；公开项目无需每位作者单独授权 | 常规额度内0美元。匿名主额度60次/小时，普通认证 REST 主额度5,000次/小时，搜索另有限额 | 搜索新项目；检查已有122个项目；读取变化的说明、新增或修改的问题与评论 |
| Hugging Face | 仿真作品、模型或动作说明、作者、公开讨论 | 公开资源可先匿名读取；建议免费账号配置只读 Token | 免费 Hub 额度内0美元；只读资料，不运行收费训练或推理 | 搜索新增作品，比较已有项目版本；可选官方仓库更新通知 |
| Hacker News | 帖子、评论、回复关系、作者公开署名 | 不需要账号或密钥 | 官方公共接口0美元 | 发现新条目并筛选关键词，回查相关帖的评论树；官方接口没有通用关键词搜索 |
| YouTube | 视频标题、介绍、作者、公开评论及回复 | Google账号、Cloud项目、启用API及API Key；公开内容无需作者授权 | 默认免费额度内0美元。当前默认每天100次搜索，其他接口合计10,000配额单位，超额需申请 | 搜索新视频；读取新评论，并另查旧评论下面的新回复，定期刷新历史内容 |
| X | 关键词帖子、创作者动态、回复、公开互动数 | 开发者账号、应用、Token及API余额 | 当前帖子读取0.005美元/条，用户资料读取0.01美元/个；以开发者后台为准 | 从上次成功位置继续取数并去重；近期搜索覆盖7天，长时间中断需历史补采 |
| Reddit | 相关社区帖子、评论、购买自述、用途和求助 | 按实际市场研究用途申请许可；获批应用和OAuth授权；商业用途需另行许可或合同 | 待平台确认或报价；不直接套用免费开发额度 | 获批后搜索新帖，回查已有讨论的新回复、修改和删除，按获批范围执行 |
| LinkedIn | 获授权主页的帖子、评论等；不能自由搜索全站个人帖子 | 企业资料、关联主页和API审批；会员帖子读取权限 r_member_social 当前不接受新申请 | 没有确认适用于本需求的公开报价，主要障碍是权限 | 获批后仅更新允许访问的范围；全站用户讨论监测暂不排期 |
| 官方 Discord | 技术上可读取授权频道消息，但本次用户画像用途受限 | Bot进服和频道权限并不足够；官方禁止利用API数据建立用户画像，也禁止数据挖掘 | 没有确认适用于本研究的许可报价 | 暂停常规自动采集；需先由平台明确允许的研究方式 |
| Bilibili | 已授权UP主的视频资料、播放及评论数等；跨作者评论正文能力未确认 | 开发者入驻、应用审核、相应权限和UP主授权 | 未核实统一价格，不能直接标免费 | 获UP主授权后可更新其稿件和数据；全站搜索和评论研究尚无确认的官方接入方案 |

## 费用估算

前三个平台的公开取数可以按0美元平台接口费启动。若后续加入X，假设每天读取100条帖子，30天的帖子读取费约15美元；作者资料、跨日重复读取和历史补采另计。这是预算示例，不代表实际讨论量。

## 第一阶段调研目标和节奏

围绕三个问题持续观察：开发者在做什么；遇到什么实际问题及是否解决；作者怎样评价Microduck。保留明确的购买自述，但不把开发项目或评论者自动视作买家。

每天一次采集变化并整理，新增内容与历史首次入库分开。每条记录保留原链接、采集时间、来源更新时间和正文；报告区分证据与推测。先跑通，再根据一周内的信息量调整关注点。

GitHub以现有项目清单、官方仓库和关键词搜索为入口；Hugging Face以官方仿真页面、既有作品及关键词搜索为入口；Hacker News以已知产品讨论和新增帖子为入口。采集上限或访问失败必须在运行报告中显示，不能把未采集到解释为没有讨论。

## 两项关键修正

Discord管理员允许机器人进入，只解决部分技术权限，不能覆盖平台对用户画像和数据挖掘用途的限制。LinkedIn的会员帖子读取权限目前暂停接受新申请，不能作为常规可申请的全站研究入口。

Bilibili官网部分文档未能取得完整当前正文，跨作者评论能力和报价仍需平台确认。

## 官方资料

- GitHub：[访问额度](https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api)、[项目说明接口](https://docs.github.com/en/rest/repos/contents)、[问题及评论](https://docs.github.com/en/rest/issues/comments)
- Hugging Face：[Hub API](https://huggingface.co/docs/hub/api)、[额度](https://huggingface.co/docs/hub/rate-limits)、[只读凭证](https://huggingface.co/docs/hub/security-tokens)、[更新通知](https://huggingface.co/docs/hub/webhooks)
- Hacker News：[官方 API](https://github.com/HackerNews/API)
- YouTube：[接入](https://developers.google.com/youtube/v3/getting-started)、[配额](https://developers.google.com/youtube/data/determine_quota_cost)、[评论](https://developers.google.com/youtube/v3/docs/commentThreads/list)、[回复](https://developers.google.com/youtube/v3/docs/comments/list)
- X：[价格](https://docs.x.com/x-api/getting-started/pricing)、[搜索范围](https://docs.x.com/x-api/posts/search/introduction)
- Reddit：[访问和用途规则](https://support.reddithelp.com/hc/en-us/articles/14945211791892-Developer-Platform-Accessing-Reddit-Data)
- LinkedIn：[权限现状](https://learn.microsoft.com/en-us/linkedin/marketing/community-management/community-management-overview)、[申请要求](https://learn.microsoft.com/en-us/linkedin/marketing/community-management-app-review)
- Discord：[开发者政策](https://support-dev.discord.com/hc/en-us/articles/8563934450327-Discord-Developer-Policy)
- Bilibili：[开放平台](https://open.bilibili.com/doc)、[开发者协议](https://open.bilibili.com/agreement/developer-service)
