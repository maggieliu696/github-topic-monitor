# microduck-lab (Hermes Agent)｜预订鸭子后，先训练动作并让 AI 用自然语言控制

名单选择号：69。方向：鸭子能用来做什么、怎么玩。作者／发布账号：**notwitcheer**。资料整理日期：2026 年 10 月 26 日。

## 项目做什么

作者 notwitcheer 明确说鸭子仍在预订中，因此先在电脑里开发：一边接入 Hermes Agent 的自然语言控制，一边训练走路、起身、踢球等动作。 [项目说明](https://github.com/notwitcheer/microduck-lab)

代码或制作资料已在 GitHub 公开。**Star：4**，采集于 2026-10-26 16:43（北京时间）。各动作模型分别维护版本和测试结果，没有一个版本号可以代表整套实验都验证完成。 [仓库数据](https://api.github.com/repos/notwitcheer/microduck-lab)

## 目前做到哪一步

GitHub 保存工具、训练条件和修补代码；Hugging Face 保存动作模型与训练记录。作者还加入台阶、湿滑地面、坡面和推搡等条件，分别记录动作表现。这些模型和记录合并到同一项目，避免重复计算。 [项目说明](https://github.com/notwitcheer/microduck-lab)

**当前判断：**这是明确表达预订、并在等待期间持续开发的线索。它能帮助理解早期买家在研究什么，但只能代表该作者，不能推算买家总体。

## 遇到了什么问题，怎样处理

作者发现原粗糙地形训练可能把站在较低台阶上的鸭子误判为倒下，随后重置；还发现练习难度的排序不合理。已提供六项补丁，调整地面高度判断和难度升降规则。全部结果仍限于模拟，尚未接触实体机器人。 [项目说明](https://github.com/notwitcheer/microduck-lab)

## 按日期记录进展

**2026 年 10 月 26 日：首次建立项目记录。** 按本方向 Star 排序第 7 位纳入本轮，记录用途、进展、问题及上述验证边界。当次 Star 为 4，这一数字不是用户或买家人数。文中此前的测试和功能是历史资料，不是今天新增。[仓库数据](https://api.github.com/repos/notwitcheer/microduck-lab)

资料依据为今天已保存的原作者说明和本轮公开留言查询。本轮官方搜索未返回该仓库的问题帖；这不表示没有使用问题。仅补读了部分关键帖的回复，未独立运行代码或测试机器人；未核实的发行版本已在上文注明。 配套资料与原项目合并记录：[资料1](https://huggingface.co/datasets/witcheer/microduck-skill-tree) · [资料2](https://huggingface.co/datasets/witcheer/microduck-hermes-runs)。
