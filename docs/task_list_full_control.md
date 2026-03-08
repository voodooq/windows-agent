# Task List - Windows Agent 完全控制权开启

## 任务列表

### 阶段 1：配置文件修改
- [ ] **任务 1.1**: 备份当前的 `configs/default.yaml` 文件 -> `docs/default.yaml.bak`。
- [ ] **任务 1.2**: 修改 `security.allowed_roots` 为 `["C:\\"]`，允许全盘访问。
- [ ] **任务 1.3**: 清空 `security.blocked_commands` 列表，允许执行任意命令。
- [ ] **任务 1.4**: 修改 `security.allowed_apps` 为通配符或扩展列表。
- [ ] **任务 1.5**: 清空 `runtime.approval_policy.always_require_for_tools`，解除强制人工审批。

### 阶段 2：验证与测试
- [ ] **任务 2.1**: 使用静态解析工具检查 YAML 格式是否正确。
- [ ] **任务 2.2**: （可选）模拟启动 Agent 观察配置加载日志是否报错。
