# S02.3 五 Agent 骨架与权限

版本 stage02-agents-v1。状态 **OK**。

| Agent | 沙箱内 | 可访问 | 禁访问 |
|---|---|---|---|
| Discovery Agent | 是 | A 发现区（sandbox_root/inputs/zone_A_open.csv） | B 开发验证区目标（调参用）；C 锁定区任何形式（含密文与密钥）；全域原始数据 data/（含全城 LST 栅格与全表 CSV）；旧论文结论/相关矩阵 |
| Experiment Agent | 是 | A 发现区、B 开发验证区 | C 锁定区任何形式；全域原始数据 data/ |
| Falsification Agent | 是 | A 发现区、B 开发验证区、分区掩膜（Grid_ID→row/col/zone） | C 锁定区任何形式；全域原始数据 data/ |
| Physics Auditor | 是 | hard_constraints.json、DATA_DICTIONARY.md、no_direction_preset.md、分区掩膜 | C 锁定区任何形式；全域原始数据 data/ |
| Independent Validator | **否（独立进程）** | vault/zone_C_targets.enc + vault/validator_key.bin（C 锁定区，密文级隔离）、已冻结候选登记 | 不得向开发域回传 C 目标值（只发布聚合后的通过/失败与不确定性） |

提示词哈希：

| Agent | SHA-256（前 16） |
|---|---|
| Discovery Agent | `0f364b060313c434` |
| Experiment Agent | `8d67a10dd9d2ba86` |
| Falsification Agent | `c620f88a098d4c4f` |
| Physics Auditor | `a25a467b8639b239` |
| Independent Validator | `2a9692f1a31d4fe4` |

> Independent Validator 必须在沙箱**之外**独立运行，不得接受发现方的参数更新请求。