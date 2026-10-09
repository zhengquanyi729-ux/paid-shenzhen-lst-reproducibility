"""
Falsification Agent（沙箱内）
=============================
职责（Table 10）：寻找反例、空间混杂、伪相关与负对照；可建议放弃候选。
框架依据：Table 13「负对照及合适的空间置换」「空间分块/缓冲验证」；Table 14 对照组。

本模块实现三个负对照（均在 B 开发验证区，模型固定不自适应）：
  NC1 行序打乱目标 —— 破坏一切结构；
  NC2 空间块置换     —— 按 5×5 格块整体置换目标，保留块内空间自相关；
  NC3 随机目标列     —— 与协变量无关的高斯噪声。
判据：负对照下 RMSE **不应优于**真实目标的 RMSE（即 RMSE_ctrl >= RMSE_real）。
若某负对照反而更优，说明候选在拟合噪声 → 建议放弃。

用法：
  python agents/falsification_agent.py <candidate_json> <out_json>
"""
import os, sys, json, argparse
_HERE = os.path.dirname(os.path.abspath(__file__))
for p in (_HERE, os.path.join(_HERE, '..', 'lib'), os.path.join(_HERE, '..', 'sandbox')):
    sys.path.insert(0, p)
import paths02 as P
import log_tool
import model as M
import numpy as np
import pandas as pd

LOG = os.path.join(P.S02_LOGS, 'experiment_log.jsonl')


def block_permute(df, ycol, blocksize=5, seed=20260924):
    """标准空间块置换：置换块**均值**、保留块内残差。

    这样既破坏块间结构（打散空间趋势），又保持每个块的样本量与块内分布，
    不产生尺寸错配。

    注意（2026-09-24 修正）：必须重排块均值的**取值**并贴回原块标签。早先写成
    `uniq.loc[rng.permutation(uniq.index)]`（只重排索引顺序），随后 `blk.map(shuffled)`
    按标签取值必然取回原值 → 置换退化为恒等，负对照失效（实测 corr=1.000）。
    """
    rng = np.random.default_rng(seed)
    blk = pd.Series(list(zip(df['row'] // blocksize, df['col'] // blocksize)),
                    index=df.index)
    bmean = df[ycol].groupby(blk).transform('mean')
    resid = df[ycol].to_numpy(float) - bmean.to_numpy(float)
    uniq = bmean.groupby(blk).first()                       # 每个块的均值
    shuffled = pd.Series(rng.permutation(uniq.to_numpy(float)), index=uniq.index)
    out = df.copy()
    out[ycol] = blk.map(shuffled).to_numpy(float) + resid
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('candidate'); ap.add_argument('out')
    a = ap.parse_args(argv)
    cand = json.load(open(a.candidate, encoding='utf-8'))

    B = pd.read_csv(os.path.join(P.SANDBOX_INPUTS, 'zone_B_devval.csv'))
    mask = pd.read_csv(os.path.join(P.SANDBOX_INPUTS, 'spatial_mask.csv'))
    B = B.merge(mask[['Grid_ID', 'row', 'col']], on='Grid_ID', how='left')
    mdl = cand.get('model')
    if mdl is None:
        raise SystemExit('candidate has no fitted model; run Experiment Agent first')

    rmse_real = M.rmse(B[M.Y], M.predict(mdl, B))
    rng = np.random.default_rng(7)

    B1 = B.copy(); B1[M.Y] = rng.permutation(B1[M.Y].to_numpy())
    rmse_nc1 = M.rmse(B1[M.Y], M.predict(mdl, B1))

    B2 = block_permute(B, M.Y)
    rmse_nc2 = M.rmse(B2[M.Y], M.predict(mdl, B2))

    B3 = B.copy(); B3[M.Y] = rng.normal(B[M.Y].mean(), B[M.Y].std(), len(B))
    rmse_nc3 = M.rmse(B3[M.Y], M.predict(mdl, B3))

    ctrls = dict(NC1_row_shuffle=rmse_nc1, NC2_block_permute=rmse_nc2, NC3_random_target=rmse_nc3)
    # 负对照「通过（未被愚弄）」= 各对照 RMSE >= 真实 RMSE
    passed = {k: bool(v >= rmse_real) for k, v in ctrls.items()}
    verdict = 'not_fooled' if all(passed.values()) else 'fooled_suggest_drop'

    cand['falsification'] = dict(rmse_real=rmse_real, controls=ctrls,
                                 control_passed=passed, verdict=verdict)
    with open(a.out, 'w', encoding='utf-8') as f:
        json.dump(cand, f, ensure_ascii=False, indent=2)

    log_tool.append(cand['id'], 'falsification', logpath=LOG,
                    rmse_real=rmse_real, **ctrls, verdict=verdict)
    print(json.dumps(dict(id=cand['id'], rmse_real=rmse_real, controls=ctrls,
                          verdict=verdict), ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
