#!/usr/bin/env bash
# Stage 05 复现：Baseline B + Results 3（外部复现）+ Baseline D（消融）
# 按顺序执行（每步建议 < 45s）
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
S05="$(dirname "$HERE")"
S="$S05/scripts/s05_01_baselineB.py"

python3 "$S" cv 0
python3 "$S" cv 1
python3 "$S" cv 2
python3 "$S" cv 3
python3 "$S" cv 4
python3 "$S" fit
python3 "$S" fit_aug
python3 "$S" pdp NDVI_mean
python3 "$S" pdp DEM_mean
python3 "$S" pdp SVF_mean
python3 "$S" perm
python3 "$S" control
python3 "$S" report

python3 "$S05/scripts/s05_02_figures.py"

# Results 3：外部城市复现（需外部数据集，见 repro/README.md；无该数据时可跳过）
python3 "$S05/scripts/s05_04_external_replication.py" all

# Baseline D：无约束 / 无防火墙消融（可在末位传种群规模，默认 200）
python3 "$S05/scripts/s05_05_baselineD.py" 150

python3 "$S05/scripts/s05_03_manifest_verify.py"
echo "Stage 05 reproduction complete."
