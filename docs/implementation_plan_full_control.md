# Implementation Plan - Windows Agent 完全控制权开启

## 1. 背景
用户希望基于最新大模型（如描述中的 GPT-5.4/Claude 4.6 概念）赋予 Windows Agent 对电脑的“完全控制权”。这需要解除现有架构中的安全过滤、白名单及人工审批机制。

## 2. 修改目标
- **文件系统**：允许访问 `C:\` 全盘。
- **命令执行**：移除对 `del`, `format`, `rm -rf` 等高危命令的拦截。
- **自动审批**：移除所有键鼠与命令执行工具的人工审批。
- **白名单**：解除应用程序启动限制。

## 3. 具体变更方案
### 3.1 修改 `configs/default.yaml`
- `runtime.approval_policy.always_require_for_tools`: 设置为空数组 `[]`。
- `security.allowed_roots`: 修改为 `["C:\\"]`。
- `security.blocked_commands`: 设置为空数组 `[]`。
- `security.allowed_apps`: 设置为 `["*"]` 或包含常用路径以允许任意程序运行。

## 4. 安全说明
**警告**：此配置将导致 AI 具备破坏系统的能力。建议仅在沙箱或专属虚拟机中执行上述变更。

## 5. 验收标准
1. 修改后的配置文件语法正确（YAML 格式）。
2. Agent 能够直接执行原本被拦截的命令（如 `del`）。
3. 执行键鼠操作时不再需要用户手动点击确认。
