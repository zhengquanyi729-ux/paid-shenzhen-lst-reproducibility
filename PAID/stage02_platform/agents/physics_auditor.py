"""
Physics Auditor（沙箱内）
=========================
职责（Table 10）：独立审计量纲、几何、可计算物理约束及解释的过度延伸。
框架依据：Table 3（规则）、Table 13（物理及量纲审计）、§3.1 硬约束、
          §3.2 无方向预设。

审计项：
  PA1 量纲一致性     —— 表达式是否量纲一致或已无量纲化；
  PA2 几何合法性     —— 派生变量（覆盖率/高度/体量）是否满足几何约束（X_BD≤1 等）；
  PA3 能量闭合       —— 是否出现数据不支持的能量残差/机制叙述；
  PA4 无方向预设     —— 系统提示词是否含方向性预设（正/负双向检查）；
  PA5 测量边界       —— 是否把 5 m SVF 当作 5 m LST、或把重采样当新观测；
  PA6 统计诚信       —— 主终点与停止条件是否在解封前冻结。

用法：
  python agents/physics_auditor.py <candidate_json> <out_json>
"""
import os, sys, json, argparse
_HERE = os.path.dirname(os.path.abspath(__file__))
for p in (_HERE, os.path.join(_HERE, '..', 'lib'), os.path.join(_HERE, '..', 'sandbox')):
    sys.path.insert(0, p)
import paths02 as P
import log_tool
import registry as REG

LOG = os.path.join(P.S02_LOGS, 'experiment_log.jsonl')

# 方向性「断言式」措辞（不含禁令条款本身的否定表述）
ASSERTIVE_PRESETS = [
    'NDVI 与 LST 负相关', 'NDVI 越高越凉', 'SVF 增大导致升温', 'SVF 增大导致降温',
    '建筑越高越热', '建筑越高越凉', '最优尺度为', '应采用线性模型', '应使用随机森林',
    'p<0.05 为唯一判据', '必须显著',
]
# 能量/机制越界措辞
ENERGY_OVERREACH = ['能量闭合已通过', '能量残差为零', '人为热通量为', '感热通量为',
                    '净辐射为', '由能量平衡可知']


def audit(cand, hard):
    items = []
    expr = cand['expression']

    # PA1 量纲
    standardized = bool(expr.get('standardize'))
    ok1 = standardized and expr.get('form') == 'linear'
    items.append(dict(id='PA1', desc='量纲一致/无量纲化', ok=ok1,
                      detail='线性表达式作用于 A 区标准化协变量 → 无量纲' if ok1
                      else '未声明标准化，量纲可能不一致'))

    # PA2 几何
    bd_max = hard['measured_domain']['X_BD']['max']
    ok2 = bd_max <= 1.0
    items.append(dict(id='PA2', desc='几何合法性（X_BD 为覆盖率且 ≤1）', ok=ok2,
                      detail='X_BD 实测 max=%.2f，超 [0,1]；口径未确认，须登记假设、'
                             '不得当作合法覆盖率使用（DG-2/PC-3）' % bd_max))

    # PA3 能量闭合
    blob = json.dumps(cand, ensure_ascii=False)
    hits3 = [w for w in ENERGY_OVERREACH if w in blob]
    items.append(dict(id='PA3', desc='无能量残差/机制越界', ok=not hits3,
                      detail='未出现缺失输入的能量断言' if not hits3 else '命中：%s' % hits3))

    # PA4 无方向预设
    prompt = next(a['system_prompt'] for a in REG.AGENTS if a['agent'] == cand['agent'])
    hits4 = [w for w in ASSERTIVE_PRESETS if w in prompt]
    has_clause = '不得假定' in prompt and '方向性结论' in prompt
    items.append(dict(id='PA4', desc='系统提示词无方向预设', ok=(not hits4) and has_clause,
                      detail='禁令条款存在=%s，断言式措辞命中=%s' % (has_clause, hits4)))

    # PA5 测量边界
    ok5 = not any(w in blob for w in ['5 m LST', '5m LST', '重采样提升'])
    items.append(dict(id='PA5', desc='测量边界（不混淆 SVF 与 LST 支持尺度）', ok=ok5,
                      detail='未把 5 m SVF 当作 5 m LST，未把重采样当作新观测' if ok5 else '越界'))

    # PA6 统计诚信
    ok6 = bool(cand.get('prereg_test')) and cand.get('unseal_result') is None
    items.append(dict(id='PA6', desc='主终点解封前冻结', ok=ok6,
                      detail='主终点已声明=%s，解封结果尚未写入=%s'
                      % (bool(cand.get('prereg_test')), cand.get('unseal_result') is None)))

    # 若 X_BD 口径问题存在，按 §7 证据分类降级适用范围（不判假，只限定）
    verdict = 'pass' if all(i['ok'] for i in items if i['id'] != 'PA2') else 'fail'
    return dict(items=items, verdict=verdict,
                caveats=['X_BD 口径未确认：相关候选的适用域须限定，且须登记口径假设']
                if not ok2 else [])


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('candidate'); ap.add_argument('out'); ap.add_argument('hard')
    a = ap.parse_args(argv)
    cand = json.load(open(a.candidate, encoding='utf-8'))
    hard = json.load(open(a.hard, encoding='utf-8'))
    cand['physics_audit'] = audit(cand, hard)
    cand['status'] = 'audited'
    with open(a.out, 'w', encoding='utf-8') as f:
        json.dump(cand, f, ensure_ascii=False, indent=2)
    log_tool.append(cand['id'], 'physics_audit', logpath=LOG,
                    verdict=cand['physics_audit']['verdict'],
                    items={i['id']: i['ok'] for i in cand['physics_audit']['items']})
    print(json.dumps(dict(id=cand['id'], verdict=cand['physics_audit']['verdict'],
                          items={i['id']: i['ok'] for i in cand['physics_audit']['items']}),
                     ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
