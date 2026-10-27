# Isaac Lab Microduck port｜把鸭子的多种训练任务接入 Isaac Lab

名单选择号：2。方向：教鸭子做动作。作者／发布账号：**5usu**。资料整理日期：2026 年 10 月 26 日。

## 项目做什么

作者 5usu 在自己的 IsaacLab 仓库分支中增加 Microduck，提供机器人模型、关节控制和训练任务，让开发者沿用 Isaac Lab 的训练、回放和导出流程。 [项目说明](https://github.com/5usu/IsaacLab/blob/microduck-port/source/isaaclab_microduck/docs/README.md)

代码或制作资料已在 GitHub 公开。**Star：18**，采集于 2026-10-26 16:43（北京时间）。跟踪 microduck-port 分支中的 Microduck 扩展，不能用 Isaac Lab 本体版本代表这部分的完成程度。 [仓库数据](https://api.github.com/repos/5usu/IsaacLab)

这里的 Star 是整个仓库的数量，不是 Microduck 分支单独的数量。

## 目前做到哪一步

说明列出行走、跌倒恢复、坐站、拾取等 21 类主要任务，并说明如何生成模型资源和导出动作文件。动作接口保留 14 个受控关节；这些是已提供的配置与工作流程，不能据任务数量推断全部训练成功。 [项目说明](https://github.com/5usu/IsaacLab/blob/microduck-port/source/isaaclab_microduck/docs/README.md)

**当前判断：**适合研究第三方怎样把鸭子接进已有机器人训练工具。需要优先核对‘任务能启动’之后是否真的能学会，以及导出的动作是否适配实物。

## 遇到了什么问题，怎样处理

模型转换后的文件不随源码提供，使用者需先自行生成；修改模型后也要重新生成。本轮没有取得各任务的训练成功率、完整对照结果或实体运行证据。项目位于分支内，表里的 Star 是整个 5usu/IsaacLab 仓库的数量。 [项目说明](https://github.com/5usu/IsaacLab/blob/microduck-port/source/isaaclab_microduck/docs/README.md)

## 按日期记录进展

**2026 年 10 月 26 日：首次建立项目记录。** 按本方向 Star 排序第 4 位纳入本轮，记录用途、进展、问题及上述验证边界。当次 Star 为 18，这一数字不是用户或买家人数。文中此前的测试和功能是历史资料，不是今天新增。[仓库数据](https://api.github.com/repos/5usu/IsaacLab)

资料依据为今天已保存的原作者说明和本轮公开留言查询。本轮官方搜索未返回该仓库的问题帖；这不表示没有使用问题。仅补读了部分关键帖的回复，未独立运行代码或测试机器人；未核实的发行版本已在上文注明。
