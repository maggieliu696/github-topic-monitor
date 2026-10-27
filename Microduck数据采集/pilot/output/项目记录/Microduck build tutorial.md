# Microduck build tutorial｜给想自己组装鸭子的人一套入门教程和系统镜像

名单选择号：108。方向：自己组装、换零件和调试。作者／发布账号：**ai-fange**。资料整理日期：2026 年 10 月 26 日。

## 项目做什么

用 Raspberry Pi Zero 2 W、OpenRB-150 和 XL330 电机搭建 Microduck，提供买零件、打印、接线、装系统、调试和运行行走模型的说明。项目账号为 AI-FanGe。 [项目说明](https://github.com/AI-FanGe/Microduck-build-tutorial)

代码或制作资料已在 GitHub 公开。**Star：1,489**，采集于 2026-10-26 16:43（北京时间）。已提供 microduck.img.xz 镜像；本次未核实其最新发布标签。 [仓库数据](https://api.github.com/repos/AI-FanGe/Microduck-build-tutorial)

## 目前做到哪一步

已提供含运行环境、行走模型和手柄服务的系统镜像，也保留训练与导出模型的代码。作者明确感谢 Microduck 等开源工作提供结构、训练和实机流程基础。相关的 wslengzhicheng/microduck-diy 资料沿用原研究中的合并关系，不重复算一个项目。 [项目说明](https://github.com/AI-FanGe/Microduck-build-tutorial)

**当前判断：**这类教程受到较多关注，也已有实际复现问题和研究用途咨询。不能只因材料齐全，就认定初学者可以完整无障碍复刻；模拟流程与实机运行要分别验证。

## 遇到了什么问题，怎样处理

10 月 25 日有第三方报告：模拟文件与控制程序使用的关节数量、名称不一致，启动就报错，并遇到模拟依赖无法安装。该用户称自行调整后跑通站立阶段，但尚无作者回复，不能认定原项目已修好。同日另一位用户咨询能否把鸭子作为训练后评测的平台；这是明确研究用途，但其职业身份与后续购买均未核实。 [模拟启动失败与用户自改](https://github.com/AI-FanGe/Microduck-build-tutorial/issues/14) · [用于机器人研究的咨询](https://github.com/AI-FanGe/Microduck-build-tutorial/issues/13)

## 按日期记录进展

**2026 年 10 月 26 日：首次建立项目记录。** 按本方向 Star 排序第 1 位纳入本轮，记录用途、进展、问题及上述验证边界。当次 Star 为 1,489，这一数字不是用户或买家人数。文中此前的测试和功能是历史资料，不是今天新增。[仓库数据](https://api.github.com/repos/AI-FanGe/Microduck-build-tutorial)

资料依据为今天已保存的原作者说明和本轮公开留言查询。本轮取得该仓库公开问题区的 14 条帖子。仅补读了部分关键帖的回复，未独立运行代码或测试机器人；未核实的发行版本已在上文注明。 配套资料与原项目合并记录：[资料1](https://github.com/wslengzhicheng/microduck-diy)。
