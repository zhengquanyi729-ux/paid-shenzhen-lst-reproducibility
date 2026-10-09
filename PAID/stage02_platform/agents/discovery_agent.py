"""
Discovery Agent（沙箱内）
=========================
职责（Table 10）：自主选择特征、尺度、假设与数学表达式；仅访问开放探索数据。

Stage 02 说明：本阶段的目标是「可运行系统」，故 Discovery Agent 仅按预注册的
Baseline A 规格生成一个占位候选，用于打通登记链路；**不进行任何真实发现**。
真正的符号回归 / 多尺度 / 机器学习搜索属于 Stage 03。

用法：
  python agents/discovery_agent.py <out_json>
"""
import os, sys, json, argparse
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
sys.path.insert(0, os.path.join(_HERE, '..', 'lib'))
sys.path.insert(0, os.path.join(_HERE, '..', 'sandbox'))
import paths02 as P
import registry as REG
import log_tool
import model as M

CREATED = '2026-09-24'


def propose(cand_id='CAND-0001'):
    """返回一个候选登记条目（Table 20 字段）。"""
    return dict(
        id=cand_id, created=CREATED, agent=REG.AGENTS[0]['agent'],
        model_version=REG.MODEL_VERSION, code_version='stage02-platform-v1',
        claim='（平台占位，非科学发现）LST_mean 可用预注册协变量的线性组合描述；'
              '本条目仅用于验证登记—冻结—解封链路。',
        expression=dict(form='linear',
                        terms=['NDVI_mean', 'DEM_mean', 'SVF_mean', 'Road_Dens',
                               'X_BD', 'X_BH', 'X_VolDens'],
                        standardize=True, intercept=True),
        variables={t: '见 constraints/DATA_DICTIONARY.md' for t in M.COVARIATES},
        domain='深圳研究区、单一时相、100 m 网格；A 发现区',
        dev_evidence=None,          # 由 Experiment Agent 填写
        prereg_test='见 protocol/validation_protocol.json 主终点（C 区 RMSE 与 ΔRMSE）',
        physics_audit=None,         # 由 Physics Auditor 填写
        unseal_result=None,         # 由 Independent Validator 填写
        status='proposed')


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('out'); ap.add_argument('--id', default='CAND-0001')
    a = ap.parse_args(argv)
    cand = propose(a.id)
    with open(a.out, 'w', encoding='utf-8') as f:
        json.dump(cand, f, ensure_ascii=False, indent=2)
    log_tool.append(a.id, 'candidate_proposed', logpath=os.path.join(P.S02_LOGS, 'experiment_log.jsonl'),
                    agent=cand['agent'], expression=cand['expression'])
    print(json.dumps(dict(proposed=cand['id'], out=a.out), ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
