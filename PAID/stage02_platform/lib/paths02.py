"""
Stage 02 平台路径与权限边界定义
================================
本模块是 Stage 02「可运行系统 + 泄漏测试」的路径唯一事实来源。

设计要点（对应框架 §5.1/§5.3）：
  * SANDBOX_ROOT  —— 发现/实验/证伪/物理审计四类 Agent 唯一可读写的工作树；
  * VAULT         —— 独立目录，仅 Independent Validator 进程可读；
                     存放 C 锁定区目标值的**加密封装**（AES-GCM）与密钥；
  * DENY_PREFIXES —— 沙箱内**必须拒绝**的敏感前缀（原始全域数据、保险库、锁定区）。

不修改 Stage 01 冻结产物：本模块不写入 stage01_protocol/ 与 lib/ 任何文件。
"""
import os

# ---------------------------------------------------------------- 基路径
PROJ = '/sessions/friendly-awesome-turing/mnt/AI_lst/PAID'
DATA = '/sessions/friendly-awesome-turing/mnt/data'
S01 = os.path.join(PROJ, 'stage01_protocol')
S00 = os.path.join(PROJ, 'stage00_data_audit')

S02 = os.path.join(PROJ, 'stage02_platform')
S02_LIB = os.path.join(S02, 'lib')
S02_SCRIPTS = os.path.join(S02, 'scripts')
S02_REPORTS = os.path.join(S02, 'reports')
S02_MANIFEST = os.path.join(S02, 'manifests')
S02_AGENTS = os.path.join(S02, 'agents')
S02_SANDBOX = os.path.join(S02, 'sandbox')
S02_PROMPTS = os.path.join(S02, 'prompts')
S02_LOGS = os.path.join(S02, 'logs')
S02_REGISTRY = os.path.join(S02, 'registry')

SANDBOX_ROOT = os.path.join(S02, 'sandbox_root')
SANDBOX_INPUTS = os.path.join(SANDBOX_ROOT, 'inputs')
SANDBOX_WORK = os.path.join(SANDBOX_ROOT, 'work')

VAULT = os.path.join(S02, 'vault')
VAULT_ENC = os.path.join(VAULT, 'zone_C_targets.enc')
VAULT_KEY = os.path.join(VAULT, 'validator_key.bin')
VAULT_MANIFEST = os.path.join(VAULT, 'vault_manifest.json')

LOG_FILE = os.path.join(S02_LOGS, 'experiment_log.jsonl')
LOG_ANCHOR = os.path.join(S02_LOGS, 'log_anchor.json')
REGISTRY_FILE = os.path.join(S02_REGISTRY, 'candidate_registry.json')
FROZEN_FILE = os.path.join(S02_REGISTRY, 'frozen_candidates.json')
VALIDATION_OUT = os.path.join(S02_REPORTS, 's02_validation_result.json')

# ---------------------------------------------------------------- 敏感前缀（沙箱拒绝）
def _norm(p):
    return os.path.realpath(os.path.abspath(p))


DENY_PREFIXES = [
    _norm(VAULT),                                    # 保险库（密文 + 密钥）
    _norm(os.path.join(DATA)),                       # 全域原始数据：含全城 LST 栅格与全表 CSV
    _norm(os.path.join(S01, 'locked')),              # Stage 01 明文 C 目标值
    _norm(os.path.join(S01, 'split', 'analysis_split.csv')),
    _norm(os.path.join(S02, 'reports')),             # 验证结果报告（含解封后的结论）
]

# 文件名级拒绝（无论路径）：防止以副本形式出现
DENY_NAME_PATTERNS = ['zone_c', 'zonec', 'vault', 'validator_key', 'data_原始', 'lst_30m']

# 沙箱内**允许**读写的根（写白名单；/tmp 可写为临时草稿）
ALLOW_PREFIXES = [
    _norm(SANDBOX_ROOT),
    _norm(os.path.join(PROJ, 'lib')),                # 无秘密的通用 IO 库
    _norm('/usr'),                                   # Python 标准库与第三方包
    _norm('/etc'),
    _norm('/tmp'),
]

# 沙箱内**允许读取**的根（读白名单，比写白名单更严）：
#   读白名单之外的路径一律拒绝。这正是为堵住「把受保护文件以硬链接/改名副本
#   放到白名单之外（或 /tmp）再读」的绕行；DENY_PREFIXES 优先级高于本白名单。
#   注意：PROJ 整体可读——平台代码、Stage 01 公开协议、沙箱工作树都在其下，
#   而真正敏感的子目录（vault / locked / analysis_split.csv / S02/reports / data）
#   已在 DENY_PREFIXES 中显式排除。
ALLOW_READ_PREFIXES = [
    _norm(SANDBOX_ROOT),
    _norm(PROJ),
    _norm('/usr'),                                   # Python 标准库、numpy/pandas
    _norm('/etc'),
    _norm('/dev/urandom'),                           # 随机源（非敏感设备文件）
    _norm('/dev/null'),
]


def rel_in(prefixes, path):
    """True 若 path 位于 prefixes 任一前缀之下。"""
    rp = _norm(path)
    for pre in prefixes:
        if rp == pre or rp.startswith(pre + os.sep):
            return True
    return False
