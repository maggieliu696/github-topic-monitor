# microduck-replica：让爱好者自己组装一只实体小鸭

名单选择号：106。资料截至2026年10月26日。方向：硬件复刻与适配。

## 项目做什么

**作者是 fanhao375，方向是硬件复刻与适配。** 项目面向想亲手造出 Microduck 的爱好者和开发者，把买零件、打印外壳、组装、调试和控制串起来。主方案采用 15 颗飞特 HD-1910 舵机和 Radxa Zero 3W 主板；机械行者 Robo 参与维护机械资料。这是社区复刻项目，与原厂 Pollen Robotics 没有隶属关系。[项目介绍](https://github.com/fanhao375/microduck-replica/blob/master/README.md)

截至 **2026-10-26 16:43（北京时间）**，仓库有 **1,367 个 Star**；较当天前次记录的 1,361 个增加 6 个，这不是一天的涨幅。最新采到的整机系统包仍是 **20261023c**，10 月 23 日发布，本轮没有重新全量核对发行版。源码和资料已公开，系统包附带模型的使用范围仍按发布说明。[仓库数据](https://api.github.com/repos/fanhao375/microduck-replica) · [版本与使用范围](https://github.com/fanhao375/microduck-replica/releases/tag/microduck-replica-image-20261023c)

## 目前做到哪一步

作者在项目说明中报告：实体鸭子已经能站立、行走、前滚翻后起身，首次装机到开始使用的流程也已跑通。用户可以通过手机或电脑上的网页配网、校准关节和姿态传感器、连接手柄、查看故障信息；项目还提供采购清单、打印资料和装配教程。[当前功能与演示说明](https://github.com/fanhao375/microduck-replica/blob/master/README.md)

**“实体能走”已经有作者报告；“用本项目的新训练工具训练出动作，再完整用到实体上”仍待验证。** 电脑端训练工具已完成短时间训练、动作回放和模型导出的试验，长时间训练及自训动作上机尚未完成。最新版本新增的部分姿态传感器兼容也只通过软件检查，仍需接真实电路板测试。本轮没有独立运行代码或验证实体效果。[训练进度](https://github.com/fanhao375/microduck-replica/blob/master/README.md) · [新增硬件兼容的验证范围](https://github.com/fanhao375/microduck-replica/releases/tag/microduck-replica-image-20261023c)

网页还支持导入和切换动作模型，省去每换一个动作就重装系统的麻烦。不过，摄像头页面存在并不代表真实摄像头已经测通；发布说明写明默认仍使用测试画面，真实摄像头和距离传感器需要另外验证。[模型管理与感知功能](https://github.com/fanhao375/microduck-replica/releases/tag/microduck-replica-image-20261023)

## 遇到了什么问题，怎样处理

**安装调试曾经卡住，作者在连续改进。** 旧版本出现主程序一直显示“启动中”、网页读不到机器人数据的问题，后续版本修正了启动状态判断。另一处问题是机器人已经站稳，系统却不接受这个姿势进行传感器校准；10 月 23 日的更新增加了相应支持。后来作者又报告完整上手已跑通，因此不能把这些旧问题写成今天仍然无法使用。[启动修复](https://github.com/fanhao375/microduck-replica/releases/tag/microduck-replica-image-20261021) · [校准修复](https://github.com/fanhao375/microduck-replica/releases/tag/microduck-replica-image-20261023b)

**复刻者还想知道“到底照哪套方案买和装”。** Gianluca 已开始打印零件，但采购前仍想确认经过实测的板卡、供电接线和软件配置；另一位用户准备增加视觉、语音对话和家人识别，追问打印参数、现成动作是否可用，以及电路板能否拼单。这些扩展功能是用户的计划，不能算成项目已实现的能力。[装配前的具体提问](https://github.com/fanhao375/microduck-replica/issues/33) · [采购与功能扩展需求](https://github.com/fanhao375/microduck-replica/issues/46)

项目目前已增加采购、装配和首次使用资料，但本轮没有看到上述提问者确认自己的鸭子已经装好。还有用户直接说逐个找零件太麻烦，希望拼团。**当前值得关注的是：有兴趣的人已经开始动手，后续能否用明确的配置和采购方案帮助他们完成组装。** 这些讨论说明存在具体需求，还不能证明付费意愿或成交规模。[寻找拼单渠道](https://github.com/fanhao375/microduck-replica/issues/38)

## 更新记录

以下日期按北京时间整理；首次采集前的内容是历史进展。

- **2026 年 10 月 21 日：** 发布系统包 20261021，修复一直显示“启动中”的问题，并增加站姿控制、网络设置等功能。当时只确认了部分实机步骤。[发布记录](https://github.com/fanhao375/microduck-replica/releases/tag/microduck-replica-image-20261021)
- **2026 年 10 月 23 日：** 当天连续更新模型管理、传感器校准和兼容功能。最新的 20261023c 可以自动识别指定格式的姿态传感器，但新兼容方案仍待真实电路板验证。[发布记录](https://github.com/fanhao375/microduck-replica/releases/tag/microduck-replica-image-20261023c)
- **2026 年 10 月 24—25 日：** 作者分别记录实体运动演示和首次上手流程跑通；尚未逐一核对演示使用的系统包、传感器及动作模型组合。[作者进展说明](https://github.com/fanhao375/microduck-replica/blob/master/README.md)
- **2026 年 10 月 26 日：** 首次采集并整理本记录，记下 1,361 个 Star。今天完成的是我们的资料整理，上述项目进展不能都算成今天新增；Star 增减从下一次可比采集开始计算。[仓库信息](https://api.github.com/repos/fanhao375/microduck-replica)

**2026 年 10 月 26 日：纳入本轮各类 Star 前十的跟踪名单。** 本轮复查公开留言，继续看到打印、板卡配套和交流群入口的问题；没有把提问当作已购买。Star 在 2026-10-26 16:43 记录为 1,367。原有问题和历史进展保留在本文。[最新留言](https://github.com/fanhao375/microduck-replica/issues)
