# S02.2 沙箱工作树与访问守卫

版本 stage02-guard-v1。状态 **OK**。

沙箱工作树：`stage02_platform/sandbox_root`（发现侧唯一可读写区）。

## 守卫冒烟测试

| 用例 | 期望 | 实际 |
|---|---|---|
| read zone_A | 允许 | ✓ 允许 |
| write work | 允许 | ✓ 允许 |
| read vault enc | 拒绝 | ✓ 拒绝 |
| read vault key | 拒绝 | ✓ 拒绝 |
| read locked C | 拒绝 | ✓ 拒绝 |
| read full CSV | 拒绝 | ✓ 拒绝 |
| read LST tif | 拒绝 | ✓ 拒绝 |
| write stage01 | 拒绝 | ✓ 拒绝 |
| subprocess | 拒绝 | ✓ 拒绝 |

拒绝次数 7，沙箱内 open 计数 788。