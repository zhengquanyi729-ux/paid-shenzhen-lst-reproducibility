# Stage 01 规则冻结 — 完成报告

**项目**：物理约束下城市地表热环境规律的 AI 自主科学发现研究框架（PAID）
**阶段**：Stage 01 规则冻结（Table 17）
**日期**：2026-09-24  |  **状态**：完成并通过独立复算（**PASS**，13/13 项）

> 本阶段已按预注册冻结「约束、空间切分、主指标、预算与权限」四件套，产出预注册协议与清单哈希。
> 依既定范围（Stage 00 + Stage 01，然后暂停），**现暂停等待确认**，未开放正式发现环境。

---

## 1 本阶段做了什么

| 步骤 | 任务 | 核心结论 |
|---|---|---|
| S01.1 | 空间自相关诊断（确定去相关尺度 R） | 去趋势残差 Moran's I=**0.886**（伪 p=0.005）；建成/中层 r(k) 降至 0.2 最大滞后 15 格 → **R = 15 格 = 1.5 km** |
| S01.2 | 60/20/20 空间划分（发现—验证防火墙） | 5 个连通 k-means 簇整簇指派：A **19184**（67.7%）/ B **6182**（21.8%）/ C **2987**（10.5%，缓冲后）；C↔A∪B = 16 格 ≥ R |
| S01.3 | 物理约束与无方向预设（§3.1/§3.2） | 冻结 **21 条硬约束**（可执行 14 / 仅声明 5 / 不可计算 2）；**9 条**系统提示词禁用方向 |
| S01.4 | Agent / 实验 / 验证 / 代码 四清单 | 冻结 5 类 Agent 权限、候选上限与预算、主终点与通过条件、代码环境哈希 |
| S01.5 | 预注册协议与哈希清单 | `PREREGISTRATION.md` + `manifest/stage01_hashes.txt`（36 个产物） |
| S01.6 | 最终核验（独立复算） | 13 项全部一致，无泄漏、哈希自洽 → **PASS** |

---

## 2 关键设计决定（及其理由）

**为什么必须去趋势再定 R。** 深圳 LST 存在沿海—内陆、核心—边缘的大尺度确定性梯度。若直接在原始场上算相关图，会把趋势的长程相关误当随机过程的相关长度，显著高估缓冲带宽。故以三阶二维多项式趋势面（R²=0.435，残差 sd 3.31 ℃）为大尺度项，对残差估计去相关尺度。

**为什么用连通分块而非随机抽格。** S01.1 证 LST 强空间自相关（Moran's I=0.886），随机抽格会造成空间泄漏。改用 5 个连通 Voronoi 簇整簇指派，保证每区空间连续。

**为什么缓冲只施加于 C。** 框架明确规定 B 区「参与调参后不再视为独立确认」；A 与 B 同属开发域，无需相互隔离。若对 A/B 之间也设 1.5 km 缓冲，会把非连通区撕碎、样本锐减。这一处理使保留率从 ~67% 提升到 95.5%，同时保证 C 与 A∪B 的 ≥R 间距。**这是本阶段最重要的方法学判断。**

**为什么能量闭合标为 not_computable。** 现有数据无净辐射、人为热、感热、潜热、地热通量任一输入；且 DEM 全域仅 3–17 m（不符合深圳地形）。据此，任何能量残差或高程机制推断都被禁止，避免伪造物理一致性。

---

## 3 必须如实声明的局限

1. **单一时相**：LST 观测元数据（时间/传感器/反演/QA）不可恢复，研究限定为单时相空间分异，禁日夜/季节/热恢复分析（S00.1）。
2. **地表覆盖偏斜**：C 区 NDVI 三分位构成 [0.338, 0.548, 0.115]，偏离全局 [0.333, 0.333, 0.333]（L1=0.2445）。系连通分区与深圳地表覆盖空间聚集所致，非抽样失误；L2 结论适用范围须据此限定，验证时须分层报告。
3. **协变量口径未确认**：X_BD（max 1.77，非 [0,1] 覆盖率）、X_BH（max 224 m，非格均高度）、X_VolDens（与 X_BD·X_BH 恒等式未证实）、DEM（不合地形）、Road_Dens（量纲未明）——仅可无量纲化入模并登记口径假设。
4. **不可逆缺口**：CSV 导出时 61 格剔除条件、栅格二次掩膜依据未留存；须回溯数据作者。
5. **测量误差无法正式传播**：LST 无 QA/不确定度元数据，故以 ±0.5 K / ±1.0 K 两档扰动作为预注册的敏感性方案（见验证协议 `measurement_error`），效应量须大于扰动区间宽度方可宣称稳健。
6. **缓冲区判据有敏感性**：R=15 取 r(k)<0.2 判据；更保守的 r<0.1（建成层）给出替代 R=25 格，作为预注册稳健性对照，不改变主分析。
7. **预训练先验**：不得宣称 Agent 无先验；可操作主张为「提示词不注入目标领域结论、研究者不按结果引导、全过程可审计」。

---

## 4 产物索引

| 类别 | 路径 |
|---|---|
| 预注册协议 | `PREREGISTRATION.md` |
| S01.1 报告 | `reports/s01_01_spatial_autocorr.{md,json}`、`reports/figures/s01_01_correlogram.png` |
| S01.2 报告 | `reports/s01_02_split.{md,json}`、`reports/figures/s01_02_split_map.png` |
| S01.3 报告 | `reports/s01_03_constraints.{md,json}` |
| S01.4 报告 | `reports/s01_04_protocols.{md,json}` |
| S01.5 报告 | `reports/s01_05_preregistration.json` |
| S01.6 核验 | `reports/s01_06_verify.{md,json}` |
| 六清单 | `split/split_manifest.json`、`agent/agent_manifest.json`、`protocol/experiment_protocol.json`、`protocol/validation_protocol.json`、`manifest/code_manifest.json`、`stage00_data_audit/manifest/data_sha256.txt` |
| 硬约束与字典 | `constraints/hard_constraints.json`、`constraints/DATA_DICTIONARY.md`、`constraints/no_direction_preset.md` |
| 分区数据 | `split/analysis_split.csv`、`split/zone_A_open.csv`、`split/zone_B_devval.csv`、`locked/zone_C_targets.csv`、`locked/README.txt` |
| 哈希清单 | `manifest/stage01_hashes.txt` |
| 脚本 | `scripts/s01_01…s01_06*.py` |

---

## 5 门禁与下一步

Stage 01 全部子任务完成并复算通过。**开放 Stage 02 前需用户确认。**

Stage 02（平台构建）的首要任务是**访问控制的物理实现**与**泄漏测试**：把 `locked/zone_C_targets.csv` 移入发现 Agent 无权读取的独立目录/服务，并以泄漏测试验证防火墙有效；随后搭建 Agent、沙箱与 append-only 日志。框架允许 AI 最终得出「尚无经独立验证的新规律」的结论。
