# 发现侧沙箱工作树（sandbox_root）

这是 Discovery / Experiment / Falsification / Physics Auditor 四类 Agent 的**唯一**
可读写区。目录内不存在 C 锁定区目标值，也不存在全域原始数据。

- `inputs/`：A 发现区、B 开发验证区的开放数据，以及硬约束、数据字典、无方向预设。
- `work/`：Agent 运行时产物（不参与冻结）。

越界访问（保险库、`data/` 全域数据、`stage01_protocol/locked/`、平台报告）由
`sandbox/access_guard.py` 在运行时拒绝，并写入 append-only 日志。
