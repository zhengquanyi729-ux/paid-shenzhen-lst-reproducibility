# A-6B 时间线审计：Region C 明文访问与"冻结前完成"断言

**审计目的（唯一问题）**
在**第一次任何形式的 Region C（锁定区 C）明文访问**之后，是否发生了任何**可能受 C 结果影响的实质性科学决策或验证规则改动**？

**待检验的形式化条件：**

```
candidate freeze  <  endpoint freeze  <  final validation-rule freeze  <  first C decrypt
                 且：first C decrypt 之后 → 不再发生 candidate / endpoint / inferential-rule 修改
```

**审计范围**：只读。本步骤**未解封 C、未重跑任何 Stage、未修改任何冻结产物、未修改 manuscript**。
所有"当前文件"哈希均为本次审计中重新 `sha256sum` 得到，并与各阶段 manifest 对照。

**结论先行（详见文末与 `A6B_VERDICT.txt`）**：**CASE C**。C 区的"发现侧隔离"可证；
但**归档证据无法证明"最终验证逻辑早于第一次 C 解密"**——因为（i）代码改动不进入哈希链日志，
（ii）两套时钟相差约 3 天且互相矛盾（见 §2），（iii）不存在独立的"验证器已冻结"记录。
此外有一处**确定可证、且方向不利**的事实：**第一次 C 明文解密发生在真实候选被发现/冻结之前**（§3、T4）。

---

## 1 证据源与优先级

| 序 | 证据源 | 说明 | 本审计如何使用 |
|---|---|---|---|
| 1 | 哈希链 append-only 日志 `stage02_platform/logs/experiment_log.jsonl` | 每行含 `seq`(递增)、`hash`、`prev`，构成防篡改链；`ts` 由 `log_tool.append` 在写入时取系统时钟（`time.strftime('%Y-%m-%dT%H:%M:%S')`） | **最高**：用于**顺序**判断（seq 单调、hash/prev 可链式校验） |
| 2 | manifest 内容 + 密码学哈希 | `stageNN_hashes.txt`、`vault_manifest.json`、`pre_unseal_snapshot.json` | 用于证明"当前文件 == 冻结时内容" |
| 3 | 文件内容内嵌时间戳 | JSON 的 `created` 字段等 | **辅助** |
| 4 | 文件系统 mtime | `stat` | **最低**；仅在无更高证据时使用 |

**冲突处理规则**：若低优先级与高优先级矛盾，标记 `[TIMESTAMP CONFLICT]`，**不作"修正"**，如实并陈。

已核实的关键哈希（本次重算 vs manifest）：

| 文件 | 当前 SHA-256 | manifest 记录 | 判定 |
|---|---|---|---|
| `stage01_protocol/protocol/validation_protocol.json` | `a04220a7…4a75` | `a04220a7…4a75`（stage01） | **一致**（终点规格自 Stage 01 起未变） |
| `stage01_protocol/PREREGISTRATION.md` | `56f3e79a…70b4` | `56f3e79a…70b4`（stage01） | 一致 |
| `stage02_platform/agents/independent_validator.py` | `523889c6…932a` | `523889c6…932a`（stage02） | 一致 |
| `stage02_platform/vault/zone_C_targets.enc` | `ef1d8e6e…731f` | `ef1d8e6e…731f`（stage02 / vault_manifest） | 一致 |
| `stage02_platform/logs/experiment_log.jsonl`（1259 行） | `b10cc702…5488` | `b10cc702…5488`（stage04, lines=1259） | 一致 |
| `stage04_validation/scripts/s04_01_validate.py` | `0c015e11…caaf` | `0c015e11…caaf`（stage04） | 一致 |
| `stage03_discovery/registry/frozen_candidates.json` | `69a8ad6f…167b` | `fb8f1d76…7186`（stage03, 3218 B） | **不一致**（见 T7：解封后按设计重生成，`validation_runs` 已置 1 → V4 绊线） |

> 附注：`stage03` manifest 记录的日志为 **1231 行**（`26dc8703…`），`stage04` manifest 为 **1259 行**（`b10cc702…`）。
> 即日志在 Stage-03 冻结与 Stage-04 解封之间增长 1231→1259；`pre_unseal_snapshot.json` 记录解封前 `log_lines_pre=1237`。
> 三者彼此自洽，未见链断裂。

---

## 2 `[TIMESTAMP CONFLICT]`：两套时钟相差约 3 天

**时钟甲（日志内嵌 ts）**：覆盖 `2026-09-24T08:52:53` → `2026-09-24T13:14:01`。全部 Stage-02/03/04 运行内的**科学事件**都落在这不到 5 小时区间内。

**时钟乙（文件系统 mtime）**：呈**两批**结构——

- 第一批 `2026-09-24`：Stage 00 / Stage 01 / Stage-02 早期（`s02_01`…`s02_05`、`log_tool.py`、`access_guard.py`、vault `.enc`）。
- 第二批 `2026-09-27`：自 `s02_07_selftest.py`（`02:50:35`）起，**涵盖全部 Stage-03 / Stage-04 / Stage-05**，例如
  `independent_validator.py` = `09-27 02:58:24`、`approved_unseal.json` = `09-27 03:00:59`、
  `s04_01_validate.py` = `09-27 03:02:56`、`frozen_candidates.json`(stage03) = `09-27 03:03:14`、
  `experiment_log.jsonl` = `09-27 03:05:04`、`stage04_hashes.txt` = `09-27 03:05:34`。

**冲突点**：日志说"解封发生在 09-24 13:12"；mtime 说"同一批产物写于 09-27 凌晨"。二者相差约 **2.5 天**。

**为何不能靠"挑一个信"来解**：
- 若信**日志 ts**：解封 = 09-24 13:12，但 `independent_validator.py` 的改动**没有任何日志条目**，无法定位其相对解封/相对第一次 C 解密的先后。
- 若信 **mtime**：全部科学产物都在 09-27，则验证器定稿（`02:58:24`）**早于**解封批准（`03:00:59`）与结果（`03:03:14`）——顺序看似"正确"，但这与哈希链内嵌 ts 直接矛盾，且意味着"哈希链日志的 ts 不可信"，从而削弱整条链的时间证据力。

→ 按预置规则，此处标记 **`[TIMESTAMP CONFLICT]`**，两读并列、不裁决。**正是这一无法裁决性，构成本次审计判定为 CASE C 的核心依据。**

---

## 3 事件时间线（T1–T11）

> 说明：`internal ts` = 日志内嵌时间戳；`mtime` = 文件系统修改时间。
> 仅日志事件有 `seq`；代码/产物无 `seq`。
> `confidence` 取值：**确定**（哈希/链可直接证明）/ **高**（内容自洽+单一证据源）/ **低**（依赖冲突时钟）。

| Event ID | Event | File / path | internal timestamp | filesystem mtime | manifest/hash evidence | confidence | implication |
|---|---|---|---|---|---|---|---|
| **T1** | **终点与验证协议冻结**（Stage 01）：主终点 = C 区 ΔRMSE(vs Baseline A)，通过条件 = ΔRMSE>0 ∧ 199 次空间块置换 p<0.05 ∧ 95% CI 不跨 0 ∧ 物理审计过 ∧ 负对照未通过；文末注明"主终点在**解封前**冻结；解封后不得更改模型、指标、假设或停止条件（SI-1）" | `stage01_protocol/protocol/validation_protocol.json`；`stage01_protocol/PREREGISTRATION.md` | 内容 `created:"2026-09-24"` | `08:45:42`（json）/ `08:46:16`（md） | SHA `a04220a7…` / `56f3e79a…` = stage01 manifest | **确定** | 终点/推断规则在**任何** C 访问之前冻结，且此后哈希未变 |
| **T2** | **空间划分与缓冲冻结**：A/B/C 三分 + `R = 15 格 = 1.5 km`；`C↔A∪B = 16 格 ≥ R`；C 连通分量=1 | `stage01_protocol/split/split_manifest.json`；`PREREGISTRATION.md` §L21/§33-34 | `created:"2026-09-24"` | `08:45:05`（split）/ `08:46:16`（md） | stage01 manifest | **确定** | 分区/缓冲规格冻结 |
| **T3** | **C 区加密封存**：AES-256-GCM；密钥 `validator_key.bin`（32B）与密文分离；幂等可复现（确定性 nonce） | `stage02_platform/vault/zone_C_targets.enc`；`vault/validator_key.bin`；`vault/vault_manifest.json` | `created:"2026-09-24"`；`n_rows=2987` | key `08:47:43`；`.enc` `09:08:30`（重构，哈希不变） | `.enc` SHA `ef1d8e6e…` = manifest | **确定** | 密文级隔离就位 |
| **T4** | **★第一次 Region C 明文解密**（且为一次"发布"）：Stage-02 端到端自测跑 Independent Validator，先拒未冻结/哈希不符，随后**解封并发布**占位候选 SMOKE-0001（=Baseline A 规格）。`decrypt_vault()` 在哈希校验**之后**执行 → 该发布即一次真实 C 明文访问。发布值 `rmse_baselineA=2.8415…, Δ=0.0, p=1.0` | `stage02_platform/logs/experiment_log.jsonl` seq **43–46**；`reports/s02_07_selftest.json` | **`2026-09-24T08:52:58`** | 日志文件 `09-27 03:05:04` | 日志 hash/prev 链可校验；`s02_07_selftest.json` 内 `rmse_baselineA=2.841519…` = 真实 C 基线 | **高**（日志给出精确时点；"真实 C"由数值自洽佐证） | **C 明文第一次被访问发生在任何真实候选被发现/冻结之前** |
| **T5** | **C 被反复解密的开发期自测**：同一占位候选在多次 selftest 中重复解封发布（每次 `validate()` 均 `decrypt_vault()`），含 3 次 `dry_run=True` 的 `unsealed_validated`（13:11 段）与 14 次 `validation_published`（SMOKE-0001）| `experiment_log.jsonl` seq 45/66/87/108/172/209/255/272/318/780/797/923/1069/1210（publish）+ 1232–1237（dry-run）；另 seq 1238–1239 为正式 | `08:52:58` → `13:12:11` | — | 链可校验 | **确定** | **Region C 明文至少被解密 ≥ 22 次**（14 publish + 8 unsealed）；"一次性/唯一解封"叙事不成立 |
| **T6** | **Stage-03 沙箱内自主发现**（A/B 数据；C 被 deny）：R1 预注册假设议程 → R2 贪心前向（全项池）→ R3 局部修订；候选按 **A 区空间分块 CV** 评估 | `stage03_discovery/scripts/s03_02_symreg_search.py`；`agents/roles.py`；日志 `round_start/round_end` | seq 320–1192；`09:10:49` → `13:07:44` | `s03_02` = `09-24 09:14:21` | 含 `access_denied` 记录（守卫生效） | **确定** | 候选**定义与排序只用 A 区**；发现侧未见 C |
| **T7** | **Stage-03 候选冻结**：入选= `passed_dev_gain`，按 A-CV 升序取 ≤8；另冻结候选 `S03-H01-LIN7` 作**参考/安慰剂**。冻结内容由验证侧同一 `canon_hash()` 计算 | `stage03_discovery/registry/frozen_candidates.json`；`registry/candidates/*.json` | 冻结记录无独立日志条（沙箱外步骤） | **现文件** `09-27 03:03:14` | 现文件 SHA `69a8ad6f…` **≠** stage03 manifest `fb8f1d76…`（3218B） | **低**（时钟冲突） | 冻结登记在解封后**按设计重生成**（`validation_runs` 置 1）；这导致 `verification.json` 的 **V4 绊线 FAIL**（预期） |
| **T8** | **解封授权记录**：批准 `S03-H10-GREEDY`(discovery_candidate) 与 `S03-H01-LIN7`(reference_placebo)，每候选 `validation_runs` 上限 1，不可逆 | `stage04_validation/registry/approved_unseal.json` | 内容 `created:"2026-09-27"` | `09-27 03:00:59` | 哈希列入 stage04 manifest（"生成于 2026-09-24 13:14:31"）→ **内容时间与 manifest 生成时间冲突** | **低** | 出现显式"单次解封"授权，但**此前已发生多次解密**（T4/T5）→ 授权语义与事实不符 |
| **T9** | **Stage-04 正式解封**：先 3×`dry_run=True`，后 2×`dry_run=False`（H10-GREEDY 与 H01-LIN7）。结果：H10 `ΔRMSE=+0.3791, p=0.005, passed=true`；H01 `Δ=0.0, passed=false`（安慰剂如期失败）。`dry_run=True` 同样执行 `decrypt_vault()` | `stage04_validation/scripts/s04_01_validate.py`；`experiment_log.jsonl` seq 1232–1239 | `2026-09-24T13:11:20` → `13:12:11` | `s04_01_validate.py` = `09-27 03:02:56`；结果 `09-27 03:03:14` | `s04_01_validate.py` SHA `0c015e11…` = stage04 manifest | **中**（事件确定；其"真实墙钟时刻"受 §2 冲突影响） | **确证性主结果**（论文援引的 +0.3791 / [0.2761,0.4814] 来源） |
| **T10** | **★验证器判定逻辑改动**：`validate()` 的 5 项通过条件中，`physics_audit_pass` 与 `negative_controls_not_fooled` 两项由"读取候选 JSON 的自报 verdict"改为**在本验证进程内用 A/B 数据独立复算**（`audit_independent` / `controls_independent`）；判据阈值不变，只是"由谁计算"变了 | `stage02_platform/agents/independent_validator.py`（第 65–67、211–213 行注释与实现） | **无日志条目**（代码改动不写链） | **`2026-09-27 02:58:24`** | 现文件 SHA `523889c6…` = stage02 manifest（=改后内容） | **低**（改动本身确定；**先后关系不可定**） | **实质性 validation-logic 修改**；其相对"第一次 C 解密"/"正式解封"的先后**无法证明** → `[TIMESTAMP CONFLICT]` |
| **T11** | **记录定稿 + 解封后重生成**：Stage-04 报告与哈希清单；Stage-03 `verification.json` 因解封后重算显示 **`FAIL:V4`**（冻结候选 `validation_runs` 已=1，不再为 0）——这是**预期绊线**而非新缺陷 | `stage04_validation/STAGE04_REPORT.md`；`manifests/stage04_hashes.txt`；`stage03_discovery/reports/verification.json` | — | `STAGE04_REPORT.md`/`hashes` = `09-27 03:05:34`；`verification.json` = `09-27 03:05:04` | 日志最终 `b10cc702…/1259` | **高** | 归档记录在解封之后被重写；V4 FAIL 是解封消费预算的直接后果 |

---

## 4 "第一次 C 访问之后是否发生实质性改动"逐项核查

| 核查项 | 结论 | 依据 |
|---|---|---|
| **终点/通过条件（endpoint）是否在首次 C 解密后被改？** | **NO** | `validation_protocol.json` SHA 未变、mtime `09-24 08:45:42` < 首次解密 `08:52:58`；未发现任何后继终点产物。判定项语义自 T1 起恒定。 |
| **候选定义是否在首次 C 解密后被改？** | **NO**（发现侧可证） | 候选由沙箱内 `roles.discovery_propose` 产生（不读区数据）；表达式由 A 区 CV 决定；C 在沙箱内被 deny（`access_denied` 有记录）。**注意**：T4 的首次解密（08:52）在真实候选冻结（T7）**之前**，但该批解密全部针对占位候选、返回值恒为 `Δ=0.0`，不含可用于设计候选的信息。 |
| **候选排序/选择（selection）是否被 C 影响？** | **NO** | `s03_03_freeze.py` 仅以 `c['dev_evidence']['cv_rmse']`（A 区 CV）升序取前 `freeze_max`；B 仅作 `not_fooled` 门；C 从不参与。 |
| **统计检验规则（置换/自助）是否被改？** | **NO**（规则内容）；**UNRESOLVED**（定稿时点） | 置换 = 199 次、自助 = 1000 次，规则在两处实现（发现侧 `roles.falsify`、验证侧 `independent_validator`）一致且含"退化恒等"守卫。规则**内容**未变；但其**代码定稿时点**见 T10。 |
| **验证器判定逻辑是否在首次 C 解密后被改？** | **UNRESOLVED** | T10 的改动确实存在（mtime `09-27 02:58:24`）。若采信 mtime，`02:58` 早于解封（`03:00`+）→ 顺序"正确"；若采信日志 ts，则无法定位。**方向**是"更严"（独立复算只会更难通过，不会放宽），且所有已记录 verdict 在该改动下均不翻转——但这**不能**替代"先后可证"。 |
| **是否存在"一次性解封/唯一访问"事实？** | **NO** | 见 T4/T5：C 明文被解密 **≥22 次**，首次在正式解封前约 4.3 小时（日志 ts 口径）。任何 "unsealed exactly once / first and only access / single irrevocable unsealing / one authorised access" 措辞均为**不实**。 |
| **"锁定区对发现侧隔离"是否成立？** | **YES** | 沙箱 deny（含 `zone_c`/`vault`/`validator_key`/`data_原始`/`lst_30m` 名称与前缀）；角色读取面 A/B；选择只用 A-CV。此三层均有代码与日志支撑。 |

---

## 5 判定与理由

**形式化条件逐环检查：**

| 环节 | 能否证明 | 依据 |
|---|---|---|
| `candidate freeze < endpoint freeze` | **YES** | T7 候选冻结在 T1 终点冻结之后（即便按日志 ts 亦然） |
| `endpoint freeze < final validation-rule freeze` | **无法证明** | 终点内容恒定，但"验证逻辑定稿时点"无独立记录（T10 无日志条，时钟冲突） |
| `final validation-rule freeze < first C decrypt` | **无法证明** | 同上；且日志 ts 与 mtime 对该顺序给出**相反**结论 |
| `first C decrypt < candidate freeze`（反向检验） | **成立且不利** | T4 首次解密 `08:52:58` 早于 T7 真实候选冻结 → 严格链在**第一环即断裂**（虽为占位解密） |
| 首次 C 访问后无实质改动 | **部分** | endpoint/selection/endpoint 项可证为"未受 C 影响"；validation-logic 项不可证 |

**结论**：链中**关键一环（`final validation-rule freeze < first C decrypt`）不可证明**，且两套时钟对其给出矛盾结论。
按预置定义，这正是 **CASE C**。

> 补充判断（供你复核时权衡）：由于**首次 C 明文解密（T4）确实先于真实候选冻结（T7）**，
> 若把"任何形式的 C 明文访问"严格计入，则除"不可证"之外，还存在一处**可证的顺序违背**——
> 这将使情景向 **CASE B** 靠拢（即"存在需登记的协议偏差"）。
> 但该批解密针对**占位候选（Δ 恒为 0）**，在**科学内容层面**不携带可污染候选定义/选择的信息。
> **CASE C 与 CASE B 在处置上的落点相同**：Stage-04 不得再被称为 fully confirmatory / prospective，
> 应如实表述为"**锁定留出区上的、事后选择的、带有已登记协议偏差的评估**"。二者的差别仅在于把 T4 的
> 占位解密定性为"顺序违背（B）"还是"不可裁决（C）"。

---

## 6 本步骤的边界声明

- 本审计**只读**：未解密 C、未重跑任何 Stage、未触碰任何冻结产物、**未修改 manuscript**。
- 标记 `[TIMESTAMP CONFLICT]` 之处**未作修正**，两读并陈，留待你裁决。
- 本文件不代替 Stage 00–05 的任何权威产出；所有引用数值均可回溯至上表中路径与哈希。
- 下一步（Phase B 改稿）**在你就 CASE A/B/C 拍板之后**再启动。

*生成于 A-6B 只读审计步骤；同日与 `A6B_VERDICT.txt` 配套。*
