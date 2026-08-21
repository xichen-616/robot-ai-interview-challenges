# Robot AI Application Engineer — Round 1

## 1. 项目目标

完成 GitHub `robot-ai-interview-challenges` 中 Round 1 机器人接待应用任务。

目标是实现一个纯 Python 的机器人接待业务逻辑模块：

- 根据 Event 驱动业务状态变化
- 首次进入时产生迎宾动作和语音
- 对话/会议期间抑制普通迎宾
- 人员离开后开始计时
- 连续离开达到 10 秒后产生一次送客语音
- 短暂离开后重新进入，不产生重复送客
- 完整离场后再次进入，可以重新触发迎宾
- 支持 snapshot() 状态快照
- snapshot 返回值不能修改内部状态
- 业务逻辑不能直接依赖 ROS 2、相机或真实机器人 SDK

---

## 2. 核心设计

采用事件驱动 + 状态机设计。

基本流程：

```text
Event
  ↓
RobotApplication
  ↓
读取当前状态
  ↓
业务规则判断
  ↓
更新内部状态
  ↓
生成 Effect
```

业务层只负责产生 Effect，不直接执行机器人动作。

```text
RobotApplication
      │
      │ Effect
      ▼
Robot Bridge / Adapter
      │
      ▼
ROS 2 / Robot SDK
      │
      ▼
真实机器人
```

---

## 3. 数据模型

题目要求使用：

```python
@dataclass(frozen=True)
class Event:
    event_type: str
    timestamp: float
    person_id: Optional[str] = None
```

以及：

```python
@dataclass(frozen=True)
class Effect:
    effect_type: str
    value: str
    reason: str
```

Event 用于描述外部事件。

Effect 用于描述业务层希望机器人执行的动作或输出。

---

## 4. 建议状态

内部状态至少需要能够表达：

```text
当前是否有人在场
是否已经完成迎宾
是否正在对话
是否正在会议
人员离开时间
是否已经完成本次送客
```

推荐使用明确的状态对象，而不是大量散落的全局变量。

可以采用：

```python
@dataclass
class ConversationState:
    present: bool = False
    greeted: bool = False
    conversation_active: bool = False
    meeting_active: bool = False
    left_at: Optional[float] = None
    departure_sent: bool = False
```

实际实现应以题目原始接口和要求为准。

---

## 5. 核心业务规则

### 5.1 首次进入

当人员进入，并且系统处于 idle 状态：

产生：

```text
ROBOT_ACTION -> wave_hand
SPEECH -> 欢迎光临
```

必须避免重复迎宾。

---

### 5.2 对话/会议抑制

如果人员正在：

```text
conversation
```

或者：

```text
meeting
```

普通迎宾动作应被抑制。

必须保证：

```text
对话/会议期间
不会错误触发普通迎宾
```

---

### 5.3 人员离开

收到人员离开事件：

```text
记录离开时间
```

不要立即发送：

```text
欢迎下次光临
```

必须等待连续离开达到 10 秒。

---

### 5.4 离开达到 10 秒

如果：

```text
current_time - left_at >= 10
```

产生一次：

```text
SPEECH -> 欢迎下次光临
```

并记录：

```text
departure_sent = True
```

防止后续 tick 重复发送。

---

### 5.5 短暂离开

例如：

```text
0s    PERSON_LEFT
5s    PERSON_ENTERED
```

说明人员只是短暂离开。

此时：

- 不应该触发送客
- 清除离开计时
- 恢复在场状态
- 不应该错误产生“欢迎下次光临”

---

### 5.6 完整离场后重新进入

例如：

```text
0s    PERSON_LEFT
10s   TICK
15s   PERSON_ENTERED
```

应该允许新一轮迎宾。

---

## 6. snapshot()

必须提供状态快照。

重要要求：

> 外部修改 snapshot 返回值，不能影响内部状态。

因此不能简单暴露内部可变对象。

应采用：

- defensive copy
- 不可变数据结构
- 或其他等价方案

并通过测试验证。

测试思想：

```text
内部状态
   ↓
snapshot()
   ↓
修改 snapshot
   ↓
再次 snapshot()
   ↓
内部状态仍保持正确
```

---

## 7. 测试要求

至少覆盖：

1. 首次迎宾
2. 重复进入
3. 对话状态抑制迎宾
4. 会议状态抑制迎宾
5. 离场不足 10 秒
6. 离场达到 10 秒
7. 送客只能触发一次
8. 短暂离开后返回
9. 完整离场后再次进入
10. snapshot 隔离
11. 时间边界，例如刚好 10 秒
12. 事件顺序异常时系统行为合理

使用 pytest。

最终运行：

```bash
pytest -q
```

所有测试必须通过。

---

## 8. 架构原则

### 业务层不能依赖：

```text
ROS 2
相机 SDK
机器人 SDK
具体硬件
```

业务层只处理：

```text
Event
State
Effect
```

推荐架构：

```text
                 External Events
                       │
                       ▼
              ┌─────────────────┐
              │ RobotApplication │
              │   Business      │
              │     Logic       │
              └────────┬────────┘
                       │
                     Effect
                       │
                       ▼
              ┌─────────────────┐
              │ Robot Bridge    │
              │ / ROS2 Adapter  │
              └────────┬────────┘
                       │
                       ▼
                 Real Robot
```

---

## 9. ROS 2 日志分析

题目给出的日志中：

```text
app effect_created
type=ROBOT_ACTION
value=wave_hand
```

只能证明业务层产生了挥手 Effect。

看到：

```text
robot_bridge request_submitted
task_id=task-17
action=wave_hand

robot_bridge accepted_async
task_id=task-17
```

只能证明任务已经被异步接受/提交。

不能证明真实机器人已经执行完成。

进一步看到：

```text
Action clients: 1
Action servers: 0
```

说明当前环境中没有发现对应的 Action Server。

同时：

```text
robot-action.service inactive
```

说明相关机器人动作服务没有处于 active 状态。

因此不能直接执行真实机器人动作。

应该继续按照：

```text
业务层
 ↓
Robot Bridge
 ↓
ROS 2 Action Client
 ↓
ROS 2 Action Server
 ↓
robot-action.service
 ↓
真实机器人
```

逐层检查。

---

## 10. 文档要求

最终项目至少包含：

```text
robot_application/
tests/
ARCHITECTURE.md
PLAN.md
REPORT.md
AI_USAGE.md
requirements.txt
```

### PLAN.md

记录：

- 对问题的理解
- 实现计划
- 状态设计
- 测试计划
- 时间安排

### ARCHITECTURE.md

说明：

- 模块职责
- Event → State → Effect
- 为什么业务层不依赖 ROS 2
- 如何扩展 Robot Bridge
- 状态管理方式
- snapshot 隔离设计

### REPORT.md

说明：

- 实现结果
- 测试结果
- ROS 2 日志分析
- accepted_async 的含义
- Action Server 缺失意味着什么
- service inactive 的含义
- 下一步排查顺序
- 为什么不能直接执行真实动作

### AI_USAGE.md

如实记录：

- 使用的 AI 工具
- AI 参与了哪些工作
- 哪些代码/设计由 AI 辅助
- 如何人工检查
- 如何通过测试验证 AI 输出
- 出现问题后如何修改

---

## 11. GitHub 提交要求

最终分支：

```text
candidate/<候选人编号>
```

不要直接修改 main。

提交前检查：

```bash
pytest -q
```

确认：

```text
所有测试通过
文档完整
没有敏感信息
没有 API Key
没有密码
没有无关的大文件
```

最终提交 Pull Request。

---

## 12. 完成标准

最终项目必须做到：

- [ ] 核心业务逻辑正确
- [ ] 状态设计清晰
- [ ] 没有全局可变状态
- [ ] Event / Effect 数据结构符合题目
- [ ] 迎宾逻辑正确
- [ ] 对话/会议抑制正确
- [ ] 10 秒离场逻辑正确
- [ ] 送客只触发一次
- [ ] 短暂离开不会误送客
- [ ] 完整离场后可重新迎宾
- [ ] snapshot 不会泄漏内部状态
- [ ] pytest 测试完整
- [ ] ARCHITECTURE.md 完整
- [ ] PLAN.md 完整
- [ ] REPORT.md 完整
- [ ] AI_USAGE.md 完整
- [ ] requirements.txt 完整
- [ ] ROS 2 分析有证据依据
- [ ] 不直接依赖 ROS 2 / 硬件 SDK
- [ ] Git 分支符合要求
- [ ] 最终可以提交 PR