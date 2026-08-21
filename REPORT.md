# Round 1 报告

## 实现概述

已实现题目规定的 `Event`、`Effect` 和 `RobotApplication` 公共接口。应用层通过私有状态机返回迎宾、语音和送客 Effect，不导入 ROS 2、相机或机器人 SDK。

## 测试

测试命令：

```text
C:/Users/Lenovo/.conda/envs/lang/python.exe -m pytest -q
```

实际结果：`19 passed in 0.10s`。测试覆盖首次/重复进入、对话和会议抑制及不补发、9/10/10.001 秒边界、只送客一次、短暂离开、完整离场后再进入、快照隔离和重复事件。

## ROS 2 日志判断

### 事实

- `app effect_created type=ROBOT_ACTION value=wave_hand` 证明业务层创建了 `wave_hand` 的动作意图。
- `request_submitted` 与 `accepted_async` 证明 Bridge 已提交请求且异步接受该请求。
- `/basic_action_play_v2` 显示 1 个 Action Client、0 个 Action Server。
- `/get_robot_mode` 的调用返回 `mode_name: STAND`。
- `robot-action.service` 的状态为 `inactive`。

### 推断

`accepted_async` 不代表机器人已完成挥手；它不包含 Action Server 接收、执行、结果或硬件控制器完成的证据。Action Server 为 0 和服务 inactive 使 Action Server/动作服务层最值得优先排查，但日志本身不能唯一定位根因。

### 待验证与下一步

按调用链检查：业务层 Effect 内容 → Bridge 的请求映射与错误日志 → ROS 2 Action Client 的目标名称/连通性 → Action Server 是否启动并可发现 → `robot-action.service` 的状态、日志与依赖 → Robot Controller 的命令和故障 → 真实硬件的安全状态与执行反馈。

当前不能直接执行真实动作：没有可发现的对应 Action Server，动作服务也未激活，且没有硬件执行完成的证据。本项目没有尝试调用真实机器人。

## 未完成项

没有题目要求范围内的代码 TODO。创建 Draft PR、转为 Ready for review、提交和推送属于 GitHub 流程，未在本次工作中执行。
