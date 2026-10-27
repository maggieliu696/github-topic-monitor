# microduck-rl-on-thor｜解决 NVIDIA Thor 上训练鸭子时的软件兼容问题

名单选择号：12。方向：让安装、控制和开发更容易。作者／发布账号：**metahubaifeel**。资料整理日期：2026 年 10 月 26 日。

## 项目做什么

帮助使用 NVIDIA Thor 这类 ARM 架构设备的人安装官方训练环境。重点是把安装和运行中踩过的坑写清楚，并提供训练、继续训练和录像脚本。 [项目说明](https://github.com/metahubaifeel/microduck-rl-on-thor)

代码或制作资料已在 GitHub 公开。**Star：12**，采集于 2026-10-26 16:43（北京时间）。原文记载其可运行组合为 torch 2.11.0+cu130，并保留其他上游依赖锁定；本次未复跑该环境。 [仓库数据](https://api.github.com/repos/metahubaifeel/microduck-rl-on-thor)

## 目前做到哪一步

作者称在真实 Thor 计算设备上逐项验证了故障与绕过办法，包括换用支持 GPU 的 PyTorch、核对 CUDA 版本和无显示器环境下的图像输出。这里的‘真实硬件测试’指计算设备，不是实体鸭子已经跑通。 [项目说明](https://github.com/metahubaifeel/microduck-rl-on-thor)

**当前判断：**这是一份针对特定机器的排障资料。它说明‘装好了’不等于‘能训练’，但作者的版本组合不能直接当作所有 NVIDIA 设备通用方案。

## 遇到了什么问题，怎样处理

默认安装可能得到只能用 CPU 的包；有的版本虽然识别到显卡，实际计算仍报错。作者报告特定版本的矩阵计算故障，并改用其测通的版本；还提醒环境自动同步可能把修好的依赖换回去。没有显示器的机器录视频时，也需要对应的渲染配置。 [项目说明](https://github.com/metahubaifeel/microduck-rl-on-thor)

## 按日期记录进展

**2026 年 10 月 26 日：首次建立项目记录。** 按本方向 Star 排序第 3 位纳入本轮，记录用途、进展、问题及上述验证边界。当次 Star 为 12，这一数字不是用户或买家人数。文中此前的测试和功能是历史资料，不是今天新增。[仓库数据](https://api.github.com/repos/metahubaifeel/microduck-rl-on-thor)

资料依据为今天已保存的原作者说明和本轮公开留言查询。本轮官方搜索未返回该仓库的问题帖；这不表示没有使用问题。仅补读了部分关键帖的回复，未独立运行代码或测试机器人；未核实的发行版本已在上文注明。
