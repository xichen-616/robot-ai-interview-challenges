# 机器人 AI 应用工程师｜第一轮实战

- 时间：不计入评分，以完成质量和验证证据为准
- 环境：Python 3.10+
- 形式：开卷，允许使用 AI；提交内容必须能够解释和验证
- 提交：Fork 本仓库并发起 Pull Request

## 任务

实现一个简化的机器人迎宾应用。

### 输入事件

```text
PERSON_ENTERED
PERSON_LEFT
CONVERSATION_STARTED
CONVERSATION_ENDED
MEETING_STARTED
MEETING_ENDED
TICK
```

事件包含：

```python
event_type: str
timestamp: float
person_id: str | None
```

### 业务规则

1. 空闲时有人进入：输出 `wave_hand` 和“欢迎光临”。
2. 同一次持续在场期间，不重复迎宾。
3. 对话或会议期间不输出迎宾、送客或机器人动作，结束后也不补发。
4. 人员离开满 10 秒后，由 `TICK` 触发送客；同一次离场只送客一次。
5. 离开不足 10 秒又返回：不送客，也不重复迎宾。
6. 完成离场确认后，再次进入视为新的接待过程。

必须满足：

| 时间 | 事件 | 输出 |
|---:|---|---|
| 0 | `PERSON_ENTERED` | 挥手 + 欢迎光临 |
| 1 | `PERSON_ENTERED` | 无 |
| 2 | `CONVERSATION_STARTED` | 无 |
| 3 | `PERSON_ENTERED` | 无 |
| 4 | `CONVERSATION_ENDED` | 无 |
| 5 | `PERSON_LEFT` | 无 |
| 14 | `TICK` | 无 |
| 15 | `TICK` | 送客一次 |
| 16 | `TICK` | 无 |
| 20 | `PERSON_ENTERED` | 挥手 + 欢迎光临 |

## 公共接口

保留以下导入路径，内部模块可自行设计。

```python
# robot_application/models.py
from dataclasses import dataclass
from typing import Optional

@dataclass(frozen=True)
class Event:
    event_type: str
    timestamp: float
    person_id: Optional[str] = None

@dataclass(frozen=True)
class Effect:
    effect_type: str
    value: str
    reason: str
```

```python
# robot_application/application.py
class RobotApplication:
    def __init__(self, absence_timeout_s: float = 10.0): ...
    def handle_event(self, event: Event) -> list[Effect]: ...
    def snapshot(self): ...
```

要求：

- `handle_event()` 只返回本次事件新产生的效果。
- `snapshot()` 返回值不能被外部修改后影响内部状态。
- 不使用全局可变状态。
- 业务模块不直接依赖 ROS 2、相机或硬件 SDK。

## 架构设计

提交 `ARCHITECTURE.md`，简要说明：

1. 模块图及依赖方向；
2. 各模块负责什么、不负责什么；
3. 谁拥有人、对话、会议、计时和去重状态；
4. 未来增加 VIP、RAG 和 ROS 2 导航时如何扩展，避免形成一个大类。

可以使用 Mermaid。重点是边界清楚，不追求复杂。

## ROS 2 判断题

```text
app          effect_created type=ROBOT_ACTION value=wave_hand
robot_bridge request_submitted task_id=task-17 action=wave_hand
robot_bridge accepted_async task_id=task-17

$ ros2 action info /basic_action_play_v2
Action clients: 1
Action servers: 0

$ ros2 service call /get_robot_mode crb_ros_msg/srv/GetRobotMode "{}"
mode_name: STAND

$ systemctl is-active robot-action.service
inactive
```

在 `REPORT.md` 中回答：

1. 已经能证明什么；
2. `accepted_async` 是否代表机器人已经完成挥手；
3. 问题最可能在哪一层；
4. 下一步按什么顺序检查；
5. 当前能否直接执行真实动作，为什么。

请区分事实、推断和待验证项。

## Linux 与 ROS 2 加试

继续完成 [Linux、systemd 与 ROS 2 基础实操](./LINUX_ROS_PRACTICAL.md)，与本题放在同一个 PR 中提交。

## 测试

使用 `pytest` 或 `unittest`，至少覆盖：

- 首次迎宾与重复进入；
- 对话和会议抑制；
- 离场 10 秒及只送客一次；
- 短暂离开后返回；
- 完整离场后再次进入；
- `snapshot()` 隔离。

## 提交

1. Fork 本仓库，创建 `candidate/<Github帐号>` 分支。
2. 提交 `PLAN.md` 并创建 Draft PR。
3. 完成并验证后，将 PR 转为 `Ready for review`。
4. 不要隐藏未完成项，也不要改写已经进入评审的 Git 历史。

最终包含：

```text
robot_application/
tests/
ARCHITECTURE.md
PLAN.md
REPORT.md
AI_USAGE.md
requirements.txt
```

`REPORT.md`：完成情况、测试命令与结果、未完成项、ROS 2 判断题答案。

`AI_USAGE.md`：使用了什么 AI、AI 帮助了什么、如何验证结果。

## 评价重点

- 功能和测试是否正确；
- 模块边界和状态归属是否清楚；
- 是否会根据证据排查问题；
- 是否主动推进、如实反馈并完成闭环；
- 是否正确使用和验证 AI。

请勿查看或复制其他候选人的提交。
