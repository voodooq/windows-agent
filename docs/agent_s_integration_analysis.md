# Agent-S 能力应用到 Windows Agent 的分析与落地方案

## 1. 结论摘要

`Agent-S` 最适合迁移到 `windows_agent` 的，不是整套研究型执行框架，而是以下四类关键能力：

1. **真实语义 grounding 能力**
   - 将当前 `GridGroundingProvider` 升级为可替换的 grounding provider 架构
   - 接入 UI-TARS、Hugging Face Endpoint 或其他视觉 grounding 服务

2. **多步视觉轨迹记忆**
   - 将最近 N 步截图、动作、验证结果纳入 Planner / Reflector / Replanner 的上下文
   - 避免 agent 每步“失忆”

3. **结构化反思与恢复**
   - 将 Reflector 从“日志式总结”升级为“失败诊断 + 恢复建议”模块
   - 为后续重规划提供结构化输入

4. **GUI 与本地代码执行双通道**
   - 对适合代码完成的任务优先使用 Shell / 文件工具
   - 对必须依赖界面的任务使用 Computer Use / Windows UI 工具
   - 建立任务路由而不是一律走 GUI

这四项能力中，**grounding 升级**和**视觉轨迹记忆**是第一优先级。

---

## 2. Agent-S 的核心功能拆解

基于 `Agent-S` README，可归纳出以下核心能力。

### 2.1 Grounding 模型与可替换感知后端
Agent-S 将 GUI 元素定位从主 agent 中解耦，独立配置：

- `ground_provider`
- `ground_url`
- `ground_model`
- `grounding_width`
- `grounding_height`

这使得 grounding 能力可以替换，不绑定某一种实现。

### 2.2 截图轨迹驱动的多步推理
Agent-S S3 支持保留多步视觉轨迹，核心点包括：

- `max_trajectory_length`
- 多轮截图上下文保留
- reflection agent 辅助 worker agent

这意味着 agent 并非只看当前截图，而是会参考历史动作链路。

### 2.3 Reflection / 多代理协作
Agent-S 强调：

- 主执行 agent
- grounding agent
- reflection agent

反思不是单纯写日志，而是参与下一步动作修正。

### 2.4 本地代码执行环境
Agent-S 提供 `enable_local_env`：

- 可执行 Python / Bash
- 用于数据处理、文件批量操作、代码执行、文本处理等

这让 agent 在 GUI 和 code 两种执行方式之间切换。

### 2.5 行为选优与 Best-of-N
Agent-S S3 通过 Behavior Best-of-N 进一步提升效果：

- 多 rollout
- 候选轨迹选优
- Benchmark 表现显著提升

这类能力更适合后期增强，不建议在 `windows_agent` 第一阶段直接引入完整实现。

---

## 3. Windows Agent 当前能力现状

从 `windows_agent/README.md`、`configs/default.yaml`、`docs/implementation_plan_full_control.md` 看，当前项目已经具备较完整的闭环骨架。

### 3.1 已具备的能力
- Plan / Act / Verify / Reflect / Approve 闭环
- 文件工具、Shell 工具、Windows UI 工具
- 视觉 Computer Use 执行链路
- 世界状态记录
- 风险分级与审批机制
- 视觉观察字段：
  - `screenshot_path`
  - `annotated_screenshot_path`
  - `ui_elements`
  - `screen_summary`

### 3.2 当前主要短板
- grounding 仍然是网格化近似，不是语义级 UI 定位
- Planner 尚未真正消费截图和视觉轨迹上下文
- Visual Verifier 仍偏像素差异验证
- Reflector 还不够结构化
- 缺少 GUI / 代码执行的任务分流策略
- 尚未有轻量候选动作选优机制

### 3.3 关键判断
`windows_agent` 当前缺的不是“系统框架”，而是“感知层、上下文层、纠错层”的升级。  
因此最优路线是：**保留现有 runtime 和治理机制，吸收 Agent-S 的高价值能力模块。**

---

## 4. Agent-S -> Windows Agent 功能映射

| Agent-S 能力 | Windows Agent 当前状态 | 推荐落地方式 | 优先级 |
|---|---|---|---|
| 真实 grounding provider | 仅有 `GridGroundingProvider` | 将 `grounding.py` 抽象为 provider 架构 | P0 |
| grounding 服务外部配置 | 暂无 grounding service 配置 | 在 `default.yaml` 增加 `grounding_provider/url/model/api_key` | P0 |
| 多步视觉轨迹记忆 | 以当前状态为主 | 在 `WorldState` 中保留最近 N 步 trajectory | P0 |
| Reflection agent | 已有 `Reflector` | 结构化输出失败原因与恢复计划 | P1 |
| 本地代码环境 | 已有 shell/files 工具 | 升级为“代码执行子代理”或策略层 | P1 |
| GUI 与代码混合执行 | 具备基础工具但未显式路由 | 在 Planner/Replanner 加任务分流规则 | P1 |
| 多模态主模型直接看图 | 接口预留中 | 将截图上下文接入 planner/verifier | P1 |
| Best-of-N / rollout | 暂无 | 先做轻量候选动作重排 | P2 |
| Benchmark 化评估 | 暂无 | 后续对接 WindowsAgentArena 风格评测 | P2 |

---

## 5. 推荐落地架构

## 5.1 Grounding 层升级

### 当前结构
- `app/computer_use/screen.py`
- `app/computer_use/grounding.py`
- `app/computer_use/controller.py`
- `app/computer_use/visual_verifier.py`

### 推荐改造
将 `grounding.py` 改造成 provider 抽象，例如：

- `BaseGroundingProvider`
- `GridGroundingProvider`
- `UITarsGroundingProvider`
- `HttpGroundingProvider`

### 推荐配置扩展
```yaml
runtime:
  computer_use:
    enable_visual_observation: true
    enable_tools: true
    grounding_provider: "grid"   # grid | ui_tars | custom_http
    grounding_model: ""
    grounding_url: ""
    grounding_api_key_env: "GROUNDING_API_KEY"
    grounding_width: 1920
    grounding_height: 1080
    grounding_columns: 4
    grounding_rows: 3
    pause_sec: 0.1
```

### 价值
- 从“点击区域”升级为“点击语义元素”
- 大幅提升 GUI 任务成功率
- 为后续多模态 Planner 奠定基础

---

## 5.2 视觉轨迹记忆升级

### Agent-S 启发
- `max_trajectory_length`
- 多轮截图历史
- reflection agent 可参考上下文

### 推荐改造
在 `WorldState` 或独立状态结构中记录最近 N 步：

- step_id
- screenshot_path
- annotated_screenshot_path
- screen_summary
- ui_elements
- planned_action
- executed_tool
- verification_result
- reflection_result

### 供以下模块消费
- `planner.py`
- `reflector.py`
- `replanner.py`
- `verifier.py`

### 建议策略
- 默认保留最近 5~8 步
- 超出长度后做 sliding window 裁剪
- 对历史截图只保留摘要字段，必要时再加载原图

### 价值
- 减少重复动作
- 增强失败恢复能力
- 支持真正多步 GUI 任务

---

## 5.3 Reflector 结构化升级

### 当前问题
反思如果只是文本总结，难以被 Replanner 可靠消费。

### 推荐输出格式
```json
{
  "failure_type": "wrong_target",
  "reason": "clicked non-interactive region",
  "evidence": "screen did not change after click",
  "recovery_plan": "re-ground the screen and target the search box in the upper right",
  "tool_hint": "ground_screen",
  "confidence": 0.82
}
```

### 应用位置
- `app/runtime/reflector.py`
- `app/runtime/replanner.py`
- `app/schemas/reflection.py`

### 价值
- 让反思成为执行链的一部分
- 提高自动恢复效果
- 便于日志统计和失败模式聚类

---

## 5.4 GUI / 代码执行双通道策略

### Agent-S 启发
本地代码环境适合以下任务：

- 批量文件处理
- 数据整理
- 文本替换
- 自动生成脚本
- 系统级批处理

### Windows Agent 当前条件
项目已经具备：

- `app/tools/files.py`
- `app/tools/shell.py`

所以不需要照搬 Agent-S 的 `exec(action[0])` 模式，而应在现有 ToolRegistry 之上增加策略路由。

### 推荐策略
当任务属于以下类型时优先走代码/命令：

- 文件批量操作
- 日志搜索和处理
- CSV / JSON 数据转换
- 文本替换和生成
- 开发辅助任务

当任务属于以下类型时优先走 GUI：

- 桌面软件交互
- 系统设置导航
- 登录流程
- 浏览器页面点击
- 可视元素选择

### 价值
- 避免低效率 GUI 重复点击
- 更贴合真实生产任务
- 增强任务完成速度与稳定性

---

## 5.5 Verifier 升级方向

### 当前情况
`visual_verifier.py` 主要基于前后截图差异。

### 推荐升级路径
第一阶段：
- 保留像素差异验证
- 叠加 screen summary / ui_elements 对比

第二阶段：
- 使用多模态模型输入：
  - 目标
  - 动作
  - 前图
  - 后图
- 让 verifier 输出是否成功及原因

### 价值
- 避免“画面有变化但任务没完成”
- 提高复杂交互任务的验证准确率

---

## 6. 不建议直接照搬的部分

### 6.1 不建议直接使用 `exec(action[0])`
Agent-S 示例中的研究型执行方式不适合 `windows_agent`，因为当前项目已经有：

- `ToolRegistry`
- 审批流
- 风险分级
- 白名单
- 世界状态
- 安全控制

正确做法应该是：

- 让模型输出结构化 action
- 映射到既有工具体系
- 保留审批和风险控制

### 6.2 不建议为追求“完全控制”移除治理机制
`windows_agent/docs/implementation_plan_full_control.md` 提到放开：

- 全盘访问
- 危险命令拦截
- 审批限制
- 应用白名单

这类改造虽然有助于“完全控制”，但如果结合 Agent-S 风格能力一起放开，会放大风险。  
更稳妥的策略是：

- 优先接入 grounding / trajectory / reflection
- 保留高风险动作审批
- 对本地代码环境单独加开关
- 建议沙箱运行

### 6.3 不建议一开始就实现完整 Best-of-N
Best-of-N 工程复杂度较高，涉及：

- 多候选轨迹执行
- 候选评分
- 多步结果回溯
- 成本控制

更建议先实现轻量候选动作机制，再逐步增强。

---

## 7. 推荐实施顺序

## Phase 0：最小高收益改造
目标：不推翻架构，先提升 GUI 成功率

1. 抽象 grounding provider 接口
2. 保留 `GridGroundingProvider` 作为 fallback
3. 增加外部 grounding endpoint 配置
4. 在 `WorldState` 中记录最近 N 步轨迹
5. 更新 `planner_system.txt`，明确优先使用视觉工具链

### 预期收益
- GUI 操作更稳定
- 为后续接入多模态能力打基础

---

## Phase 1：让闭环真正会看、会记、会纠错
1. Planner 接入截图摘要与轨迹历史
2. Reflector 输出结构化失败诊断
3. Replanner 基于失败类型选择恢复策略
4. Verifier 升级为视觉 + 目标语义联合判断

### 预期收益
- 显著增强多步任务鲁棒性
- 减少错误重复与死循环

---

## Phase 2：引入代码执行子代理
1. 新增代码执行模式开关
2. 建立任务路由规则
3. 将 shell/files 提升为策略层能力
4. 审批与沙箱机制继续保留

### 预期收益
- 提升文件与系统任务效率
- 降低对 GUI 操作的过度依赖

---

## Phase 3：高级优化
1. 候选动作生成与排序
2. 轻量 rollout / retry 策略
3. Best-of-N
4. WindowsAgentArena 风格评测
5. 多分辨率、单显示器约束适配优化

### 预期收益
- 向 Agent-S 风格 benchmark 能力靠拢
- 更适合复杂开放环境

---

## 8. 建议优先改造的文件

### P0
- `windows_agent/app/computer_use/grounding.py`
- `windows_agent/configs/default.yaml`
- `windows_agent/app/state/world_state_store.py`
- `windows_agent/app/prompts/planner_system.txt`

### P1
- `windows_agent/app/runtime/planner.py`
- `windows_agent/app/runtime/reflector.py`
- `windows_agent/app/runtime/replanner.py`
- `windows_agent/app/runtime/verifier.py`
- `windows_agent/app/computer_use/visual_verifier.py`

### P2
- `windows_agent/app/tools/registry.py`
- `windows_agent/app/runtime/executor.py`
- `windows_agent/app/schemas/reflection.py`

---

## 9. 最终建议

如果目标是让 `windows_agent` 真正吸收 `Agent-S` 的价值，最佳路线不是“移植 Agent-S”，而是：

**在现有 Plan-Act-Verify-Reflect-Approve 架构中，分阶段吸收 Agent-S 的 grounding、trajectory、reflection、local-env 四项关键能力。**

这条路线有四个优势：

1. **复用现有工程骨架**
2. **保留安全与审批治理**
3. **支持渐进式演进**
4. **更适合 Windows 桌面个人 agent 场景**

---

## 10. 建议的下一步实现任务

建议按以下顺序立项：

1. grounding provider 抽象与配置化
2. WorldState 增加 recent trajectory
3. Planner prompt 接入视觉轨迹
4. Reflector 结构化输出
5. Verifier 多模态升级
6. GUI / code 双通道路由
7. 轻量候选动作选优

完成前四项后，`windows_agent` 就会明显从“视觉 MVP”向“实用型 computer-use agent”进化。