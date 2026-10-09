"""
Stage 02 五 Agent 注册表：权限、工具白名单、预算与系统提示词
============================================================
框架依据：Table 10（五单元权限与产出）、Table 11（数据层权限）、Table 12 Agent manifest、
§3.2 无方向预设、§4.3 自主探索循环、§5.3 解封原则。

本模块是「权限」的代码化事实来源：每个 Agent 声明
  - data_access / forbidden_access：可读与禁读的数据层；
  - tools：工具白名单（越界即违规）；
  - budget：候选上限、fit 预算；
  - sandboxed：是否必须在访问守卫内运行；
  - system_prompt：注入提示词（受 §3.2 约束，不得含任何方向性预设）。
"""
import os
S02 = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

MODEL_VERSION = 'PAID-Agent-v0（Stage 02 平台骨架，无语料级目标先验注入）'

# §3.2 通用禁令（写入每个沙箱内 Agent 的提示词，供 Physics Auditor 审计）
NO_DIRECTION_CLAUSE = (
    "禁止在提出或评估候选时预设任何方向性结论：不得假定 NDVI 单调降温、SVF 升/降温、"
    "建筑高度/体量产生某一方向的热响应；不得预设唯一最优空间尺度、固定函数形式、"
    "单一显著阈值或特定交互组合；不得引用旧论文结论或相关矩阵引导发现。"
    "若数据支持不存在稳健关系，应如实给出该结论。")

COMMON_HEAD = (
    "你是一个受物理约束的城市地表热环境自主发现系统中的 {role}。"
    "你可使用的数据严格限定为沙箱工作树 sandbox_root/inputs 中的 A/B 开放数据、"
    "硬约束、数据字典与计算工具；对任何越界路径的读取都会被运行时守卫拒绝并记入日志。"
    "所有实验必须以只追加方式记录，不得覆盖失败结果。")

AGENTS = [
    dict(
        agent='Discovery Agent',
        purpose='自主选择特征、尺度、假设与数学表达式；仅访问开放探索数据。',
        data_access=['A 发现区（sandbox_root/inputs/zone_A_open.csv）'],
        forbidden_access=['B 开发验证区目标（调参用）', 'C 锁定区任何形式（含密文与密钥）',
                          '全域原始数据 data/（含全城 LST 栅格与全表 CSV）', '旧论文结论/相关矩阵'],
        tools=['pandas', 'numpy', 'agents/model.py'],
        budget=dict(candidates_per_round=8, total_fit_budget=2000),
        sandboxed=True,
        system_prompt=None),                      # 由 prompts 生成
    dict(
        agent='Experiment Agent',
        purpose='编写实验代码、比较允许的方法、测量开发集表现；记录全部运行。',
        data_access=['A 发现区', 'B 开发验证区'],
        forbidden_access=['C 锁定区任何形式', '全域原始数据 data/'],
        tools=['pandas', 'numpy', 'agents/model.py', 'sandbox/log_tool.py'],
        budget=dict(candidates_per_round=8, total_fit_budget=2000),
        sandboxed=True,
        system_prompt=None),
    dict(
        agent='Falsification Agent',
        purpose='寻找反例、空间混杂、伪相关与负对照；可建议放弃候选。',
        data_access=['A 发现区', 'B 开发验证区', '分区掩膜（Grid_ID→row/col/zone）'],
        forbidden_access=['C 锁定区任何形式', '全域原始数据 data/'],
        tools=['pandas', 'numpy', 'agents/model.py'],
        budget=dict(negative_controls=3, perms=199),
        sandboxed=True,
        system_prompt=None),
    dict(
        agent='Physics Auditor',
        purpose='独立审计量纲、几何、可计算物理约束及解释的过度延伸。',
        data_access=['hard_constraints.json', 'DATA_DICTIONARY.md', 'no_direction_preset.md',
                     '分区掩膜'],
        forbidden_access=['C 锁定区任何形式', '全域原始数据 data/'],
        tools=['json', 'agents/audit.py'],
        budget=dict(audits_per_candidate=1),
        sandboxed=True,
        system_prompt=None),
    dict(
        agent='Independent Validator',
        purpose='独立进程持有锁定测试目标值，验证后发布完整结果，不执行发现方请求的参数更新。',
        data_access=['vault/zone_C_targets.enc + vault/validator_key.bin（C 锁定区，密文级隔离）',
                     '已冻结候选登记'],
        forbidden_access=['不得向开发域回传 C 目标值（只发布聚合后的通过/失败与不确定性）'],
        tools=['cryptography', 'pandas', 'numpy'],
        budget=dict(validation_runs=1, block_permutation=199),
        sandboxed=False,                          # 必须运行于沙箱之外
        system_prompt=None),
]

for _a in AGENTS:
    _a['system_prompt'] = COMMON_HEAD.format(role=_a['agent']) + NO_DIRECTION_CLAUSE


def by_name(name):
    for a in AGENTS:
        if a['agent'] == name:
            return a
    raise KeyError(name)
