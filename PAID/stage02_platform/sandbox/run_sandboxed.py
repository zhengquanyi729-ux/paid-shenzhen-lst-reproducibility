"""
Stage 02 沙箱运行器
===================
在**激活访问守卫之后**再运行目标 Agent 脚本，确保发现侧任何越界读取都被拦截。

用法：
  python sandbox/run_sandboxed.py <agent_script.py> [args...]
环境变量：PAID_ACTOR 指定记录用角色名。
"""
import sys, os, runpy
_HERE = os.path.dirname(os.path.abspath(__file__))
S02 = os.path.dirname(_HERE)
for p in (_HERE, os.path.join(S02, 'lib'), S02):
    if p not in sys.path:
        sys.path.insert(0, p)
import paths02 as P
import access_guard as G

DEFAULT_LIMITS = dict(max_open_calls=200000, max_seconds=600, max_fits=2000)


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
