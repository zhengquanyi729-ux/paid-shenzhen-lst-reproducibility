# S02.6 泄漏测试套件

版本 stage02-leakage-v1。判定：**PASS**（10 项）。

| 编号 | 测试 | 结果 | 明细 |
|---|---|---|---|
| LK1 | 沙箱可见 CSV 不含任何 C 区 Grid_ID | ✓ | offenders=[] |
| LK2 | 沙箱样本恰为 A∪B 子集（行数=分区规模，且与 C 无交集） | ✓ | A=19184 B=6182 C=2987；mismatch=[] |
| LK3 | 沙箱输入为 Stage 01 公共来源的原样副本（无注入 C 内容） | ✓ | drifted=[] |
| LK4 | 守卫内直读敏感目标全部被拒 | ✓ | denied=['LK10_symlink', 'LK8_hardlink_open', 'LK8_numpy_fromfile', 'LK9_tmp_copy', 'direct_enc', 'direct_key', 'full_csv', 'full_raster', 'listdir_locked', 'listdir_vault', 'locked_C', 'normalized_path', 'numpy_fromfile', 'numpy_loadtxt', 'read_reports', 'relative_dotdot'] leaked=[] |
| LK5 | 绕行尝试（相对/归一化路径、numpy、listdir、glob、reports）均未取得信息 | ✓ | denied=['LK10_symlink', 'LK8_hardlink_open', 'LK8_numpy_fromfile', 'LK9_tmp_copy', 'direct_enc', 'direct_key', 'full_csv', 'full_raster', 'listdir_locked', 'listdir_vault', 'locked_C', 'normalized_path', 'numpy_fromfile', 'numpy_loadtxt', 'read_reports', 'relative_dotdot'] contained(抛错被吞但为空)=['glob_locked', 'glob_vault'] leaked=[] |
| LK6 | 无密钥不可解密；密文不含明文片段；有密钥可还原 | ✓ | wrong_key_rejected=True plaintext_fragment_in_cipher=False plaintext_head=b'Grid_ID,LST_' |
| LK7 | 验证服务只发布聚合结论，且沙箱不可读 reports | ✓ | never_returns=['C 区逐格目标值'] sandbox_reports_denied=True |
| LK8 | 白名单内预置硬链接（文件名无敏感词）无法读取——按 inode 身份拒绝 | ✓ | denied=['LK8_hardlink_open', 'LK8_numpy_fromfile'] leaked=[] |
| LK9 | 白名单之外的改名副本（/tmp）无法读取——读白名单拒绝 | ✓ | denied=True |
| LK10 | 指向锁定真值的符号链接无法读取（realpath 落回拒绝前缀） | ✓ | denied=True |

## 附：为何不用「数值子串匹配」判定泄漏

LST 连续、量程约 19.2 ℃；4 位小数下有 ~191663 个可分辨区间，A∪B 与 C 的偶然重合期望约 360 次，与实测 449 同量级。故「数值子串匹配」不是有效泄漏判据；有效判据是 LK1（ID 归属）与 LK3（输入为原样副本）。

> LK4/LK5 在访问守卫进程内执行；所有拒绝均已写入 append-only 日志。
> 局限：守卫运行于同一 OS 用户，属运行时+密码学隔离；内核级隔离（专用用户/容器）为生产化下一步。