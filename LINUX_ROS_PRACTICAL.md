# Linux、systemd 与 ROS 2 基础实操

目标：考察能否在 Linux 机器人环境中完成部署、诊断和验证，而不是背命令。

- 不计完成速度；重点看最终结果、验证证据和工程判断。
- 可使用 AI，但必须说明如何检查 AI 给出的命令、配置和结论。
- 只操作自己的测试程序。禁止连接真实机器人，禁止发送真实动作目标。

## 一、基础判断

将答案写入 `LINUX_ROS_REPORT.md`。每题区分：**事实、推断、待验证项、下一步命令**。

### 1. systemd：`active` 是否等于可用

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

回答：

1. 已经能证明什么，不能证明什么；
2. 为什么服务显示 `active`，应用仍可能不可用；
3. 下一步用哪些只读命令定位 `ExecStart`、工作目录、运行用户、Python 环境、子进程和监听端口；
4. 怎样避免无限重启掩盖故障；
5. `enabled`、当前 `active`、用户登录后自启、机器开机即启动分别是什么意思，如何验证。

### 2. Linux 权限

```text
$ ls -l /dev/ttyUSB0
crw-rw---- 1 root dialout 188, 0 /dev/ttyUSB0

$ id robot
uid=1001(robot) gid=1001(robot) groups=1001(robot)

$ journalctl --user -u robot-reception.service -n 2 --no-pager
PermissionError: [Errno 13] Permission denied: '/dev/ttyUSB0'
```

回答最可能原因、安全修复方式和验证方法。说明为什么不应使用 `chmod 777`。

### 3. ROS 2 发现不等于数据正常

```text
$ ros2 topic list -t
/camera/status [std_msgs/msg/String]

$ ros2 topic info -v /camera/status
Publisher count: 1
Subscription count: 1

$ timeout 5s ros2 topic echo --once /camera/status
# 超时，无消息
```

回答：还缺少哪些证据，如何区分“发现了端点”“正在发布新数据”和“业务真的消费成功”。

### 4. ROS 2 QoS

```text
Publisher: BEST_EFFORT + VOLATILE
Subscriber: RELIABLE + TRANSIENT_LOCAL
```

判断是否可能正常通信，给出验证命令和修复原则。不要只写“QoS 不匹配”。

### 5. ROS 2 Action

结合主任务中的 `accepted_async`、`Action servers: 0` 和 `STAND`，说明以下状态为什么必须分别验证：

1. 应用已创建动作意图；
2. bridge 已接收请求；
3. Action Server 已接受 Goal；
4. Action Result 成功；
5. 机器人真实完成动作。

## 二、Linux 与 systemd 实操

实现一个只用于本题的本地健康服务，并交给 `systemd --user` 管理。

### 交付文件

```text
ops/health_server.py
ops/systemd/robot-reception.service
ops/install_user_service.sh
ops/uninstall_user_service.sh
ops/linux_diagnose.sh
tests/test_health_server.py
```

### 要求

1. `health_server.py` 仅监听 `127.0.0.1:18080`，`GET /healthz` 返回可机器判断的健康结果。
2. service 必须明确启动命令、工作目录和环境来源，日志进入 journald。
3. `[Install]` 必须配置正确的 `WantedBy`；安装脚本执行 `systemctl --user enable --now`，证明服务能够自动启动，而不是只在当前 shell 中运行。
4. 使用 `Restart=on-failure`，并设置合理的重启间隔和启动频率限制；不得无限快速重启。
5. 安装脚本使用 `systemctl --user`，可重复执行，不使用 `sudo`，不覆盖无关文件。
6. 必须说明：普通 user service 通常是“用户登录后自启”。如果声称“机器开机、无人登录也会启动”，必须额外证明 `Linger=yes`，或说明如何改为受控的 system service；不得混淆两者。
7. 卸载脚本只删除本题安装的用户服务，重复执行也应安全。
8. `linux_diagnose.sh <service-name>` 只做读取，至少收集：
   - `is-enabled`、`is-active`、`MainPID`、`ExecMainStatus`、`NRestarts`；
   - 主进程的 PID、PPID、用户、状态、运行时长和命令行；
   - 可读取时的 `/proc/<pid>/cwd` 和 `/proc/<pid>/exe`；
   - 监听端口、最近 100 行日志和 `/healthz` 结果。
9. 可选命令不存在或单项检查失败时，诊断脚本要给出明确状态并继续，不能静默退出。
10. 不读取或输出进程完整环境变量、令牌、密码等敏感信息。

### 验收证据

在 `LINUX_ROS_REPORT.md` 中贴出关键输出并解释：

```bash
systemd-analyze --user verify ops/systemd/robot-reception.service
systemctl --user is-enabled robot-reception.service
systemctl --user is-active robot-reception.service
systemctl --user show robot-reception.service -p MainPID -p ExecMainStatus -p NRestarts
loginctl show-user "$USER" -p Linger
curl -fsS http://127.0.0.1:18080/healthz
journalctl --user -u robot-reception.service -n 50 --no-pager
pytest -q
```

再使用你自己设计的可控故障，让进程非零退出一次，证明服务会按策略恢复且不会无限快速重启。只允许操作本题服务。

如果环境没有运行 systemd，至少提交 `systemd-analyze verify`、自动化测试结果，并如实说明尚未验证什么；不要伪造运行结果。

## 三、ROS 2 实操

使用 ROS 2 Humble 和标准消息创建 Python 包：

```text
ros2_ws/src/effect_router/
```

### 节点行为

- 订阅 `/reception/effects`，类型为 `std_msgs/msg/String`，内容为 JSON。
- 只接受：

```json
{"effect_type":"ROBOT_ACTION","value":"wave_hand","reason":"first_entry"}
```

- 合法输入转换后发布到 `/robot/action_requests`，类型仍为 `std_msgs/msg/String`。
- malformed JSON、未知 `effect_type`、未知动作不得发布请求，节点不能崩溃，并给出可诊断日志。
- 只允许 `wave_hand`；不得调用真实 Action、Service 或硬件 SDK。
- 解析与校验逻辑应与 ROS 节点壳分离，能够独立单元测试。

### ROS 2 诊断脚本

提交 `ops/ros2_diagnose.sh`，使用带超时的只读命令收集：

```text
ROS_DISTRO、ROS_DOMAIN_ID、RMW_IMPLEMENTATION
ros2 node list
ros2 topic list -t
ros2 service list -t
ros2 action list -t
ros2 topic info -v /reception/effects
ros2 topic info -v /robot/action_requests
一次有界的 topic echo
```

脚本不得执行 `ros2 service call`、`ros2 action send_goal`、重启服务或修改机器人状态。

### 验收证据

```bash
cd ros2_ws
colcon build --symlink-install
source install/setup.bash
colcon test --event-handlers console_direct+
colcon test-result --verbose
```

证明以下情况：合法输入只产生一次请求；非法 JSON、未知动作不产生请求；节点在错误输入后仍能处理下一条合法输入。

## 四、提交与评价

新增内容至少包括：

```text
LINUX_ROS_REPORT.md
ops/
ros2_ws/src/effect_router/
tests/
```

评价重点：

- systemd 服务能否安装、自启、恢复、卸载并被独立验证，是否准确区分登录自启与无人登录的开机自启；
- Linux/ROS 2 诊断是否基于证据，而不是看到 `active` 或端点就下结论；
- ROS 2 适配层是否保持业务、ROS 和真实硬件边界；
- 脚本是否安全、幂等、可失败、可解释；
- AI 生成内容是否经过实际验证，报告是否诚实；
- 是否有克制、清楚、可维护的工程品味。
