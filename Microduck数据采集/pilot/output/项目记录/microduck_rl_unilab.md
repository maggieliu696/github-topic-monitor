# microduck_rl_unilab｜比较不同训练方法，检查鸭子是否真的学会动作

名单选择号：26。方向：教鸭子做动作。作者／发布账号：**rocpai-forge**。资料整理日期：2026 年 10 月 26 日。

## 项目做什么

把 Microduck 的行走、冲刺和倒地恢复任务接入 UniLab，并配套面向初学者的教程。重点是比较不同算法和模拟环境下的实际动作，而不只看训练得分。 [项目说明](https://github.com/rocPAI-Forge/microduck_rl_unilab)

代码或制作资料已在 GitHub 公开。**Star：9**，采集于 2026-10-26 16:43（北京时间）。已看到 2026-10-15 的行走记录；配套教程注明 v2.6。二者不是同一个软件版本。 [仓库数据](https://api.github.com/repos/rocPAI-Forge/microduck_rl_unilab)

## 目前做到哪一步

作者记录：2026 年 10 月 15 日，基础行走的一组训练完成，MuJoCo 回放能站稳并迈步。冲刺实验从跑得快但头部倒置，逐步调整到头部朝上、较长时间走直线；还给出了特定强制摔倒测试中的起身模型。 [项目说明](https://github.com/rocPAI-Forge/microduck_rl_unilab)

**当前判断：**这个项目的价值在于同时保留成功和失败。需要把算法、代码版本和测试条件一起记录，不能把一个任务的成功概括成所有动作都已跑通。

## 遇到了什么问题，怎样处理

另一种 SAC 训练虽然完成了 5,000 轮，回放仍反复摔倒，被作者标为不可用。用户还报告：降低同时训练的数量后可以避开内存不足，但某一版本的行走加恢复任务仍学不会起身。后来的成功示例不能自动证明该用户配置的问题已解决。 [用户的内存与起身失败记录](https://github.com/rocPAI-Forge/microduck_rl_unilab/issues/2) · [配套教程](https://github.com/rocPAI-Forge/microduck_rl_tutorial)

## 按日期记录进展

**2026 年 10 月 26 日：首次建立项目记录。** 按本方向 Star 排序第 6 位纳入本轮，记录用途、进展、问题及上述验证边界。当次 Star 为 9，这一数字不是用户或买家人数。文中此前的测试和功能是历史资料，不是今天新增。[仓库数据](https://api.github.com/repos/rocPAI-Forge/microduck_rl_unilab)

资料依据为今天已保存的原作者说明和本轮公开留言查询。本轮取得该仓库公开问题区的 1 条帖子。仅补读了部分关键帖的回复，未独立运行代码或测试机器人；未核实的发行版本已在上文注明。 配套资料与原项目合并记录：[资料1](https://github.com/rocPAI-Forge/microduck_rl_tutorial)。
