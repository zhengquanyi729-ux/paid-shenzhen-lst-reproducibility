# S01.4 预注册清单：Agent / 实验协议 / 验证协议 / 代码

框架依据：Table 12 六清单（本报告补齐其中四项）、Table 10/11/13/14、§5.3、§3.2。

版本 **stage01-protocols-v1**，2026-09-24。

## 1 Agent manifest

> 系统提示词只注入：`DATA_DICTIONARY.md`、`hard_constraints.json`、计算预算、工具白名单；禁用 9 条方向性主张（§3.2）。基础模型版本待 Stage 02 声明并冻结。

| Agent | 用途 | 可访问数据 | 禁止访问 |
|---|---|---|---|
| Discovery Agent | 自主选择特征、尺度、假设与数学表达式，提出可证伪候选。 | A 发现区 | B 开发验证区（调参用，不下发目标）；C 锁定区目标值；旧论文结论/相关矩阵 |
| Experiment Agent | 编写实验代码、比较允许的方法、测量开发集表现，记录全部运行。 | A 发现区、B 开发验证区 | C 锁定区目标值 |
| Falsification Agent | 寻找反例、空间混杂、伪相关与负对照；可建议放弃候选。 | A 发现区、B 开发验证区、分区掩膜（row/col/zone） | C 锁定区目标值 |
| Physics Auditor | 独立审计量纲、几何、可计算物理约束及解释的过度延伸。 | constraints/hard_constraints.json、constraints/DATA_DICTIONARY.md、全部分区掩膜 | C 锁定区目标值 |
| Independent Validator | 独立进程持有 C 区目标值，验证后发布完整通过/失败结果，不执行发现 Agent 的调参请求。 | locked/zone_C_targets.csv、已冻结候选登记 | 不得向开发域回传 C 目标值（只发布聚合后的通过/失败与不确定性） |

## 2 Experiment protocol

- 候选上限：每轮 ≤ 50 个；总 fit 预算 5000；冻结候选 ≤ 8 个。
- 开发主指标：A 发现区空间分块交叉验证 RMSE（℃），分块=连通簇，块数≥5；并列报告 MAE、R²、AIC/BIC（同族比较）、表达式复杂度（项数/参数量）。
- 停止条件：连续 200 次 fit 无开发指标改进；累计 fit 达 5000 次预算；冻结候选数达上限 8；反例/混杂检验使所有候选被否决（允许以「暂无经证伪仍成立的候选」结束）
- 失败记录：append-only JSONL，禁止覆盖（字段：candidate_id、timestamp、agent、prompt_sha256、code_sha256、expr、vars、scale_r、dev_metric、dev_metric_value、status(pass/fail/rejected)、reason、counterexamples）。
- 对照组：Baseline A、Baseline B、Baseline C、Baseline D + Proposed。

## 3 Validation protocol

- 主终点：候选表达式在 C 区的 RMSE（℃）以及相对 Baseline A 的 ΔRMSE；通过条件：ΔRMSE>0（优于 Baseline A）且经 199 次空间块置换检验 p<0.05，且 95% 置信区间不跨 0，且物理审计通过，且负对照（空间置换/随机目标）未通过。
- 空间推断：空间划分为主：C 与 A∪B 最小间距 16 格（1.5 km）≥ R（15 格）。
- 多重比较：Holm–Bonferroni（family = 冻结候选集）；同时报告未校正 p。
- 缺失处理：C 区不插补；缺失/无效格显式排除并登记数量。
- 负对照：C 区目标空间置换 199 次；随机目标列；打乱行序的伪候选
- 分层与异常：不得以全样本显著掩盖某一分层不成立；任一分层符号相反须如实报告。
- 测量误差：对 C 区目标施加 ±0.5 K 与 ±1.0 K 两档扰动重算主检验；效应的符号与显著性须在两档下均保持，且效应量须大于扰动引起的区间宽度，方可宣称稳健。
- 判据敏感性：主分析采用 R=15 格；以更保守判据（r<0.1，建成层）得到的替代分区 R=25 格作为**预注册的稳健性对照**，在同一批冻结候选上重算，与主结果一并报告；替代分区不改变主分析，也不得据其结果修订候选。

### 3.1 Table 13 七类检验逐项落实

| # | 检验 | 落实方式 | 位置 |
|---|---|---|---|
| 1 | 空间分块 / 缓冲验证 | 分区于空间连续簇；C 与 A∪B 间距 = 16 格 ≥ R = 15 格；C 内不混入任何 A/B 格。 | split/split_manifest.json、validation_protocol |
| 2 | 负对照及合适的空间置换 | C 区目标空间置换 199 次 + 随机目标列 + 打乱行序伪候选。 | validation_protocol.negative_controls |
| 3 | 物理及量纲审计 | Physics Auditor 独立审计量纲一致性、几何合法性、可计算物理约束；能量闭合标 not_computable。 | constraints/hard_constraints.json、agent/agent_manifest.json |
| 4 | 地表类型分层与异常掩膜 | 按 NDVI 三分位（低/中/高植被）分层报告每个候选的效应与 RMSE；C 区构成为 [0.338, 0.548, 0.115]，须分层呈现以避免少数类型主导结论；异常值以 S00 掩膜（LST==0 填充、非物理 NDVI、边界部分格）排除，并在报告中登记被排除格数。 | validation_protocol.strata_and_outliers |
| 5 | 测量误差传播 | LST 无 QA/不确定度元数据（S00.1），故无法做正式误差传播；预注册**敏感性方案**：以 LST 观测不确定度 ±0.5 K 与 ±1.0 K 两档对目标加扰动，检验候选效应的符号与显著性是否保持；效应量须大于该扰动下的区间宽度方可宣称稳健。 | validation_protocol.measurement_error |
| 6 | 多重检验和候选记录 | Holm–Bonferroni（family = 冻结候选集 ≤ 8）+ 报告未校正 p；搜索规模登记于 append-only 日志。 | validation_protocol.multiplicity、experiment_protocol.failure_logging |
| 7 | 外部时相与地区复现 | D 层（新时相/新城市）独立收集；当前数据无第二时相，故 L3 结论须待外部数据补齐后给出。 | validation_protocol.external（N/A 于本数据） |

覆盖：Table 13 七类检验全部登记（第 7 类因缺第二时相/城市，标记为 not_available）。

## 4 Code manifest

- 环境：Python 3.10.12 / numpy 2.2.6 / pandas 2.3.3 / matplotlib 3.10.8。
- 冻结代码 **15** 个（lib + Stage 00 + Stage 01），逐文件 SHA-256 见 `manifest/code_manifest.json`。

## 5 交付物

| 清单 | 路径 |
|---|---|
| agent_manifest.json | `agent/agent_manifest.json` |
| experiment_protocol.json | `protocol/experiment_protocol.json` |
| validation_protocol.json | `protocol/validation_protocol.json` |
| code_manifest.json | `manifest/code_manifest.json` |