# S02.7 端到端自测

版本 stage02-selftest-v1。判定：**PASS**。

| 步骤 | 结果 | 明细 |
|---|---|---|
| 洁净室：清空沙箱工作树（保留阶段专属子目录） | ✓ | removed=6 |
| Discovery Agent（沙箱内） | ✓ | {"proposed": "SMOKE-0001", "out": "/sessions/friendly-awesome-turing/mnt/AI_lst/PAID/stage02_platform/sandbox_root/work/cand_0_proposed.json"} |
| Experiment Agent（沙箱内） | ✓ | {"id": "SMOKE-0001", "rmse_A": 2.914880975503129, "rmse_B": 2.54250853893637} |
| Falsification Agent（沙箱内） | ✓ | {"id": "SMOKE-0001", "rmse_real": 2.54250853893637, "controls": {"NC1_row_shuffle": 5.483515214186221, "NC2_block_permute": 5.464164167989063, "NC3_random_target": 5.48888219099766 |
| Physics Auditor（沙箱内） | ✓ | {"id": "SMOKE-0001", "verdict": "pass", "items": {"PA1": true, "PA2": false, "PA3": true, "PA4": true, "PA5": true, "PA6": true}} |
| 冻结候选 | ✓ | id=SMOKE-0001 canon=f60cc3fa32ff2ecd |
| 拒绝未冻结候选 | ✓ | {"rc": 2, "refused": true} |
| 拒绝哈希不一致（解封后修订） | ✓ | {"rc": 2, "refused": true} |
| Independent Validator 解封并发布（沙箱外） | ✓ | {"statistic": "RMSE_C 与 ΔRMSE(vs Baseline A)", "rmse_baselineA": 2.841519144671417, "rmse_candidate": 2.841519144671417, "delta_rmse": 0.0, "perm_p": 1.0, "n_perm": 199, "perm_corr |
| 拒绝重复解封（validation_runs=1） | ✓ | {"rc": 2, "refused": true} |
| 通过条件判定单元测试（正/反两例） | ✓ | all-true→True, p-fail→False |

## 验证服务发布（沙箱外）

候选 `SMOKE-0001`：RMSE(C)=2.8415，Baseline A RMSE(C)=2.8415，ΔRMSE=0.0000，空间块置换 p=1.000（199 次），95% CI=[0.0000, 0.0000]。

通过条件：{"delta_rmse_pos": false, "perm_p_lt_0.05": false, "ci_excludes_zero": false, "physics_audit_pass": true, "negative_controls_not_fooled": true} → **未通过**。

> 平台冒烟测试：候选为预注册 Baseline A 占位，非科学发现；结论不得作为研究结果引用

## 日志

哈希链自洽 **True**，共 1211 条，链尾 `2857ce32645acd2f`。

## 哈希清单

共 47 个产物，复算一致 **True**。