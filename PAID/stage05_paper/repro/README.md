# Stage 05 复现说明（Baseline B + Results 3 + Baseline D）

复现件覆盖三部分：**Baseline B（随机森林 / 梯度提升）公平比较**、**Results 3 外部城市复现
（长春 2021）**、**Baseline D 无约束 / 无防火墙消融**。所有随机种子固定为 `20260924`；
结果对同一环境重跑逐位一致。

## 环境

- Python 3.10；仅需 `numpy`、`pandas`、`matplotlib`。
- **不需要** scikit-learn / xgboost / scipy（环境无这些包、亦无网络）。
  ML 模型在 `scripts/bmlib.py` 中自行实现（CART 回归树 + 随机森林 + 平方损失提升）。

## 运行顺序

因单个 shell 调用有时限，Baseline B 主脚本按子命令分段执行、逐段写 `cache/`：

```bash
S=stage05_paper/scripts/s05_01_baselineB.py
python3 $S cv 0    # A 区第 0 折 CV（RF+GBM）——每折一次调用
python3 $S cv 1
python3 $S cv 2
python3 $S cv 3
python3 $S cv 4
python3 $S fit            # 全 A 拟合 RF/GBM(原始)，预测 A/B/C
python3 $S fit_aug        # 全 A 拟合 RF(增广特征)
python3 $S pdp NDVI_mean  # 1D PDP（每个变量一次调用）
python3 $S pdp DEM_mean
python3 $S pdp SVF_mean
python3 $S perm           # B/C 置换 p 与自助 CI
python3 $S control        # 负对照：打乱 A 区目标后训练
python3 $S report         # 汇总 -> reports/baselineB.json + BASELINE_B.md

python3 stage05_paper/scripts/s05_02_figures.py             # 图件
python3 stage05_paper/scripts/s05_03_manifest_verify.py     # 清单 + 自验证
```

Results 3（外部复现）与 Baseline D（消融）各为单脚本，可直接运行：

```bash
# Results 3：需外部数据集（长春 2021 DBF），路径写在脚本常量 CC_DIR / CC_MAIN / CC_GRID
python3 stage05_paper/scripts/s05_04_external_replication.py all
# 参数可选：all（默认，全流程）/ nogreedy（跳过贪心再发现）/ report（仅重生成报告）

# Baseline D：末尾参数为种群规模 N（默认 200；本稿用 150）
python3 stage05_paper/scripts/s05_05_baselineD.py 150
```

`repro/run_all.sh` 按上述顺序串联（可整体执行；无长春数据时可注释掉 s05_04 一行）。

## 主要产物

| 文件 | 说明 |
|---|---|
| `reports/baselineB.json` | Baseline B 全部数值（A-CV、A/B/C 各区、置换 p、CI、重要度、PDP、负对照） |
| `reports/BASELINE_B.md` | 同上的人类可读报告 |
| `reports/external_replication.json`、`reports/EXTERNAL_REPLICATION.md` | Results 3 外部复现（冻结投影迁移、支点/方向复现、独立再发现、跨城迁移） |
| `reports/baselineD.json`、`reports/BASELINE_D.md` | Baseline D 消融（Arm 1 无约束、Arm 2 无防火墙、Arm 2b 全量重拟合） |
| `manifests/stage05_hashes.txt` | Stage 05 全部产物 SHA-256 |
| `figures/fig1_protocol_split.*` | 研究区 A/B/缓冲/C 空间划分 |
| `figures/fig2_baselineB.*` | Baseline 公平比较（PNG/PDF/SVG，300 dpi） |

## 关键口径

- 训练集 = A 区；开发指标 = A 区**冻结空间分块 CV**（connected k-means, k=5, seed=20260924）。
- Baseline B 使用与 Baseline A **相同的 7 个原始协变量**（主口径）；另有增广口径（+ 候选工程特征）。
- **C 区已解封**：C 区读数为事后比较，非新增确认性检验。
- 负对照：打乱 A 区目标后训练，C 区 RMSE ≈ 常数地板，远差于真模型 → 排除泄漏。
- **Results 3** 为**外部数据**（长春 2021），不在 Stage 01 冻结协议内；因缺 `SVF_mean` / `Road_Dens`，
  冻结式只在其可表达投影上检验，结论为"部分复现"。数据路径见脚本头部常量。
- **Baseline D** 的 Arm 2 触及锁定区 C，仅用于"选择泄漏"消融演示；脚本调用物理审计时把
  `log_tool.append` 临时置为 no-op，**不写入**任何 Stage 02/03/04 冻结日志或登记
  （由 `s05_03` 的 V7 校验）。
