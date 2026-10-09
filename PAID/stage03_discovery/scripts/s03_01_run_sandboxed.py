"""
Stage 03 沙箱运行器
====================
与 Stage 02 的 sandbox/run_sandboxed.py 等价，但预算上限**按 Stage 01 冻结值**放宽：

  Stage 01 constraints/hard_constraints.json（冻结）：
    budget.total_fit_budget = 5000
    budget.per_round_max_candidates = 50
    budget.freeze_max = 8

Stage 02 的运行器把 max_fits 写死为 2000（平台冒烟用），不足以支撑 Stage 03 的
多轮自主探索循环。本运行器不改动 Stage 02 任何冻结产物，仅以 Stage 03 自己的
限值激活同一套访问守卫（sandbox/access_guard.py）——权限模型逐字不变。

用法：
  PAID_ACTOR="Discovery Agent" python3 stage03_discovery/scripts/s03_01_run_sandboxed.py \
        stage03_discovery/scripts/s03_02_symreg_search.py
"""
import sys, os, runpy
_HERE = os.path.dirname(os.path.abspath(__file__))
S03 = os.path.dirname(_HERE)
PROJ = os.path.dirname(S03)
S02 = os.path.join(PROJ, 'stage02_platform')
for p in (os.path.join(S02, 'sandbox'), os.path.join(S02, 'lib'), os.path.join(S02, 'agents'), S02):
    if p not in sys.path:
        sys.path.insert(0, p)
import access_guard as G

# 冻结上限：total_fit_budget=5000（Stage 01）。其余为运行期安全护栏。
DEFAULT_LIMITS = dict(max_open_calls=500000, max_seconds=1800, max_fits=5000)


def main(argv):
    if len(argv) < 2:
        print(__doc__); return 2
    script, rest = argv[1], argv[2:]
    actor = os.environ.get('PAID_ACTOR', os.path.basename(script).replace('.py', ''))
    G.activate(actor=actor, limits=DEFAULT_LIMITS)
    code = 0
    sys.argv = [script] + rest
    try:
        runpy.run_path(script, run_name='__main__')
    except SystemExit as e:
        code = int(e.code or 0)
    except G.AccessDenied as e:
        G.shutdown('access_denied'); print('[sandbox] ACCESS DENIED:', e); return 3
    finally:
        if G.status()['active']:
            G.shutdown('ok' if code == 0 else 'exit_%d' % code)
    return code


if __name__ == '__main__':
    raise SystemExit(main(sys.argv))
