"""
S02.5 独立验证服务登记与冻结候选规范
====================================
框架依据：§5.3 解封原则、Table 20 候选登记、Table 12 Validation protocol。

生成：
  registry/candidate_registry.json —— Table 20 登记模板（字段说明）
  registry/frozen_candidates.json  —— 冻结候选登记（供验证服务校验哈希与次数）
  reports/s02_05_validator.json / .md

验证服务由 `agents/independent_validator.py` 实现，运行于沙箱之外。
"""
import sys, os, json, hashlib
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lib'))
import paths02 as P

CREATED = '2026-09-24'
VERSION = 'stage02-validator-v1'
os.makedirs(P.S02_REGISTRY, exist_ok=True)
os.makedirs(P.S02_REPORTS, exist_ok=True)

REGISTRY_FIELDS = [
    ('候选 ID / 时间', '唯一不可修改编号，生成时间，Agent 和代码版本。'),
    ('科学主张', '明确预测关系，避免“影响很大”等模糊表述。'),
    ('数学表达式与变量', '完整公式、量纲、输入来源、变换、尺度。'),
    ('适用域', '空间、时间、地表类型与测量条件。'),
    ('开发证据', '估计、区间、残差、反例、已尝试的检验。'),
    ('预定主检验', '冻结主指标、比较对象、误差处理及失败判据。'),
    ('物理审计', '通过项、无法检验项、假设及理由。'),
    ('测试解封结果', '统一报告通过、失败及所有不确定性。'),
]
template = dict(version=VERSION, created=CREATED,
                framework_ref='Table 20 候选科学发现登记模板',
                fields=[dict(field=f, content=c) for f, c in REGISTRY_FIELDS],
                note='每条候选一行记录；失败候选同样登记，不得删除。')
with open(P.REGISTRY_FILE, 'w', encoding='utf-8') as f:
    json.dump(template, f, ensure_ascii=False, indent=2)

frozen = dict(version=VERSION, created=CREATED,
              rule='仅登记 canon_hash = sha256(canonical({id,claim,expression,model}))；'
                   '每个候选 validation_runs ≤ 1；哈希不一致即拒绝解封。',
              frozen=[])
with open(P.FROZEN_FILE, 'w', encoding='utf-8') as f:
    json.dump(frozen, f, ensure_ascii=False, indent=2)

vp = json.load(open(os.path.join(P.S01, 'protocol', 'validation_protocol.json'), encoding='utf-8'))
R = dict(version=VERSION, created=CREATED, status='OK',
         service='agents/independent_validator.py',
         runs_outside_sandbox=True,
         refusal_rules=['候选未在冻结登记中 → 拒绝',
                        '候选哈希与冻结登记不一致 → 拒绝（防解封后修订）',
                        'validation_runs ≥ 1 → 拒绝重复解封'],
         passes_only=frozenset(['已冻结候选']) and ['已冻结候选'],
         publishes=['RMSE_C', 'ΔRMSE(vs Baseline A)', '空间块置换 p（199 次）',
                    '空间块自助 95% CI（1000 次）', '物理审计判定', '负对照判定'],
         never_returns=['C 区逐格目标值'],
         binds=dict(primary_endpoint=vp['primary_endpoint']['pass_rule'],
                    block_permutation=vp['spatial_inference']['block_permutation'],
                    multiplicity=vp['multiplicity']['control']))
with open(os.path.join(P.S02_REPORTS, 's02_05_validator.json'), 'w', encoding='utf-8') as f:
    json.dump(R, f, ensure_ascii=False, indent=2)

L = ['# S02.5 独立验证服务登记与冻结候选规范\n', '版本 %s。状态 **OK**。\n' % VERSION,
     '服务实现：`%s`（运行于沙箱**之外**）。\n' % R['service'],
     '## 拒绝规则（§5.3）\n']
for r in R['refusal_rules']:
    L.append('- %s' % r)
L += ['\n## 发布内容\n', '- ' + '；'.join(R['publishes']), '',
      '## 绝不回传\n', '- ' + '；'.join(R['never_returns']), '',
      '## 绑定的预注册条件\n', '- 主终点：%s' % R['binds']['primary_endpoint'],
      '- 空间置换：%d 次' % R['binds']['block_permutation'],
      '- 多重比较：%s' % R['binds']['multiplicity']]
with open(os.path.join(P.S02_REPORTS, 's02_05_validator.md'), 'w', encoding='utf-8') as f:
    f.write('\n'.join(L))

print(json.dumps(dict(status='OK', service=R['service'], refusal_rules=len(R['refusal_rules'])),
                 ensure_ascii=False, indent=2))
