# Windows Agent

一个面向 Windows 桌面环境的个人 Agent，具备规划（Plan）、执行（Act）、验证（Verify）、反思（Reflect）与审批（Approve）闭环。

**新版本：深度集成 Agent-S 风格的 Computer Use 能力。**

## 核心架构演进 (Powered by Agent-S Insights)

本项目已吸收 `Agent-S` 的核心设计理念，在保持原有治理架构的同时，实现了感知、记忆与执行效率的飞跃：

### 1. 感知层：Grounding Provider 抽象化
- **灵活性**：不再绑定单一的网格识别。通过 `BaseGroundingProvider` 接口，支持平滑切换 `GridGrounding`、`UI-TARS`、或外部 HTTP Grounding 服务。
- **语义化**：支持从“坐标点击”向“语义元素点击”进化。

### 2. 记忆层：视觉轨迹记忆 (Visual Trajectories)
- **多步意识**：在 `WorldState` 中引入 `recent_trajectories`，保留最近 5-8 步的截图、动作及结果。
- **防止失忆**：Agent 在规划时会参考历史视觉轨迹，有效避免在复杂 UI 下出现死循环或重复错误。

### 3. 反思层：结构化诊断与纠错
- **结构化输出**：`Reflector` 能够输出包含 `failure_type` (如 `wrong_target`, `stale_ui`) 和 `recovery_plan` 的 JSON 诊断结论。
- **多模态验证**：`VisualVerifier` 结合模型能力，比对“期望结果”与“实际画面语义”，提供比像素差异更可靠的验证得分。

### 4. 执行层：双通道路由与 Best-of-N
- **双通道路由**：Planner 优先选择 **Code Channel** (File/Shell) 处理数据与文件任务，仅在必要时切入 **GUI Channel**。
- **Best-of-N 选优**：引入 `ActionScorer`，支持对多个候选动作（Candidates）进行打分选优，大幅提升高歧义环境下的决策准确率。

## 核心工具集

### 视觉 Computer Use 工具
- `capture_screen`: 桌面采集
- `ground_screen`: 元素定位/网格标注
- `click_box` / `move_to_box`: 视觉交互
- `computer_type_text` / `computer_press_keys`: 键盘录入

### 后端/命令工具
- `write_text` / `read_text`: 文件读写
- `move_file` / `create_dir`: 文件管理
- `run_command`: 系统命令执行

## 配置说明

在 `configs/default.yaml` 中进行核心配置：

```yaml
runtime:
  computer_use:
    enable_visual_observation: true
    enable_tools: true
    grounding_provider: "grid"   # 可选: grid | ui_tars | custom_http
    grounding_columns: 4
    grounding_rows: 3
    pause_sec: 0.1
```

## 安装与运行

```bash
# 安装依赖
pip install -r requirements.txt

# 运行 CLI
python -m app.main "帮我整理桌面上的所有图片到 'Images' 文件夹"

# 运行 UI (实验性)
python app/ui_main.py
```

## 项目分层
- `app/runtime/`: 核心大脑 (Planner, Executor, Reflector, Scorer)
- `app/computer_use/`: 视觉感知与控制层
- `app/state/`: 状态存储与世界模型
- `app/schemas/`: 结构化数据定义

## 开发者规则
本项目遵循严格的开发规范，详见 `docs/` 下的相关文档。
- **所有自动生成的代码必须符合 Pydantic 类型约束**。
- **安全第一**：高风险动作必须获取用户审批。
