"""
S05.3 Stage 05 清单与自验证
=============================
生成 `manifests/stage05_hashes.txt`（Stage 05 全部产物 SHA-256），并核对
本轮结果与上游（Stage 03/04）的一致性。**不修改任何 Stage 03/04 冻结产物**。

检查项：
  V1 清单：stage05_hashes.txt 中除自身外逐条 SHA-256 复算一致
  V2 复现 Stage 04：Baseline B 脚本在 A 上重拟合候选得到的 C 区 ΔRMSE
                    与 Stage 04 发布值逐位一致（< 1e-9）
  V3 候选未改：S03-H10-GREEDY.json 的 canon_hash 与 Stage 03 冻结登记一致
  V4 负对照成立：打乱目标的随机森林在 C 区 RMSE 显著差于真随机森林
  V5 图件齐全：figures/ 下 7 图 × 4 格式 = 28 个文件存在（矢量 PDF/SVG + 600 dpi PNG/TIFF）
  V6 上游未被动：Stage 04 的 s04_03_verify.py 复算仍全过
  V7–V10 见下（冻结日志未污染 / 外部复现 / Baseline D / 引用一致）
  V11 图件分辨率达标：每张 PNG 宽度 ≥ 2500 px（≥ 106 mm @600 dpi；最窄图为 120 mm 地图）

用法：python3 stage05_paper/scripts/s05_03_manifest_verify.py
"""
import os, sys, json, hashlib, subprocess

_HERE = os.path.dirname(os.path.abspath(__file__))
S05 = os.path.dirname(_HERE)
PROJ = os.path.dirname(S05)
for _p in (os.path.join(PROJ, 'stage02_platform', 'agents'),
           os.path.join(PROJ, 'stage02_platform', 'lib'),
           os.path.join(PROJ, 'stage02_platform', 'sandbox'),
           os.path.join(PROJ, 'stage03_discovery', 'lib'),
           os.path.join(PROJ, 'stage03_discovery', 'agents')):
    sys.path.insert(0, _p)

import paths03 as P3
import paths02 as P
from independent_validator import canon_hash

MAN = os.path.join(S05, 'manifests', 'stage05_hashes.txt')
RESULTS04 = os.path.join(PROJ, 'stage04_validation', 'reports', 's04_validation_results.json')
BB = os.path.join(S05, 'reports', 'baselineB.json')
EXT = os.path.join(S05, 'reports', 'external_replication.json')
BD = os.path.join(S05, 'reports', 'baselineD.json')


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for c in iter(lambda: f.read(1 << 20), b''):
            h.update(c)
    return h.hexdigest()


def collect():
    files = []
    for sub in ('scripts', 'manuscript', 'reports', 'figures', 'repro'):
        d = os.path.join(S05, sub)
        for root, _, fns in os.walk(d):
            for fn in sorted(fns):
                if fn.endswith('.pyc') or '__pycache__' in root:
                    continue
                if fn == 'verification.json':      # 自验证输出自身会随运行改变，跳过
                    continue
                files.append(os.path.join(root, fn))
    return sorted(files)


def write_manifest():
    files = collect()
    os.makedirs(os.path.dirname(MAN), exist_ok=True)
    lines = ['# Stage 05 SHA-256 manifest (excludes this file)']
    for p in files:
        rel = os.path.relpath(p, PROJ)
        lines.append('%s  %10d  %s' % (sha256_file(p), os.path.getsize(p), rel))
    open(MAN, 'w', encoding='utf-8').write('\n'.join(lines) + '\n')
    print('[manifest] wrote %d entries -> %s' % (len(files), os.path.basename(MAN)))
    return files


def main():
    checks = []

    def chk(cid, name, ok, detail=''):
        checks.append(dict(id=cid, name=name, ok=bool(ok), detail=detail))
        print('%s %-4s %s%s' % ('[OK] ' if ok else '[FAIL]', cid, name,
                                (' | ' + detail) if detail else ''))

    # ---- 生成清单
    files = write_manifest()

    # ---- V1 清单复算
    bad = []
    for ln in open(MAN, encoding='utf-8'):
        ln = ln.rstrip('\n')
        if not ln or ln.startswith('#'):
            continue
        parts = ln.split('  ')
        h = parts[0]; rel = parts[-1]
        full = os.path.join(PROJ, rel)
        if not os.path.exists(full) or sha256_file(full) != h:
            bad.append(rel)
    chk('V1', '清单 SHA-256 逐条复算一致', not bad, 'n=%d mismatch=%s' % (len(files), bad))

    # ---- V2 复现 Stage 04 的 C 区 ΔRMSE
    r4 = json.load(open(RESULTS04, encoding='utf-8'))
    pub = r4['candidates']['S03-H10-GREEDY']['primary_endpoint']['delta_rmse']
    bb = json.load(open(BB, encoding='utf-8'))
    mine = bb['regions']['C']['h10']['delta_vs_baselineA']
    chk('V2', '候选 C 区 ΔRMSE 与 Stage 04 发布值逐位一致', abs(mine - pub) < 1e-9,
        'stage05=%.6f stage04=%.6f' % (mine, pub))

    # ---- V3 候选未被改写
    fr = json.load(open(P3.FROZEN_FILE, encoding='utf-8'))
    reg = {c['id']: c for c in fr['frozen']}
    cand = json.load(open(os.path.join(P3.S03_CAND, 'S03-H10-GREEDY.json'), encoding='utf-8'))
    same = canon_hash(cand) == reg['S03-H10-GREEDY']['canon_hash']
    chk('V3', 'S03-H10-GREEDY 候选 canon_hash 与冻结登记一致', same)

    # ---- V4 负对照
    ctl = bb['negative_control_shuffled_target']['rf']['C']
    real = bb['regions']['C']['rf']['rmse']
    chk('V4', '负对照成立（打乱目标 RF 在 C 明显更差）', ctl > real + 0.2,
        'shuffled=%.4f real=%.4f' % (ctl, real))

    # ---- V5 图件齐全
    figdir = os.path.join(S05, 'figures')
    figs = ('fig0_study_overview', 'fig1_protocol_split', 'fig2_baselineB',
            'fig3_search', 'fig4_validation', 'fig5_external', 'fig6_baselineD')
    need = [os.path.join(figdir, '%s.%s' % (b, e))
            for b in figs for e in ('pdf', 'svg', 'png', 'tif')]
    miss = [os.path.basename(p) for p in need if not os.path.exists(p)]
    chk('V5', '图件齐全（7 图 × 4 格式）', not miss, 'missing=%s' % miss)

    # ---- V6 上游未被动（Stage 04 自验证仍全过）
    r = subprocess.run([sys.executable, os.path.join(PROJ, 'stage04_validation',
                       'scripts', 's04_03_verify.py')], capture_output=True, text=True)
    ok6 = (r.returncode == 0)
    tail = (r.stdout or '').strip().splitlines()[-1] if r.stdout else (r.stderr or '')[-200:]
    chk('V6', 'Stage 04 自验证仍全过（上游未被动）', ok6, tail)

    # ---- V7 Baseline D 未污染冻结日志（审计调用被临时置 no-op）
    logp = os.path.join(P.S02_LOGS, 'experiment_log.jsonl')
    polluted = False
    if os.path.exists(logp):
        txt = open(logp, encoding='utf-8').read()
        polluted = ('BD-freeform' in txt) or ('S05-BaselineD' in txt)
    chk('V7', 'Baseline D 未写入冻结实验日志', not polluted,
        'log=%s' % os.path.basename(logp))

    # ---- V8 Results 3（外部复现）数据产品自洽
    e = json.load(open(EXT, encoding='utf-8'))
    a_star = e['baselineA_star_cv_rmse']
    greedy_cv = e['greedy_rediscovery']['trace'][-1]['cv_rmse']
    n_cc = e.get('dataset', {}).get('n_cells_used')
    chk('V8', 'Results 3 自洽（独立再发现优于匹配线性基线）', greedy_cv < a_star,
        'greedy=%.4f < A*=%.4f | n=%s' % (greedy_cv, a_star, n_cc))

    # ---- V9 Baseline D 消融自洽（无约束臂 A/C 取舍 + 防火墙膨胀为正）
    b = json.load(open(BD, encoding='utf-8'))
    w = b['arm1_winner']; h = b['reference']['h10_constrained']
    infl = b['arm2_firewall_off']['c_rmse_inflation']
    ok9 = (w['cv_rmse'] < h['cv_rmse']) and (w['rmse_C'] > h['rmse_C']) and (infl > 0)
    chk('V9', 'Baseline D 自洽（约束=正则：A 更好但 C 更差；防火墙膨胀>0）', ok9,
        'A: D %.4f<H10 %.4f | C: D %.4f>H10 %.4f | infl %.4f'
        % (w['cv_rmse'], h['cv_rmse'], w['rmse_C'], h['rmse_C'], infl))

    # ---- V10 引言引用与参考文献一致（文献检索后于候选冻结）
    import re as _re
    intro_p = os.path.join(S05, 'manuscript', 'intro_en.md')
    refs_p = os.path.join(S05, 'manuscript', 'references_en.md')
    bib_p = os.path.join(S05, 'manuscript', 'references.bib')
    if all(os.path.exists(p) for p in (intro_p, refs_p, bib_p)):
        intro_txt = open(intro_p, encoding='utf-8').read()
        refs_txt = open(refs_p, encoding='utf-8').read()
        bib_txt = open(bib_p, encoding='utf-8').read()
        # 引用组形如 [2, 3] / [4, 5, 6]，逐组拆出数字
        cited = set()
        for g in _re.findall(r'\[([\d,\s]+)\]', intro_txt):
            for part in g.split(','):
                part = part.strip()
                if part.isdigit():
                    cited.add(int(part))
        # 参考文献列表：行首 [n] 条目
        listed = {int(m) for m in _re.findall(r'^\[(\d+)\]', refs_txt, _re.M)}
        bib_n = bib_txt.count('@')
        ok10 = (cited == listed) and (len(listed) == bib_n) and len(listed) > 0
        chk('V10', '引言引用 [n] 与参考文献/BibTeX 条目一致',
            ok10, 'cited=%d listed=%d bib=%d missing=%s'
            % (len(cited), len(listed), bib_n, sorted(cited - listed)))
    else:
        chk('V10', '引言引用 [n] 与参考文献/BibTeX 条目一致', False, 'files missing')

    # ---- V11 图件分辨率达标（期刊导出：每张 PNG 宽度 ≥ 2500 px）
    try:
        from PIL import Image
        dims = {}
        for b in figs:
            png = os.path.join(figdir, '%s.png' % b)
            if os.path.exists(png):
                dims[b] = Image.open(png).size
        minw = min([w for (w, h) in dims.values()] or [0])
        ok11 = (len(dims) == len(figs)) and minw >= 2500
        chk('V11', '图件分辨率达标（每张 PNG 宽度 ≥ 2500 px）', ok11,
            'n=%d min_width=%d px' % (len(dims), minw))
    except Exception as exc:                              # pragma: no cover
        chk('V11', '图件分辨率达标（每张 PNG 宽度 ≥ 2500 px）', False, str(exc))

    ok_all = all(c['ok'] for c in checks)
    print('\n== Stage 05 verify: %s (%d/%d) =='
          % ('PASS' if ok_all else 'FAIL', sum(c['ok'] for c in checks), len(checks)))
    out = os.path.join(S05, 'reports', 'verification.json')
    json.dump(dict(ok=ok_all, checks=checks), open(out, 'w', encoding='utf-8'),
              ensure_ascii=False, indent=2)
    return 0 if ok_all else 1


if __name__ == '__main__':
    raise SystemExit(main())
