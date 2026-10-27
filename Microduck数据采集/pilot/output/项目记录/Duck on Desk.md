# Duck on Desk｜让虚拟鸭子陪伴编程，也能尝试训练新动作

名单选择号：98。资料截至2026年10月26日。方向：AI应用与交互玩法。

## 项目做什么

作者是 **Happenmass**。项目把 Microduck 做成电脑桌面上的虚拟伙伴：AI 编程工具工作时走动，需要用户授权时鸣叫，闲置时休息。目前接入 Claude Code、Codex CLI、opencode 和 Pi，其中 Pi 只同步工作状态。它属于 AI 应用与交互玩法；使用虚拟鸭子不代表购买了实体机器人。[项目介绍](https://github.com/Happenmass/duck-on-desk/blob/main/README.md)

项目代码已公开，作者注明代码与模型、声音等素材适用不同许可，使用前应查看对应说明。[代码与素材说明](https://github.com/Happenmass/duck-on-desk/blob/main/README.md)

**已采集资料中最新版本是 v1.2.0，发布于 2026年9月11日。** 10月26日采集时为 **15 个 Star**；这是一次关注数量记录，不能计算涨幅，也不代表用户或买家人数。以下按资料原本的日期记录进展，10月26日是整理日期。[版本说明](https://github.com/Happenmass/duck-on-desk/releases/tag/v1.2.0) · [仓库信息](https://api.github.com/repos/Happenmass/duck-on-desk)

## 目前做到哪一步

除了桌面陪伴，作者提供了训练实验室：查看和控制关节、修改训练评分规则、查看过程、继续未完成的训练，并将结果导出给桌宠使用。还接入了另一种机器人 Reachy Mini，支持实体与虚拟画面联动；这项能力不能写成实体 Microduck 已能被它控制。[项目介绍](https://github.com/Happenmass/duck-on-desk/blob/main/README.md) · [机器人联动说明](https://github.com/Happenmass/duck-on-desk/releases/tag/v0.2.0)

当前判断是：**它已把编程陪伴与动作实验放进同一个应用，但训练成功和稳定使用仍有条件。** 苹果电脑上的官方行走训练目前主要用于确认流程能运行；大规模训练仍需 NVIDIA 设备验证。轮滑转向靠程序直接旋转身体，高跷跌倒也由程序扶正，不能把画面表现全部理解为机器人自己学会了这些能力。[行走训练说明](https://github.com/Happenmass/duck-on-desk/releases/tag/v1.2.0) · [动作限制](https://github.com/Happenmass/duck-on-desk/blob/main/README.md)

## 问题与处理情况

**苹果电脑训练是否正常，尚未确认。** 用户 hiyizi 在9月12日反馈：选择苹果 GPU 训练，却看不到负载；作者9月14日表示上游框架没有原生支持，并计划修复。另一方面，项目说明和版本记录称苹果训练已测试。由于用户的软件版本不明确，也没有其复测确认，暂时不能认定问题已解决，或所有苹果训练都失效。[用户反馈与作者回复](https://github.com/Happenmass/duck-on-desk/issues/1)

**是否必须联网下载，说明存在差异。** 当前项目介绍称动作模型随安装包提供；v1.1.1 则称首次使用需要下载。还需核对具体安装包、版本和动作，不能直接承诺完全离线。NVIDIA 训练尚待实机验证，Windows 还记录了系统拦截训练依赖文件的问题；有安装包不等于所有设备都能顺利训练。[项目介绍](https://github.com/Happenmass/duck-on-desk/blob/main/README.md) · [下载说明](https://github.com/Happenmass/duck-on-desk/releases/tag/v1.1.1) · [设备限制](https://github.com/Happenmass/duck-on-desk/releases/tag/v1.2.0)

## 按日期记录进展

**2026年9月6日：加入 Reachy Mini 联动。** 可连接实体机器人，也可显示虚拟机器人，让头部、天线等动作响应编程状态。这是应用向另一种机器人扩展的记录。[版本说明](https://github.com/Happenmass/duck-on-desk/releases/tag/v0.2.0)

**2026年9月7日至8日：处理静止、耗电和更新失败问题。** 作者称修正启动时消息丢失造成鸭子不动的问题；降低画面刷新率并简化阴影后，在一台120赫兹屏幕的 Mac 上，应用占用单核处理器的比例由53.8%降至26.5%。另修正了错误的更新地址，旧版本需先手动更新一次。这些是作者报告的测试结果。[静止问题](https://github.com/Happenmass/duck-on-desk/releases/tag/v0.2.1) · [性能改动](https://github.com/Happenmass/duck-on-desk/releases/tag/v0.2.2) · [更新修复](https://github.com/Happenmass/duck-on-desk/releases/tag/v0.2.3)

**2026年9月8日至9日：加入训练与教学功能。** 实验室随后增加继续训练、自动准备部分运行环境等功能，并修复 Windows 中文配置读取问题。最初短时测试证明训练、导出和桌宠加载可以串起来，还不能证明动作已经学好。[实验室发布](https://github.com/Happenmass/duck-on-desk/releases/tag/v1.0.0) · [教学与续训](https://github.com/Happenmass/duck-on-desk/releases/tag/v1.1.1) · [环境修复](https://github.com/Happenmass/duck-on-desk/releases/tag/v1.1.2)

**2026年9月10日：倒立恢复实验暴露评分问题。** 旧规则会惩罚恢复所需的蹬地动作，也会把“折叠在头上”的失败姿态评成高分。作者调整评分和起始姿势后，报告三次不同随机设置的训练仅一次成功。这个实验说明评分规则会让机器学偏，目前还不能认为结果稳定。[实验与修改记录](https://github.com/Happenmass/duck-on-desk/releases/tag/v1.1.4)

**2026年9月11日：行走课程改用官方训练环境。** 苹果电脑由处理器计算物理、GPU 计算模型，作者称本机运行200轮约37分钟，仅适合验证流程。大规模训练仍需在 NVIDIA 上复现。后续重点看用户复测及不同设备表现；本记录没有安装软件或独立重跑实验。[版本说明](https://github.com/Happenmass/duck-on-desk/releases/tag/v1.2.0)

**2026年10月26日：首次采集并整理本记录。** 当次为15个 Star，尚无前次数据可计算涨幅；以上功能和修复属于历史进展。后续继续在本文追加用户复测结果、新版本及关注数量变化。[仓库信息](https://api.github.com/repos/Happenmass/duck-on-desk)

**2026 年 10 月 26 日：纳入本轮各类 Star 前十的跟踪名单。** 2026-10-26 16:43 的仓库数据仍为 15 个 Star，与此前记录相同。重新取得的苹果 GPU 提问仍处于开放状态；没有新的用户复测材料足以改变上面的判断。[仓库数据](https://api.github.com/repos/Happenmass/duck-on-desk) · [用户提问](https://github.com/Happenmass/duck-on-desk/issues/1)
