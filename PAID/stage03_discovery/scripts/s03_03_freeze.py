"""
S03.3 候选冻结（沙箱之外执行）
================================
读取发现侧在沙箱内写出的 candidate_registry.json，按**预注册、可复现的选择规则**冻结少量候选，
写出：
  registry/candidates/<id>.json     每个冻结候选的完整记录（供独立验证服务单次解封）
  registry/frozen_candidates.json   冻结登记（id + 规范化哈希 + validation_runs=0 等）
  registry/candidate_registry.json  全量候选登记（含未入选者，失败不删除）
  registry/experiment_trajectory.json 完整实验轨迹（各轮 trace + 折信息 + 预算）

预注册选择规则（在 Stage 01 冻结的 budget 之内）：
  R1) 入选条件 = status == 'passed_dev_gain'
      （即：通过物理审计 + 未通过反例测试 + 在 A 区空间分块 CV 上优于冻结 Baseline A）；
  R2) 按 A 区 CV RMSE 升序，最多取 freeze_max=8 个；
  R3) 额外冻结 1 个**参考/安慰剂候选**（冻结 Baseline A 规格本身）：它在验证区主终点上
      按定义 ΔRMSE≈0，用于检验验证服务能否把"零效应"判为不通过（系统判别力自检）。

安全属性：本步骤在沙箱之外，发现 Agent 无法调用（无路径写权限）；哈希由验证侧同一
canon_hash 函数计算，保证冻结内容与解封内容一致。

用法：python stage03_discovery/scripts/s03_03_freeze.py
"""
import os, sys, json, hashlib, datetime
_HERE = os.path.dirname(os.path.abspath(__file__))
S03 = os.path.dirname(_HERE)
PROJ = os.path.dirname(S03)
for p in (os.path.join(S03, 'lib'), os.path.join(PROJ, 'stage02_platform', 'agents')):
    sys.path.insert(0, p)
import paths03 as P3
sys.path.insert(0, os.path.join(PROJ, 'stage02_platform', 'agents'))
from independent_validator import canon_hash   # 与验证侧**同一**哈希实现


def _jsonable(o):
    import numpy as np
    if isinstance(o, dict):
        return {k: _jsonable(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_jsonable(v) for v in o]
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.bool_,)):
        return bool(o)
    return o


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def main():
    raw = json.load(open(P3.RAW_REGISTRY, encoding='utf-8'))
    for d in (P3.S03_REGISTRY, P3.S03_CAND, P3.S03_MANIFEST):
        os.makedirs(d, exist_ok=True)

    cands = raw['candidates']
    freeze_max = raw['budget']['freeze_max']

    # ---- 规则 R1/R2：优于基线且通过全部发现侧门槛者，按 A 区 CV 升序取前 freeze_max 个
    gain = [c for c in cands if c['status'] == 'passed_dev_gain']
    gain.sort(key=lambda c: c['dev_evidence']['cv_rmse'])
    selected = gain[:freeze_max]

    frozen = []
    for rank, c in enumerate(selected, 1):
        c = _jsonable(c)
        ch = canon_hash(c)
        rec = dict(id=c['id'], role='discovery_candidate', rank=rank,
                   canon_hash=ch, validation_runs=0,
                   why='A 区空间分块 CV RMSE=%.4f，优于冻结 Baseline A %.4f（Δ=%+.4f）；'
                       '通过物理审计与反例测试。'
                       % (c['dev_evidence']['cv_rmse'], raw['baselineA_dev_cv_rmse'],
                          c['dev_evidence']['delta_cv_vs_baselineA']),
                   expression=c['expression']['expr'], claim=c['claim'])
        with open(os.path.join(P3.S03_CAND, c['id'] + '.json'), 'w', encoding='utf-8') as f:
            json.dump(c, f, ensure_ascii=False, indent=2)
        frozen.append(rec)

    # ---- 规则 R3：参考/安慰剂候选 = 冻结 Baseline A 规格本身
    ref = next((c for c in cands if c['id'] == 'S03-H01-LIN7'), None)
    if ref is not None:
        ref = _jsonable(ref)
        ch = canon_hash(ref)
        with open(os.path.join(P3.S03_CAND, ref['id'] + '.json'), 'w', encoding='utf-8') as f:
            json.dump(ref, f, ensure_ascii=False, indent=2)
        frozen.append(dict(id=ref['id'], role='reference_placebo', rank=0,
                           canon_hash=ch, validation_runs=0,
                           why='冻结 Baseline A 规格（7 协变量线性）。作为**安慰剂/参考**：'
                               '其验证区 ΔRMSE 按定义为 0，应当被验证服务判为不通过。',
                           expression=ref['expression']['expr'], claim=ref['claim']))

    freeze = dict(version='stage03-freeze-v1',
                  created=datetime.datetime.now().isoformat(timespec='seconds'),
                  source=dict(raw_registry=P3.RAW_REGISTRY,
                              raw_registry_sha256=sha256_file(P3.RAW_REGISTRY),
                              run_tag=raw.get('run_tag'), ran_at=raw.get('ran_at')),
                  budget=raw['budget'],
                  baselineA_dev_cv_rmse=raw['baselineA_dev_cv_rmse'],
                  selection_rule=['R1 入选=status passed_dev_gain（审计通过+反例未通过+优于 Baseline A）',
                                  'R2 按 A 区 CV 升序取前 freeze_max=%d' % freeze_max,
                                  'R3 额外冻结 Baseline A 作为安慰剂/参考（ΔRMSE 应为 0 → 应判不通过）'],
                  n_frozen=len(frozen), frozen=frozen)
    with open(P3.FROZEN_FILE, 'w', encoding='utf-8') as f:
        json.dump(freeze, f, ensure_ascii=False, indent=2)

    # ---- 全量候选登记 + 完整轨迹
    reg = dict(version='stage03-registry-v1', created=freeze['created'],
               baselineA_dev_cv_rmse=raw['baselineA_dev_cv_rmse'],
               baselineA_rmse_B=raw.get('baselineA_rmse_B'),
               folds=raw['folds'], rounds=raw['rounds'], budget=raw['budget'],
               guard=raw.get('guard'),
               status_counts={s: sum(1 for c in cands if c['status'] == s)
                              for s in sorted({c['status'] for c in cands})},
               n_candidates=len(cands), frozen_ids=[f['id'] for f in frozen],
               candidates=cands)
    with open(P3.CANDIDATE_REGISTRY, 'w', encoding='utf-8') as f:
        json.dump(reg, f, ensure_ascii=False, indent=2)

    traj = dict(version='stage03-trajectory-v1', created=freeze['created'],
                run_tag=raw.get('run_tag'), ran_at=raw.get('ran_at'),
                budget=raw['budget'], guard_limits='max_fits=5000（Stage 01 冻结上限）',
                folds=raw['folds'], greedy_trace=raw['greedy_trace'],
                refine_trace=raw['refine_trace'], refine_seed=raw.get('refine_seed'))
    with open(P3.FULL_TRAJECTORY, 'w', encoding='utf-8') as f:
        json.dump(traj, f, ensure_ascii=False, indent=2)

    print('[s03-freeze] frozen %d candidates (+%d ref/placebo) ->'
          % (len(selected), len(frozen) - len(selected)), P3.FROZEN_FILE)
    for fr in frozen:
        print('   %-22s %-20s %s' % (fr['id'], fr['role'], fr['canon_hash'][:16]))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
