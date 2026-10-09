# S01.6 最终核验（独立复算）

版本 stage01-verify-v1。判定：**PASS**

| 编号 | 复算项 | 结果 | 明细 |
|---|---|---|---|
| V1 | Moran's I of detrended residual ≈ 0.886 | ✓ | recomputed I=0.8860 (expect 0.8860) |
| V2 | 去相关尺度 R = 15 格（1.5 km） | ✓ | R_cells=15, R_m=1500, base_k_at_0p2={'low_veg': 15, 'mid_veg': 11} |
| V3a | 分区规模 A/B/C = 19184/6182/2987 | ✓ | A=19184 B=6182 C=2987 |
| V3b | C 缓冲后连通分量 = 1 | ✓ | n_components=1 |
| V4 | C↔A∪B = 16 ≥ R=15 且三区互不重叠 | ✓ | d(C,A∪B)=16, overlap=0 |
| V4b | 锁定区格均属主样本 | ✓ | locked ⊆ main = True |
| V5a | zone_C_targets 仅 ID + 目标列 | ✓ | cols=['Grid_ID', 'LST_mean'] |
| V5b | zone_C_targets 行数 = 2987 且全为 locked | ✓ | n=2987 |
| V5c | zone_A 全为 discovery 且与 C 无交集 | ✓ | n=19184 |
| V5d | zone_B 全为 dev_validation 且与 C 无交集 | ✓ | n=6182 |
| V6 | stage01_hashes.txt 全部哈希一致（排除本脚本自身产物） | ✓ | mismatched=[] |
| V7 | 验证协议覆盖 Table 13 七类检验 | ✓ | n_coverage=7 |
| V8 | code_manifest 哈希与实际脚本一致且条目数正确 | ✓ | n_files=15, problems=[] |

复算项均不复用 s01_01/02 的中间对象：Moran’s I 与分区距离/连通性均从原始 CSV、
网格 DBF 与冻结分区表重新独立计算；哈希逐条比对。
