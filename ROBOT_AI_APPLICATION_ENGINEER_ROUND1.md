# 机器人 AI 应用工程师｜第一轮实战

- 开卷，允许使用 AI。
- 不按完成速度评分，只看结果、验证和判断。
- Fork 本仓库，通过 Pull Request 提交。
- 禁止连接真实机器人或发送真实动作。

## 1. 应用逻辑

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

```python
event_type: str
timestamp: float
person_id: str | None
```

### 规则

1. 空闲时有人进入：输出 `wave_hand` 和“欢迎光临”。
2. 同一次持续在场期间不重复迎宾。
3. 对话或会议期间不输出迎宾、送客或动作，结束后也不补发。
4. 人员离开满 10 秒后，由 `TICK` 触发送客；同一次离场只送一次。
5. 离开不足 10 秒又返回：不送客，也不重复迎宾。
6. 完成离场确认后，再次进入视为新的接待。

必须满足：

| 时间 | 事件 | 输出 |
|---:|---|---|
| 0 | `PERSON_ENTERED` | 挥手 + 欢迎 |
| 1 | `PERSON_ENTERED` | 无 |
| 2 | `CONVERSATION_STARTED` | 无 |
| 3 | `PERSON_ENTERED` | 无 |
| 4 | `CONVERSATION_ENDED` | 无 |
| 5 | `PERSON_LEFT` | 无 |
| 14 | `TICK` | 无 |
| 15 | `TICK` | 送客一次 |
| 16 | `TICK` | 无 |
| 20 | `PERSON_ENTERED` | 挥手 + 欢迎 |

### 公共接口

保留以下导入路径，内部结构自行设计。

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

- `handle_event()` 只返回本次事件产生的效果。
- 外部修改 `snapshot()` 不得影响内部状态。
- 不使用全局可变状态。
- 业务模块不直接依赖 ROS 2 或硬件 SDK。
- 测试覆盖上述规则和状态隔离。

## 2. Linux 与 systemd

### 判断题

```text
$ systemctl --user is-enabled robot-reception.service
enabled

$ systemctl --user is-active robot-reception.service
active

$ systemctl --user show robot-reception.service \
    -p MainPID -p ExecMainStatus -p NRestarts
MainPID=4210
ExecMainStatus=0
NRestarts=7

$ ss -lntp | grep 18080
# 无输出

$ journalctl --user -u robot-reception.service -n 4 --no-pager
ModuleNotFoundError: No module named 'robot_application'
worker exited, retrying
ModuleNotFoundError: No module named 'robot_application'
worker exited, retrying
```

在 `REPORT.md` 中回答：

1. 已经能证明什么，不能证明什么；
2. 为什么 `active` 不代表应用可用；
3. 下一步如何检查启动命令、工作目录、Python 环境、进程、端口和日志；
4. 如何避免无限重启掩盖故障；
5. `enabled`、登录后自启、无人登录的开机自启有什么区别。

### 实操

提交：

```text
ops/health_server.py
ops/systemd/robot-reception.service
ops/install_user_service.sh
ops/linux_diagnose.sh
```

要求：

1. 健康服务监听 `127.0.0.1:18080`，`GET /healthz` 返回机器可判断的结果。
2. service 明确 `ExecStart`、`WorkingDirectory`、环境来源和 `WantedBy`，日志进入 journald。
3. 使用 `Restart=on-failure`，设置重启间隔和启动频率限制。
4. 安装脚本可重复执行，使用 `systemctl --user enable --now`，不覆盖无关文件。
5. 普通 user service 通常是登录后自启。若声称无人登录也会启动，必须证明 `Linger=yes`，或说明如何改为 system service。
6. `linux_diagnose.sh` 只读输出服务状态、PID、用户、工作目录、可执行文件、端口、最近日志和健康检查。
7. 单项检查失败时继续执行并明确报告；不得输出密码、令牌或完整环境变量。

报告中给出实际命令和关键结果，并用一次可控的非零退出验证恢复策略。只操作本题服务；无法运行 systemd 时如实说明未验证项。

## 3. ROS 2

### 判断题

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
5. 为什么“发现 ROS 端点”“收到新数据”“Action 成功”“真实动作完成”必须分别验证；
6. 当前能否执行真实动作。

再说明以下 QoS 是否兼容，以及如何验证：

```text
Publisher: BEST_EFFORT + VOLATILE
Subscriber: RELIABLE + TRANSIENT_LOCAL
```

### 实操

使用 ROS 2 Humble 创建 Python 包：

```text
ros2_ws/src/effect_router/
```

节点要求：

- 订阅 `/reception/effects`，类型 `std_msgs/msg/String`，内容为 JSON。
- 只允许 `ROBOT_ACTION + wave_hand`，转换后发布到 `/robot/action_requests`。
- 非法 JSON、未知类型或动作不得发布，节点不能崩溃。
- 解析和校验逻辑与 ROS 节点壳分离并有单元测试。
- 不调用真实 Action、Service 或硬件 SDK。

提交 `ops/ros2_diagnose.sh`，用有界、只读命令输出：ROS 环境、节点、Topic、Service、Action、两个 Topic 的详细端点信息，以及一次有界的消息读取。脚本不得发送 Goal、调用 Service、重启服务或修改机器人状态。

报告中给出 `colcon build`、`colcon test` 和以下验证结果：

- 合法输入只产生一次请求；
- 非法 JSON 和未知动作不产生请求；
- 错误输入后，节点仍能处理下一条合法输入。

## 4. 架构与提交

`ARCHITECTURE.md` 简要说明：

1. 模块和依赖方向；
2. 状态由谁拥有；
3. 业务、ROS 2 和硬件的边界；
4. 如何扩展 VIP、RAG 和导航而不形成大类。

最终至少包含：

```text
robot_application/
ros2_ws/src/effect_router/
ops/
tests/
ARCHITECTURE.md
REPORT.md
AI_USAGE.md
requirements.txt
```

`REPORT.md`：完成情况、判断题答案、测试命令与结果、故障验证、未完成和未验证项。

`AI_USAGE.md`：使用了什么 AI、AI 生成了什么、你如何验证和修正结果。

## 评价重点

- 功能和实操结果是否正确；
- 是否用测试、日志和命令证明结果；
- systemd 自启、恢复和健康判断是否可靠；
- ROS 2 与真实硬件边界是否安全；
- 模块设计是否简单、清楚、可维护；
- 是否能识别并修正 AI 生成的错误。

请勿查看或复制其他候选人的提交。
