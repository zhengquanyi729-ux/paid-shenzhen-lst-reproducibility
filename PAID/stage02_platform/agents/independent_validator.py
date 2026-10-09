"""
Independent Validator（沙箱之外，独立进程）
==========================================
职责（Table 10）：独立进程持有锁定测试目标值，验证后发布完整结果，
**不执行发现 Agent 请求的参数更新**。
框架依据：§5.3 解封原则；Table 11（C 区仅验证服务持有目标值）；Table 13 七类检验；
          protocol/validation_protocol.json 主终点与通过条件。

安全属性：
  1) 仅接受**已冻结候选**（frozen_candidates.json 登记且规范化哈希一致），
     否则拒绝——防止解封后回传修订过的模型；
  2) 每个候选**只允许一次**验证（validation_runs=1），防止反复解封试错；
  3) 只发布**聚合结论**（RMSE/ΔRMSE、p、CI、通过/失败），
     不向调用方返回任何 C 区逐格目标值；
  4) 全过程写入 append-only 日志。

用法：
  python agents/independent_validator.py --candidate <json> --registry <frozen.json> [--dry-run]
"""
import os, sys, json, hmac, hashlib, argparse, datetime
_HERE = os.path.dirname(os.path.abspath(__file__))
for p in (_HERE, os.path.join(_HERE, '..', 'lib'), os.path.join(_HERE, '..', 'sandbox')):
    sys.path.insert(0, p)
import paths02 as P
import log_tool
import model as M
import numpy as np
import pandas as pd
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

LOG = os.path.join(P.S02_LOGS, 'experiment_log.jsonl')
N_PERM = 199
N_BOOT = 1000


class ValidationRefused(Exception):
    pass


def canon_hash(cand):
    core = {k: cand.get(k) for k in ('id', 'claim', 'expression', 'model')}
    return hashlib.sha256(json.dumps(core, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def decrypt_vault():
    key = open(P.VAULT_KEY, 'rb').read()
    blob = open(P.VAULT_ENC, 'rb').read()
    pt = AESGCM(key).decrypt(blob[:12], blob[12:], b'PAID-stage02-vault-v1')
    import io
    C = pd.read_csv(io.BytesIO(pt))
    return C, hashlib.sha256(pt).hexdigest()


def block_ids(df, bs=5):
    return list(zip(df['row'] // bs, df['col'] // bs))


def delta_rmse(df, mdl_c, mdl_b):
    rc = M.rmse(df[M.Y], M.predict(mdl_c, df))
    rb = M.rmse(df[M.Y], M.predict(mdl_b, df))
    return rb - rc, rb, rc


# ---------------------------------------------------------------- 独立复算（复核修正）
# 复核修正（2026-09-27）：下面两项在**本验证进程内自行复算**，不采信候选 JSON 里由发现侧
# 写下的 verdict。原先 5 个通过条件里有 2 个（physics_audit_pass / negative_controls_not_fooled）
# 直接读候选的自报字段，等于让"被检验方自己判卷"。判据本身不变，改变的只是"由谁计算"。
_DIR_PRESET = ['必须降温', '必须升温', '必降温', '必升温', '降温效应', '增温效应',
               '导致降温', '导致升温', '引起降温', '引起升温', '证明了因果', '因果关系']
_OVERREACH = ['已验证的物理定律', '能量闭合', '能量守恒成立', '因果', '调控机制']
TERM_SCALE_LIMIT = 1000.0


def _as_ast(terms):
    """把两种冻结表达式形式的项统一成 AST 列表，供独立复算使用。

    平台冻结了两种 schema：线性形式（`form='linear'`，项是协变量名字符串，如 'NDVI_mean'）
    与符号表达式形式（`form='expr'`，项是 AST dict）。独立复算须对两者都成立，
    故把字符串项归一为等价的 `{'op':'var','name':...}`；AST 项原样返回。
    """
    return [({'op': 'var', 'name': t} if isinstance(t, str) else t) for t in (terms or [])]


def _max_term_scale(df, terms):
    """独立复算项尺度 max|term|（与发现侧 PA7 同一判据、同一标准化规则，但独立实现）。"""
    ast = _as_ast(terms)
    vs = sorted(set().union(*[M.expr_vars(t) for t in ast]))
    mu = {v: float(df[v].mean()) for v in vs}
    sd = {v: float(df[v].std(ddof=0)) or 1.0 for v in vs}
    Z = np.nan_to_num(M.expr_design(df, ast, mu, sd), nan=0.0, posinf=0.0, neginf=0.0)
    return float(np.max(np.abs(Z[:, 1:])))


def audit_independent(cand, A):
    """独立复算物理审计的**硬门**（PA3 因果过度延伸 / PA4 无方向预设 / PA5 测量边界 / PA7 数值条件）。"""
    claim = cand.get('claim', '') or ''
    expr = (cand.get('expression') or {}).get('expr', '') or ''
    terms = (cand.get('expression') or {}).get('terms') or []
    over = [w for w in _OVERREACH if w in claim]
    dire = [w for w in _DIR_PRESET if w in claim]
    badm = ('SVF' in expr and '5 m' in claim) or ('重采样' in claim and '观测' in claim)
    scale = _max_term_scale(A, terms) if terms else None
    items = {'PA3_overreach': not over, 'PA4_no_direction': not dire,
             'PA5_measurement_boundary': not badm,
             'PA7_term_scale': (scale is None) or (scale <= TERM_SCALE_LIMIT)}
    return dict(verdict='pass' if all(items.values()) else 'fail', items=items,
                max_term_scale=scale, limit=TERM_SCALE_LIMIT, hits=dict(over=over, dir=dire))


def controls_independent(cand, B, mdl_b, n_perm=199):
    """独立复算 B 区负对照地板（NC1–NC3）与置换有效性断言。判据与发现侧一致。"""
    mdl = cand['model']
    real = M.rmse(B[M.Y], M.predict(mdl, B))
    rng = np.random.default_rng(7)
    B1 = B.copy(); B1[M.Y] = rng.permutation(B1[M.Y].to_numpy())
    nc1 = M.rmse(B1[M.Y], M.predict(mdl, B1))
    blk = pd.Series(list(zip(B['row'] // 5, B['col'] // 5)), index=B.index)
    bmean = B[M.Y].groupby(blk).transform('mean')
    resid = B[M.Y].to_numpy(float) - bmean.to_numpy(float)
    uniq = bmean.groupby(blk).first()
    sh = pd.Series(rng.permutation(uniq.to_numpy(float)), index=uniq.index)
    y2 = blk.map(sh).to_numpy(float) + resid
    B2 = B.copy(); B2[M.Y] = y2
    nc2 = M.rmse(B2[M.Y], M.predict(mdl, B2))
    B3 = B.copy(); B3[M.Y] = rng.normal(B[M.Y].mean(), B[M.Y].std(), len(B))
    nc3 = M.rmse(B3[M.Y], M.predict(mdl, B3))
    corr_sanity = float(np.corrcoef(B[M.Y].to_numpy(float), y2)[0, 1])
    ok = all(v >= real for v in (nc1, nc2, nc3))
    return dict(verdict='not_fooled' if ok else 'fooled_suggest_drop',
                rmse_real=real, controls=dict(NC1_row_shuffle=nc1, NC2_block_permute=nc2,
                                              NC3_random_target=nc3),
                perm_corr_sanity=corr_sanity,
                floor_note='NC1–NC3 为地板式体检，检验力弱（仅能淘汰零技巧模型）。')


def validate(cand, registry, dry_run=False):
    # ---- 1) 冻结校验
    reg = {c['id']: c for c in registry['frozen']}
    if cand['id'] not in reg:
        raise ValidationRefused('候选 %s 未在冻结登记中——拒绝解封' % cand['id'])
    h = canon_hash(cand)
    if h != reg[cand['id']]['canon_hash']:
        raise ValidationRefused('候选哈希与冻结登记不一致（可能被解封后修订）——拒绝')
    if not dry_run and reg[cand['id']].get('validation_runs', 0) >= 1:
        raise ValidationRefused('候选 %s 已验证过一次（validation_runs=1 上限）——拒绝重复解封'
                                % cand['id'])

    # ---- 2) 解封
    C, plain_sha = decrypt_vault()
    mask = pd.read_csv(os.path.join(P.S01, 'split', 'analysis_split.csv'))
    C = C.merge(mask[['Grid_ID', 'row', 'col']], on='Grid_ID', how='left')
    A = pd.read_csv(os.path.join(P.SANDBOX_INPUTS, 'zone_A_open.csv'))
    # B 区用于**独立复算**负对照地板（复核修正 2026-09-27）——不采信候选自报的 falsification。
    B = pd.read_csv(os.path.join(P.SANDBOX_INPUTS, 'zone_B_devval.csv'))
    try:
        smask = pd.read_csv(os.path.join(P.SANDBOX_INPUTS, 'spatial_mask.csv'))[['Grid_ID', 'row', 'col']]
        B = B.merge(smask, on='Grid_ID', how='left')
    except Exception:
        pass

    # ---- 3) 主终点
    # Baseline A 按**冻结规格**拟合并仅在 A 区拟合，与被验证候选的表达式无关
    # （否则若候选只含部分变量，基线会被同款裁窄，比较失真）。
    mdl_b = M.fit_linear(A, M.BASELINE_A_TERMS)
    mdl_c = cand['model']                   # 候选：冻结时固定，验证阶段不得再拟合
    d_obs, rb, rc = delta_rmse(C, mdl_c, mdl_b)

    # ---- 4) 空间块置换检验（固定模型；标准做法 = 置换块均值、保留块内残差）
    C = C.reset_index(drop=True)
    rng = np.random.default_rng(20260924)
    blk = pd.Series(list(zip(C['row'] // 5, C['col'] // 5)), index=C.index)
    groups = {b: g.index.to_numpy() for b, g in C.groupby(blk)}
    blocks = list(groups)
    bmean = C[M.Y].groupby(blk).transform('mean')
    resid = C[M.Y].to_numpy(float) - bmean.to_numpy(float)
    ymean = bmean.groupby(blk).first()
    pc_b = M.predict(mdl_b, C); pc_c = M.predict(mdl_c, C)
    null = np.empty(N_PERM)
    for i in range(N_PERM):
        # 关键（2026-09-24 修正）：重排块均值的**取值**并贴回原块标签。
        # 旧写法 ymean.loc[rng.permutation(ymean.index)] 只重排索引顺序，再用 blk.map(sh)
        # 按标签取值必然取回原值，置换退化为恒等（null 恒等于 d_obs → p_perm 恒为 1.0，
        # 主终点永远无法通过）。这是一个只会「假阴性」、不会「假阳性」的严重缺陷。
        sh = pd.Series(rng.permutation(ymean.to_numpy(float)), index=ymean.index)
        yperm = blk.map(sh).to_numpy(float) + resid
        rc_n = np.sqrt(np.mean((yperm - pc_c) ** 2))
        rb_n = np.sqrt(np.mean((yperm - pc_b) ** 2))
        null[i] = rb_n - rc_n
    p_perm = float((1 + np.sum(null >= d_obs)) / (1 + N_PERM))

    # 置换有效性断言（复核修正 2026-09-24/27）：块置换必须真正改变**取值**，
    # 否则是"只重排索引"的恒等置换缺陷——此时 null 恒等于 d_obs、p_perm 恒为 1.0，
    # 该缺陷只会造成假阴性。任何 corr ≥ 0.9 都视为置换退化，拒绝发布结论。
    sh_chk = pd.Series(rng.permutation(ymean.to_numpy(float)), index=ymean.index)
    yperm_chk = blk.map(sh_chk).to_numpy(float) + resid
    perm_corr = float(np.corrcoef(C[M.Y].to_numpy(float), yperm_chk)[0, 1])
    if not (perm_corr < 0.9):
        raise ValidationRefused('空间块置换退化为恒等（corr=%.3f）——置换检验无效，拒绝发布结论'
                                % perm_corr)

    # ---- 5) 空间块自助 95% CI
    boot = np.empty(N_BOOT)
    for i in range(N_BOOT):
        pick = rng.choice(len(blocks), size=len(blocks), replace=True)
        sel = np.concatenate([groups[blocks[j]] for j in pick])
        d, _, _ = delta_rmse(C.iloc[sel], mdl_c, mdl_b)
        boot[i] = d
    ci = [float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5))]

    # ---- 6) 通过条件（protocol/validation_protocol.json 主终点）
    # 复核修正（2026-09-27）：physics_audit / negative_controls 两项不再读候选 JSON 里
    # 由发现侧写下的 verdict，而是**在本验证进程内用 B/A 区数据独立复算**。
    # 判据（阈值、措辞、项尺度上限）与发现侧一致，改变的只是"由谁计算"。
    audit_ind = audit_independent(cand, A)
    ctrl_ind = controls_independent(cand, B, mdl_b)
    phys = audit_ind['verdict'] == 'pass'
    nc_ok = ctrl_ind['verdict'] == 'not_fooled'
    cond = {'delta_rmse_pos': d_obs > 0, 'perm_p_lt_0.05': p_perm < 0.05,
            'ci_excludes_zero': (ci[0] > 0 or ci[1] < 0),
            'physics_audit_pass': bool(phys), 'negative_controls_not_fooled': bool(nc_ok)}
    passed = all(cond.values())

    # 自报值仅作对照记录，**不参与**判定
    self_report = {
        'physics_audit': (cand.get('physics_audit') or {}).get('verdict'),
        'falsification': (cand.get('falsification') or {}).get('verdict'),
        'note': '发现侧自报值，仅供对照；判定仅采用 independent_audit / independent_controls。'}

    result = dict(
        candidate=cand['id'], canon_hash=h, validated_at=datetime.datetime.now().isoformat(timespec='seconds'),
        n_C=int(len(C)), vault_plaintext_sha256=plain_sha,
        primary_endpoint=dict(statistic='RMSE_C 与 ΔRMSE(vs Baseline A)',
                              rmse_baselineA=rb, rmse_candidate=rc, delta_rmse=d_obs,
                              perm_p=p_perm, n_perm=N_PERM, perm_corr_sanity=perm_corr,
                              ci95_delta=ci, n_bootstrap=N_BOOT),
        conditions=cond, passed=bool(passed),
        independent_audit=audit_ind,
        independent_controls=ctrl_ind,
        self_reported=self_report,
        caveats=['平台冒烟测试：候选为预注册 Baseline A 占位，非科学发现；'
                 '结论不得作为研究结果引用'] if cand.get('claim', '').startswith('（平台占位') else [],
        publish_rule='仅发布聚合结论，不返回 C 区逐格目标值；失败同样完整发布。')
    return result, reg


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--candidate', required=True)
    ap.add_argument('--registry', default=P.FROZEN_FILE)
    ap.add_argument('--out', default=P.VALIDATION_OUT)
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args(argv)
    cand = json.load(open(a.candidate, encoding='utf-8'))
    registry = json.load(open(a.registry, encoding='utf-8'))
    try:
        result, reg = validate(cand, registry, dry_run=a.dry_run)
    except ValidationRefused as e:
        log_tool.append(cand.get('id', '?'), 'validation_refused', logpath=LOG, reason=str(e))
        print(json.dumps(dict(refused=True, reason=str(e)), ensure_ascii=False, indent=2))
        return 2
    os.makedirs(P.S02_REPORTS, exist_ok=True)
    with open(a.out, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    log_tool.append(cand['id'], 'validation_published', logpath=LOG,
                    passed=result['passed'], delta_rmse=result['primary_endpoint']['delta_rmse'],
                    perm_p=result['primary_endpoint']['perm_p'],
                    ci95=result['primary_endpoint']['ci95_delta'], dry_run=a.dry_run)
    if not a.dry_run:
        for c in registry['frozen']:
            if c['id'] == cand['id']:
                c['validation_runs'] = c.get('validation_runs', 0) + 1
                c['last_result'] = dict(passed=result['passed'],
                                        delta_rmse=result['primary_endpoint']['delta_rmse'])
        with open(a.registry, 'w', encoding='utf-8') as f:
            json.dump(registry, f, ensure_ascii=False, indent=2)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
