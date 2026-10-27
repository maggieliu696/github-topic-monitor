# Microduck Academy｜面向编程开发者的机器人入门课堂

资料截至2026年10月26日。方向：开发工具与运行环境。

## 项目做什么

**Microduck Academy 由 kingsleyli920 开发，面向会编程、但刚开始学习机器人控制和训练的人。** 它把代码练习、测试反馈和三维鸭子放在同一页面，让学习者边写代码边观察效果。它是独立社区项目，作者明确表示并非机器人母公司或 Hugging Face 的官方课程。[项目介绍](https://github.com/kingsleyli920/microduck-academy/blob/main/README.md)

项目源码已公开，作者自有代码采用 Apache-2.0 许可；使用的模拟器和模型另有来源。**已采集资料中最新发布版为 v0.2.1-preview，发布于2026年9月11日；10月26日取得的 GitHub 数据为0个 Star。** Star 只是仓库关注记录，不是实际学习人数；目前只有一次采集，不能计算增减。[仓库信息](https://api.github.com/repos/kingsleyli920/microduck-academy) · [版本说明](https://github.com/kingsleyli920/microduck-academy/releases/tag/v0.2.1-preview)

## 目前做到哪一步

已有9节中英文编程练习和6个动作观察实验。学习者可以让鸭子行走、转向、转头或切换已有动作，还可以调整评分规则，对比同一套动作在不同规则下的表现。课程会检查代码结果，提供提示，并保存学习进度。[课程与功能](https://github.com/kingsleyli920/microduck-academy/blob/main/README.md)

**当前可以用它学习和观察已有动作，还不能通过修改评分直接教会鸭子新动作。** 真正训练新动作、导出训练结果、部署到实体机器人都仍在计划中。它提供了一个入门工具，但还不是覆盖训练到实机使用的完整平台。[当前功能和后续计划](https://github.com/kingsleyli920/microduck-academy/blob/main/README.md)

课堂主要在本机运行，无需账号，进度保存在浏览器，也可导出备份。首次安装仍需联网，并要准备 Node.js、Git 等开发工具；主动加载其他作者的动作模型时也会访问网络。因此“本地运行”不等于完全离线，也不代表小白无需安装配置即可使用。[安装与数据保存说明](https://github.com/kingsleyli920/microduck-academy/blob/main/README.md)

## 遇到的问题，作者怎样处理

**课程解释和示例有过修正。** 作者在 v0.2.1 中修正了部分动作控制、训练评分和部署安全的课程说明，也修改了重力方向示例；鸭子拒绝某个动作时，界面会显示错误，帮助学习者判断代码为什么没有效果。[修订记录](https://github.com/kingsleyli920/microduck-academy/releases/tag/v0.2.1-preview)

**启动和显示问题有了针对性处理。** 同一版本改进了服务启动、端口冲突及学习档案导入检查，修复从轮滑模式切回双腿模式时的控制问题，并调整手机窄屏布局。作者称已通过16项测试，并在本机试用了全部课程和主要操作。这些是作者的测试报告，我们尚未安装复现，也没有取得学习者确认问题解决的反馈。[修复与测试记录](https://github.com/kingsleyli920/microduck-academy/releases/tag/v0.2.1-preview)

**目前最大的未知是实际教学效果。** 已取得的资料主要来自作者说明和版本发布，其他回复是自动维护机器人留下的，不能当作学习者评价。还需要确认是否有人持续使用、完成课程，以及最终做出了自己的机器人项目；现有材料也不能说明这些学习者已经购买实体鸭子。

## 按日期记录进展

**2026年9月11日：连续发布三个预览版本。** 首版公开课堂；第二版介绍双语界面、动作控制、评分实验和学习进度保存；v0.2.1 集中修正课程解释、启动和模式切换等问题。三版都没有将训练新动作和实体部署列为已完成。[首版](https://github.com/kingsleyli920/microduck-academy/releases/tag/v0.1.0-preview) · [第二版](https://github.com/kingsleyli920/microduck-academy/releases/tag/v0.2.0-preview) · [修正版](https://github.com/kingsleyli920/microduck-academy/releases/tag/v0.2.1-preview)

**2026年10月26日：首次采集并整理本记录。** 当次仓库为0个 Star，尚无可比较的前次记录。上述发布与修复是历史进展，不是今天才发生的更新。下一次有实质变化时，继续在这里追加日期、变化内容、问题处理结果和来源。[仓库信息](https://api.github.com/repos/kingsleyli920/microduck-academy)
