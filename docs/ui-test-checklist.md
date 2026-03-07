# UI 侧边栏启动与测试清单

本文档用于验证 Windows Agent 的右侧侧边栏 UI 是否已正确接入当前自治运行时，并具备以下能力：

- 打开与显示窗口
- 输入自然语言指令
- 创建并显示 goal
- 控制 daemon 启停
- 展示 recent goals / events / logs / state
- 联动 watcher / world state / event audit
- 在失败场景下保持可观测与可恢复

---

## 1. 测试范围

本测试文档覆盖以下模块的联动验证：

- UI 右侧侧边栏
- AgentController（如已实现）
- daemon
- GoalManager
- WorldStateStore
- EventLogger
- watcher / event bus / scheduler
- planner / executor / verifier / replanner

---

## 2. 前置条件

启动测试前，请确保以下条件成立：

### 2.1 依赖已安装

```bash
pip install -r requirements.txt
```

如果 UI 基于 PySide6，还需确认：

```bash
pip show PySide6
```

---

### 2.2 已配置 `.env`

确保存在：

- `OPENAI_API_KEY`
- `OPENAI_BASE_URL`
- `OPENAI_MODEL`

---

### 2.3 目录已创建

```bash
mkdir data
mkdir workspace
mkdir workspace\inbox
mkdir workspace\archive
```

---

### 2.4 watcher 已启用

检查 `configs/default.yaml`：

```yaml
watchers:
  file_watch:
    enabled: true
    paths:
      - "./workspace/inbox"
```

---

## 3. 启动 UI

根据你的项目入口选择一种方式：

```bash
python app/ui_launcher.py
```

或：

```bash
python -m app.ui_launcher
```

---

## 4. UI 启动基础检查

### 测试 4.1：窗口是否能正常打开

预期结果：

- 右侧侧边栏窗口出现
- UI 不闪退
- 可以看到输入框、按钮和状态区域

验收项：

- [ ] 窗口能打开
- [ ] 无明显报错
- [ ] 无立即闪退
- [ ] 窗口可关闭

---

### 测试 4.2：窗口布局是否完整

检查是否至少包含：

- 状态栏
- 输入框
- 发送按钮
- recent goals 区域
- recent events 区域
- logs / output 区域（如已实现）
- daemon 控制按钮（如已实现）

验收项：

- [ ] 输入框可见
- [ ] 发送按钮可见
- [ ] 状态栏可见
- [ ] 列表区域可见
- [ ] 按钮无错位/严重遮挡

---

## 5. UI 基础交互测试

### 测试 5.1：输入框是否可用

在输入框中输入：

```text
测试指令
```

然后删除，再重新输入。

验收项：

- [ ] 可输入中文
- [ ] 可输入英文
- [ ] 可退格删除
- [ ] 不会卡死

---

### 测试 5.2：发送按钮点击测试

输入：

```text
在 workspace 下创建一个 ui_test 目录
```

点击 Send / 提交。

预期结果：

- UI 不报错
- 目标被创建
- 输入框清空或保留合理状态
- UI 提示已提交

验收项：

- [ ] 点击发送不崩溃
- [ ] goal 被提交
- [ ] 有提交反馈

---

### 测试 5.3：刷新按钮测试（如已实现）

点击 Refresh。

预期结果：

- recent goals / events / state 重新加载
- UI 不崩溃

验收项：

- [ ] Refresh 可点击
- [ ] 点击后无异常
- [ ] 列表内容可更新

---

## 6. UI 与 GoalManager 联动测试

### 测试 6.1：通过 UI 提交简单 goal

输入：

```text
在 workspace 下创建一个 panel_test 目录
```

点击发送。

然后检查：

```bash
type data\goals.json
```

预期结果：

- 新增一条 goal
- 文本与 UI 输入一致
- 状态为 `pending` / `active` / `completed`

验收项：

- [ ] `goals.json` 出现新 goal
- [ ] goal 文本一致
- [ ] 状态有变化

---

### 测试 6.2：目标执行结果检查

检查目录：

```bash
dir workspace
```

预期结果：

- 存在 `panel_test`

验收项：

- [ ] 目录成功创建

---

## 7. UI 与 daemon 联动测试

### 测试 7.1：Start Daemon（如已实现按钮）

点击 Start Daemon。

预期结果：

- daemon 启动
- 状态栏显示 running / online
- heartbeat / recent events 开始更新

验收项：

- [ ] 点击后 daemon 启动
- [ ] 状态栏变化正确
- [ ] 不会重复启动多个实例

---

### 测试 7.2：Stop Daemon（如已实现按钮）

点击 Stop Daemon。

预期结果：

- daemon 停止
- watcher 停止响应
- 状态栏显示 stopped / offline

验收项：

- [ ] daemon 真正停止
- [ ] 状态栏变化正确
- [ ] 停止后不再自动处理事件

---

## 8. UI 与 watcher 联动测试

### 测试 8.1：文件事件触发

保持 daemon 运行，在另一个终端执行：

```bash
echo hello from ui test > workspace\inbox\ui_event_test.txt
```

预期结果：

- watcher 检测到新文件
- 事件进入 event bus
- goal factory 做出决策
- 自动创建新 goal
- UI recent events 列表更新
- UI recent goals 列表更新

验收项：

- [ ] UI recent events 出现 file.changed
- [ ] UI recent goals 出现对应 goal
- [ ] daemon 控制台有响应
- [ ] 没有报错

---

### 测试 8.2：核对 `events.jsonl`

```bash
type data\events.jsonl
```

预期应包含：

- `event_id`
- `type=file.changed`
- `accepted`
- `goal_text`
- `debounce_hit`
- `dedupe_hit`

验收项：

- [ ] 有对应事件记录
- [ ] 字段完整
- [ ] UI 与审计数据大体一致

---

### 测试 8.3：核对 `world_state.json`

```bash
type data\world_state.json
```

预期应更新：

- `recent_events`
- `recent_goals`
- `new_files`

验收项：

- [ ] world state 已更新
- [ ] UI 与 world state 基本一致

---

## 9. 去重 / 防抖联动测试

### 测试 9.1：快速重复修改文件

执行：

```bash
echo a>> workspace\inbox\ui_event_test.txt
echo b>> workspace\inbox\ui_event_test.txt
echo c>> workspace\inbox\ui_event_test.txt
```

预期结果：

- 不会创建大量重复 goal
- events 可能多条，但部分会被忽略
- UI recent events 可能显示 ignored / debounce / dedupe 信息（如已实现）

验收项：

- [ ] 没有大量重复 open goal
- [ ] `events.jsonl` 中有 debounce/dedupe 痕迹
- [ ] UI 不会被刷爆

---

### 测试 9.2：核对 open goal 抑制

```bash
type data\goals.json
```

验收项：

- [ ] 没有大量相同 goal_text 的 pending/active 目标

---

## 10. Recent Goals 展示测试

### 测试 10.1：连续创建多个 goal

通过 UI 依次发送：

1. 在 workspace 下创建一个 ui_a1 目录
2. 在 workspace 下创建一个 ui_a2 目录
3. 在 workspace 下创建一个 ui_a3 目录

预期结果：

- Recent Goals 列表有多条记录
- 顺序正确
- 状态可变化

验收项：

- [ ] goals 列表可刷新
- [ ] 至少显示最近 3 条
- [ ] 状态与 `goals.json` 一致或接近一致

---

## 11. Recent Events 展示测试

### 测试 11.1：产生多类事件

进行以下操作：

- 启动 daemon
- 创建新文件
- 提交手动 goal
- 停止 daemon（如支持）

预期结果：

Recent Events 至少可看到部分事件：

- `goal.created`
- `file.changed`
- `system.heartbeat`
- `goal.run_pending`

验收项：

- [ ] recent events 可刷新
- [ ] 新事件能显示
- [ ] 不出现明显重复渲染 bug

---

## 12. 错误与失败展示测试

### 测试 12.1：提交故意失败任务

在 UI 输入：

```text
打开 notepad.exe，然后点击一个不存在的按钮
```

预期结果：

- 任务失败，但 UI 不应卡死
- recent goals / logs 出现失败记录
- 若已接入 replanner，可看到：
  - `recovery_mode`
  - `reasoning_summary`

验收项：

- [ ] UI 不因失败崩溃
- [ ] 可看到失败结果
- [ ] 状态/日志区域有更新

---

## 13. world state 展示联动测试

### 测试 13.1：完整链路状态更新

依次执行：

1. 启动 daemon
2. 放入一个新文件到 `workspace/inbox`
3. 提交一个手动 goal
4. 提交一个故意失败的 goal

然后检查 UI 是否能显示这些状态（如已实现）：

- recent events
- recent goals
- recent failures
- recent tools
- new files
- watched paths

验收项：

- [ ] recent events 更新
- [ ] recent goals 更新
- [ ] recent failures 更新
- [ ] recent tools 更新
- [ ] new files 更新

---

## 14. daemon 重启恢复测试

### 测试 14.1：关闭后重开 UI / daemon

步骤：

1. 启动 UI
2. 启动 daemon
3. 触发几个 goal / events
4. 关闭 UI 或停止 daemon
5. 重新打开 UI / 重启 daemon

预期结果：

- world state 不完全丢失
- recent goals / events 仍可回溯
- watcher 可重新注册
- UI 能重新刷新到最新状态

验收项：

- [ ] 重启后 UI 可正常刷新
- [ ] `world_state.json` 保留近期摘要态
- [ ] daemon 能恢复工作

---

## 15. 最小验收标准

若以下条目全部通过，则可认为 UI 已初步可用：

- [ ] UI 窗口能正常启动
- [ ] 输入框可输入并发送指令
- [ ] UI 可创建 goal
- [ ] `goals.json` 能反映 UI 提交结果
- [ ] daemon 可由 UI 启动/停止（如已实现）
- [ ] watcher 事件能在 UI 中反映
- [ ] recent goals / recent events 可以更新
- [ ] 失败任务不会导致 UI 崩溃
- [ ] `world_state.json` 与 UI 展示基本一致
- [ ] 重复文件修改不会在 UI 中产生大量重复 goal

---

## 16. 调试时重点核对的真实数据源

当 UI 显示异常时，请优先对照以下文件：

### 16.1 goals

```bash
type data\goals.json
```

### 16.2 world state

```bash
type data\world_state.json
```

### 16.3 event audit

```bash
type data\events.jsonl
```

### 16.4 daemon 控制台输出

重点观察：

- heartbeat
- file.changed
- goal.created
- goal.run_pending
- error / failure

---

## 17. 常见问题排查

### 问题 17.1：UI 能打开但提交没反应

检查：

1. UI 是否真的调用了 controller / add_goal
2. `goals.json` 是否有新增记录
3. 点击发送时是否有异常被吞掉
4. daemon 是否在运行

---

### 问题 17.2：UI 列表不刷新

检查：

1. Refresh 是否真正触发读取
2. 列表数据是否来自最新文件
3. 是否存在缓存未更新
4. UI 线程是否被长任务阻塞

---

### 问题 17.3：daemon 已运行但 UI 状态不变

检查：

1. 状态是否由 polling 定时刷新
2. controller 是否正确读取 daemon 状态
3. 是否只是 UI 本地状态未更新

---

### 问题 17.4：文件事件发生了，但 UI 无显示

检查：

1. `events.jsonl` 是否有记录
2. `world_state.json` 是否更新
3. watcher 路径是否正确
4. 是否命中 debounce / dedupe
5. UI 是否只展示 accepted 事件而过滤了 ignored 事件

---

### 问题 17.5：UI 卡顿

检查：

1. 是否在 UI 主线程执行了耗时任务
2. 是否直接阻塞式启动 daemon
3. 是否列表刷新频率过高
4. 是否一次性加载过多事件/goal

---

## 18. 推荐回归测试集

每次修改 UI 后至少回归以下 8 项：

1. UI 启动
2. 输入框发送 goal
3. goals 列表刷新
4. Start daemon
5. Stop daemon
6. watcher 新文件事件
7. debounce / dedupe 抑制
8. 失败任务显示

---