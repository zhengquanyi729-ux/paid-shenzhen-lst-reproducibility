"""
Experiment Agent（沙箱内）
==========================
职责（Table 10）：编写实验代码、比较允许的方法、测量开发集表现；记录全部运行。
框架依据：§4.3「每轮实验必须生成只追加记录，不得覆盖失败结果」。

流程：读候选 → 在 A 区拟合 → 在 B 区评估 → 回填 dev_evidence → 追加日志。
不得访问 B 区目标之外的内容，亦不得访问 C 区。

用法：
  python agents/experiment_agent.py <candidate_json> <out_json>
"""
import os, sys, json, argparse
_HERE = os.path.dirname(os.path.abspath(__file__))
for p in (_HERE, os.path.join(_HERE, '..', 'lib'), os.path.join(_HERE, '..', 'sandbox')):
    sys.path.insert(0, p)
import paths02 as P
import log_tool
import model as M
import pandas as pd

LOG = os.path.join(P.S02_LOGS, 'experiment_log.jsonl')


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('candidate'); ap.add_argument('out')
    a = ap.parse_args(argv)
    cand = json.load(open(a.candidate, encoding='utf-8'))

    A = pd.read_csv(os.path.join(P.SANDBOX_INPUTS, 'zone_A_open.csv'))
    B = pd.read_csv(os.path.join(P.SANDBOX_INPUTS, 'zone_B_devval.csv'))
    terms = cand['expression']['terms']

    mdl = M.fit_linear(A, terms)
    ev = dict(A=M.evaluate(mdl, A), B=M.evaluate(mdl, B))
    cand['model'] = mdl
    cand['dev_evidence'] = ev
    cand['status'] = 'dev_tested'
    with open(a.out, 'w', encoding='utf-8') as f:
        json.dump(cand, f, ensure_ascii=False, indent=2)

    log_tool.append(cand['id'], 'dev_fit', logpath=LOG,
                    terms=terms, rmse_A=ev['A']['rmse'], rmse_B=ev['B']['rmse'],
                    r2_A=ev['A']['r2'], r2_B=ev['B']['r2'], n_A=ev['A']['n'], n_B=ev['B']['n'])
    print(json.dumps(dict(id=cand['id'], rmse_A=ev['A']['rmse'], rmse_B=ev['B']['rmse']),
                     ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
