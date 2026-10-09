"""
S02.4 追加日志与防篡改验证
==========================
框架依据：§4.3「每轮实验必须生成只追加记录，不得覆盖失败结果」；
Table 12 Experiment protocol「失败记录策略」；Table 19「为追求创新选择性报告」防范。

做三件事：
  1) 校验现有日志哈希链；
  2) **篡改演示**：在副本上分别做「改字段 / 删记录 / 换序 / 尾插伪造」，
     证明 verify() 能逐一定位；
  3) 说明失败记录策略（失败候选同样入链，不得删除）。
"""
import sys, os, json, shutil, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lib'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'sandbox'))
import paths02 as P
import log_tool

CREATED = '2026-09-24'
VERSION = 'stage02-log-v1'
os.makedirs(P.S02_REPORTS, exist_ok=True)

base = log_tool.verify()
tamper = {}


def trial(name, mut):
    tmp = os.path.join(tempfile.mkdtemp(), 'log.jsonl')
    shutil.copyfile(P.LOG_FILE, tmp)
    recs = log_tool.read_all(tmp)
    mut(recs)
    with open(tmp, 'w', encoding='utf-8') as f:
        for r in recs:
            f.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + '\n')
    tamper[name] = log_tool.verify(tmp)
    shutil.rmtree(os.path.dirname(tmp), ignore_errors=True)


if os.path.exists(P.LOG_FILE) and base['n'] >= 4:
    trial('modify_field', lambda r: r[1].__setitem__('action', 'tampered'))
    trial('delete_record', lambda r: r.pop(1))
    trial('reorder', lambda r: (r.insert(1, r.pop(2)) if len(r) > 2 else None))
    trial('append_forged', lambda r: r.append(dict(seq=len(r) + 1, ts='2026-01-01T00:00:00',
                                                   actor='x', action='forged', detail={},
                                                   prev='0' * 64, hash='0' * 64)))
    detected = {k: (not v['ok']) for k, v in tamper.items()}
else:
    detected = {}

ok = base['ok'] and (not detected or all(detected.values()))
R = dict(version=VERSION, created=CREATED, status='OK' if ok else 'FAIL',
         log=os.path.relpath(P.LOG_FILE, P.PROJ), chain_ok=base['ok'], n_records=base['n'],
         head=base['head'], tail=base['tail'],
         tamper_detected=detected, tamper_detail=tamper,
         policy='失败候选与负对照结果同样写入本链，禁止删除或覆盖；'
                '每轮实验前记录预算与提示词哈希，实验后记录指标与判定。')
with open(os.path.join(P.S02_REPORTS, 's02_04_log.json'), 'w', encoding='utf-8') as f:
    json.dump(R, f, ensure_ascii=False, indent=2)

L = ['# S02.4 追加日志与防篡改验证\n', '版本 %s。状态 **%s**。\n' % (VERSION, R['status']),
     '日志：`%s`，共 %d 条，链头 `%s`，链尾 `%s`，哈希链自洽 **%s**。\n'
     % (R['log'], base['n'], base['head'], base['tail'], base['ok']),
     '## 篡改检测\n', '| 篡改方式 | 是否检出 | 首个不一致记录 |', '|---|---|---|']
for k, v in tamper.items():
    L.append('| %s | %s | %s |' % (k, '✓ 检出' if not v['ok'] else '✗ 未检出', v['first_bad']))
L.append('\n> 任何删改、插入、换序都会改变 `hash` 或 `prev`，从而被 `verify()` 定位并拒绝。')
with open(os.path.join(P.S02_REPORTS, 's02_04_log.md'), 'w', encoding='utf-8') as f:
    f.write('\n'.join(L))

print(json.dumps(dict(status=R['status'], n=base['n'], chain_ok=base['ok'],
                      tamper_detected=detected), ensure_ascii=False, indent=2))
if not ok:
    sys.exit(1)
