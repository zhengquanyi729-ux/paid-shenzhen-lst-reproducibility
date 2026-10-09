# S02.1 数据保险库

版本 stage02-vault-v1。状态 **OK**。

| 项 | 值 |
|---|---|
| 算法 | AES-256-GCM（认证加密） |
| 密钥 | `stage02_platform/vault/validator_key.bin`（32 B，reused） |
| 密文 | `stage02_platform/vault/zone_C_targets.enc`（339584 B） |
| 密文 SHA-256 | `ef1d8e6e2b2b8d0ce365666071abb5b5560170c8b7cca31ca338735f7fbc731f` |
| 明文 SHA-256 | `b4a709e16d7b75425496fae1cea1ea6c5fd113575fe5f6766ab3389da353eab9` |
| 行数 / 列 | 2987 / Grid_ID, LST_mean, NDVI_mean, DEM_mean, SVF_mean, Road_Dens, X_BD, X_BH, X_VolDens |

> C 区目标值已由明文改为**密文级隔离**：保险库位于发现沙箱工作树之外，且被访问守卫 deny。
> Stage 01 冻结的 `locked/zone_C_targets.csv` 作为审计件保留，同样被 deny。
