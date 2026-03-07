# Windows Agent

一个面向 Windows 桌面环境的个人 Agent MVP，具备规划（Plan）、执行（Act）、验证（Verify）、反思（Reflect）与审批（Approve）闭环。当前版本支持文件工具、Shell 工具、传统 Windows UI 自动化，以及新增的视觉驱动 Computer Use 执行链路。

## 核心能力

- 目标驱动：将自然语言目标拆分为步骤化计划
- 工具执行：调用文件、Shell、Windows UI、视觉 Computer Use 工具
- 观察与验证：结合窗口状态、文件状态、截图、视觉差异进行验证
- 审批流：对中高风险动作触发人工审批
- 记忆与复盘：沉淀任务执行记录、反思结果与坏态恢复信息

## 新增：Plan-Action-Reflection 视觉控制架构

新版引入了一个面向原生 Computer Use 的最小可运行架构，用来替代纯句柄/纯坐标脚本的脆弱控制方式。

### 1. Vision & Grounding Layer

- `app/computer_use/screen.py`
  - 负责桌面截图采集
- `app/computer_use/grounding.py`
  - 负责将截图转换为带编号框的可交互区域
  - 当前默认实现为网格化 `GridGroundingProvider`
  - 后续可平滑替换为 OmniParser 等真实 grounding 引擎
- `app/computer_use/controller.py`
  - 将 `box_id -> center point` 转换为实际鼠标/键盘动作
- `app/computer_use/visual_verifier.py`
  - 基于动作前后截图差异做视觉验证

### 2. Multi-Agent Runtime Mapping

现有运行时中的角色映射如下：

- `Planner` / `GoalFactory` / `Replanner`
  - 对应 Planning Agent
- `Executor` + `ToolRegistry`
  - 对应 Action Agent
- `Observer` + `Verifier` + `Reflector`
  - 对应 Reflection / Verification Agent

### 3. Model & API Layer

- `app/llm/openai_compatible.py`
  - 保留 chat completions 兼容路径
  - 新增 `responses` API 预留开关
  - 新增 `chat_multimodal_json()` 接口，支持后续接入截图输入
- `app/llm/base.py`
  - 提供统一多模态接口抽象

### 4. Safety & Governance Layer

- 所有高风险工具仍受审批流控制
- 新增视觉动作工具默认纳入高风险审批
- 保留坏态分析与恢复建议
- 建议将真正高风险 Shell 操作放入沙箱环境执行

## 视觉 Computer Use 工具

当 `configs/default.yaml` 中开启 `runtime.computer_use.enable_tools: true` 后，会注册以下工具：

- `capture_screen`
- `ground_screen`
- `click_box`
- `move_to_box`
- `computer_type_text`
- `computer_press_keys`
- `computer_scroll`

同时当 `runtime.computer_use.enable_visual_observation: true` 时：

- `Observer` 会自动截图
- `WorldState` 会写入：
  - `screenshot_path`
  - `annotated_screenshot_path`
  - `screenshot_metadata`
  - `ui_elements`
  - `screen_summary`

## 配置说明

`configs/default.yaml` 新增关键配置：

```yaml
llm:
  use_responses_api: false

runtime:
  computer_use:
    enable_visual_observation: true
    enable_tools: true
    grounding_columns: 4
    grounding_rows: 3
    pause_sec: 0.1
```

### 推荐迁移顺序

1. 先启用 `capture_screen + ground_screen`，观察截图与框选效果
2. 再启用 `click_box / move_to_box`，验证基础视觉交互
3. 最后将 Planner 提示词升级为显式使用视觉工具链
4. 若需要更高精度 UI 定位，将 `GridGroundingProvider` 替换为 OmniParser

## 当前实现边界

当前版本是一个 **MVP 级视觉控制骨架**，重点在于让现有架构平滑演进，而不是一次性完成所有前沿能力。当前限制包括：

- grounding 仍为网格化近似，不是真正语义级 UI 检测
- 多模态 LLM 接口已预留，但 Planner 尚未直接消费截图上下文
- 视觉验证当前以像素差异为主，尚未接入模型级视觉判断
- 尚未加入滑动窗口视觉记忆压缩与工具搜索裁剪

## 下一步建议

- 将 Planner prompt 升级为视觉工具优先策略
- 为 `ground_screen` 接入 OmniParser 或 DETR 类 UI grounding 模型
- 将 `VisualVerifier` 升级为“前后截图 + 目标描述”的多模态判定器
- 在 UI 面板中展示截图、框选结果与审批态
- 为历史截图与动作记录增加 sliding window 裁剪策略

## 安装

```bash
pip install -r requirements.txt
```

## 运行

```bash
python -m app.main
```
