"""
Stage 03 路径定义（发现侧之外，冻结/汇总/报告步骤使用）
========================================================
发现侧（sandbox 内）只能写 sandbox_root/work/；本模块定义的 stage03_discovery/registry、
reports、manifest 位于沙箱之外，只有**冻结/汇总/报告**步骤（非发现 Agent）才可写。
这与 §5.1「发现-验证防火墙」一致：发现 Agent 无法自行登记或改写已冻结候选。
"""
import os

PROJ = '/sessions/friendly-awesome-turing/mnt/AI_lst/PAID'
S02 = os.path.join(PROJ, 'stage02_platform')
S03 = os.path.join(PROJ, 'stage03_discovery')

S03_SCRIPTS = os.path.join(S03, 'scripts')
S03_AGENTS = os.path.join(S03, 'agents')
S03_LIB = os.path.join(S03, 'lib')
S03_REGISTRY = os.path.join(S03, 'registry')
S03_REPORTS = os.path.join(S03, 'reports')
S03_MANIFEST = os.path.join(S03, 'manifests')
S03_CAND = os.path.join(S03_REGISTRY, 'candidates')

# 发现侧在沙箱内写出的原始产出（只读引用）
SANDBOX_S03 = os.path.join(S02, 'sandbox_root', 'work', 's03')
RAW_REGISTRY = os.path.join(SANDBOX_S03, 'candidate_registry.json')

# 冻结产物
FROZEN_FILE = os.path.join(S03_REGISTRY, 'frozen_candidates.json')
CANDIDATE_REGISTRY = os.path.join(S03_REGISTRY, 'candidate_registry.json')
FULL_TRAJECTORY = os.path.join(S03_REGISTRY, 'experiment_trajectory.json')

# 报告与清单
REPORT = os.path.join(S03, 'STAGE03_REPORT.md')
HASH_MANIFEST = os.path.join(S03_MANIFEST, 'stage03_hashes.txt')

# 沙箱外仍只读引用的 Stage 01/02 事实源
S01 = os.path.join(PROJ, 'stage01_protocol')
S02_LOGS = os.path.join(S02, 'logs')
EXPERIMENT_LOG = os.path.join(S02_LOGS, 'experiment_log.jsonl')
