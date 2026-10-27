# quacksat｜把鸭子做成可以说话、接入家庭控制系统的助手

名单选择号：63。方向：鸭子能用来做什么、怎么玩。作者／发布账号：**andreagenovese**。资料整理日期：2026 年 10 月 26 日。

## 项目做什么

让 Microduck 听到唤醒词后接收语音，把对话交给 Home Assistant、外部 AI 服务，或兼容的本地与云端模型。没有鸭子时，也能先用电脑的麦克风和扬声器测试。 [项目说明](https://github.com/andreagenovese/quacksat)

代码或制作资料已在 GitHub 公开。**Star：5**，采集于 2026-10-26 16:43（北京时间）。语音服务 v0.1.0-rc2（2026-10-10）；配套网页控制 0.1.0-rc2，导航需按其兼容说明另行匹配。 [仓库数据](https://api.github.com/repos/andreagenovese/quacksat)

## 目前做到哪一步

作者记录 v0.1.0-rc2 于 2026 年 10 月 10 日发布，已在开发用 Mac、真实家庭控制服务及模拟鸭子上验证部分流程。家庭控制界面可以显示状态、发动作指令；导航另拆成 quack-nav，网页控制另有 quack-control，本档合并记录这一组配套工作。 [项目说明](https://github.com/andreagenovese/quacksat)

**当前判断：**它展现了‘会说话’向‘在家里办事’扩展的路线。关键后续是实物到手后的麦克风、移动和导航表现，而不是仅看支持多少种 AI 服务。

## 遇到了什么问题，怎样处理

作者把实体鸭子验证列为后续事项。没有导航服务时，鸭子可以听和回答，却不能按要求去某个地方。配套导航与网页控制目前也主要在模拟环境中测试，家庭服务接通不等于真实家中移动已经可靠。 [配套导航及模拟边界](https://github.com/andreagenovese/quacknav) · [配套网页控制](https://github.com/andreagenovese/quack-control)

## 按日期记录进展

**2026 年 10 月 26 日：首次建立项目记录。** 按本方向 Star 排序第 6 位纳入本轮，记录用途、进展、问题及上述验证边界。当次 Star 为 5，这一数字不是用户或买家人数。文中此前的测试和功能是历史资料，不是今天新增。[仓库数据](https://api.github.com/repos/andreagenovese/quacksat)

资料依据为今天已保存的原作者说明和本轮公开留言查询。本轮官方搜索未返回该仓库的问题帖；这不表示没有使用问题。仅补读了部分关键帖的回复，未独立运行代码或测试机器人；未核实的发行版本已在上文注明。 配套资料与原项目合并记录：[资料1](https://github.com/andreagenovese/quacknav) · [资料2](https://github.com/andreagenovese/quack-control)。
