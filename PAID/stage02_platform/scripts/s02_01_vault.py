"""
S02.1 数据保险库：用 AES-GCM 密封 C 锁定区（目标值 + 协变量），密钥单独保管
================================================================================
框架依据：§5.1 数据隔离设计、§5.3 解封原则、Table 11（C 区「仅独立验证服务持有 LST
目标值，候选冻结后解封」）。

实现要点：
  1) 保险库位于 SANDBOX_ROOT 之外（lib/paths02.py 的 VAULT），且被访问守卫 deny；
  2) 目标值以 AES-GCM **认证加密**保存，密钥 `validator_key.bin` 与密文分离；
     即使密文被读取，无密钥亦不可解——这是比「改权限」更强的物理隔离；
  3) 保险库内容 = C 区完整可用表（Grid_ID + 协变量 + LST_mean），
     使验证服务无需接触全域原始数据即可评估候选表达式；
  4) 构建**幂等且可复现**：密钥若已存在则沿用；nonce 由 HMAC(密钥, 明文哈希) 派生，
     故同一密钥下密文哈希稳定，便于纳入哈希清单。

不修改 Stage 01 冻结产物。Stage 01 的 `locked/zone_C_targets.csv` 作为冻结审计件保留，
但已列入沙箱拒绝前缀，发现侧不可读。

输出：
  vault/zone_C_targets.enc        （nonce || AES-GCM 密文）
  vault/validator_key.bin         （32B 密钥，0600）
  vault/vault_manifest.json       （非机密元数据）
  reports/s02_01_vault.json / .md
"""
import sys, os, json, hmac, hashlib, secrets, base64
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lib'))
import paths02 as P
import pandas as pd
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

CREATED = '2026-09-24'
VERSION = 'stage02-vault-v1'

os.makedirs(P.VAULT, exist_ok=True)
os.makedirs(P.S02_REPORTS, exist_ok=True)


def sha256(b):
    return hashlib.sha256(b).hexdigest()


# ---------------------------------------------------------------- 1) 载入或生成密钥
if os.path.exists(P.VAULT_KEY):
    key = open(P.VAULT_KEY, 'rb').read()
    key_origin = 'reused'
else:
    key = secrets.token_bytes(32)
    with open(P.VAULT_KEY, 'wb') as f:
        f.write(key)
    os.chmod(P.VAULT_KEY, 0o600)
    key_origin = 'generated'
assert len(key) == 32

# ---------------------------------------------------------------- 2) 组装 C 区完整表
c_ids = [int(x) for x in
         pd.read_csv(os.path.join(P.S01, 'locked', 'zone_C_targets.csv'))['Grid_ID']]
full = pd.read_csv(os.path.join(P.DATA, 'data_原始.csv'))
full.columns = [c.strip() for c in full.columns]
cdf = full[full['My_ID'].isin(c_ids)].copy()
cdf = cdf.rename(columns={'My_ID': 'Grid_ID'})
COLS = ['Grid_ID', 'LST_mean', 'NDVI_mean', 'DEM_mean', 'SVF_mean',
        'Road_Dens', 'X_BD', 'X_BH', 'X_VolDens']
cdf = cdf[COLS].sort_values('Grid_ID').reset_index(drop=True)
plain = cdf.to_csv(index=False).encode('utf-8')
plain_sha = sha256(plain)

# ---------------------------------------------------------------- 3) AES-GCM 加密
nonce = hmac.new(key, plain_sha.encode(), hashlib.sha256).digest()[:12]   # 确定性 nonce
ct = AESGCM(key).encrypt(nonce, plain, b'PAID-stage02-vault-v1')
blob = nonce + ct
with open(P.VAULT_ENC, 'wb') as f:
    f.write(blob)

# ---------------------------------------------------------------- 4) 元数据
manifest = dict(
    version=VERSION, created=CREATED,
    framework_ref='§5.1 / §5.3 / Table 11（C 区）',
    algorithm='AES-256-GCM（认证加密）',
    key_path=os.path.relpath(P.VAULT_KEY, P.PROJ),
    key_origin=key_origin, key_bytes=len(key),
    ciphertext_path=os.path.relpath(P.VAULT_ENC, P.PROJ),
    ciphertext_bytes=len(blob),
    ciphertext_sha256=sha256(blob),
    plaintext_sha256=plain_sha,          # 明文哈希非机密，用于审计可比对
    n_rows=int(len(cdf)), columns=COLS,
    nonce_derivation='HMAC-SHA256(key, plaintext_sha256)[:12]（确定性，保证构建可复现）',
    key_hash=sha256(key),                # 哈希非密钥本身，用于验证清单自洽
    access_rule='仅 Independent Validator 进程载入密钥并解密；发现侧沙箱 deny 整个 vault/ 与 '
                'stage01_protocol/locked/。哈希≠访问控制：本封装提供密文级隔离。')
with open(P.VAULT_MANIFEST, 'w', encoding='utf-8') as f:
    json.dump(manifest, f, ensure_ascii=False, indent=2)

R = dict(version=VERSION, created=CREATED, status='OK', **{
    k: manifest[k] for k in ('algorithm', 'key_origin', 'ciphertext_bytes',
                             'ciphertext_sha256', 'plaintext_sha256', 'n_rows', 'key_hash')})
with open(os.path.join(P.S02_REPORTS, 's02_01_vault.json'), 'w', encoding='utf-8') as f:
    json.dump(R, f, ensure_ascii=False, indent=2)

L = ['# S02.1 数据保险库\n', '版本 %s。状态 **OK**。\n' % VERSION,
     '| 项 | 值 |', '|---|---|',
     '| 算法 | %s |' % manifest['algorithm'],
     '| 密钥 | `%s`（%d B，%s） |' % (manifest['key_path'], len(key), key_origin),
     '| 密文 | `%s`（%d B） |' % (manifest['ciphertext_path'], len(blob)),
     '| 密文 SHA-256 | `%s` |' % manifest['ciphertext_sha256'],
     '| 明文 SHA-256 | `%s` |' % plain_sha,
     '| 行数 / 列 | %d / %s |' % (len(cdf), ', '.join(COLS)),
     '',
     '> C 区目标值已由明文改为**密文级隔离**：保险库位于发现沙箱工作树之外，且被访问守卫 deny。',
     '> Stage 01 冻结的 `locked/zone_C_targets.csv` 作为审计件保留，同样被 deny。\n']
with open(os.path.join(P.S02_REPORTS, 's02_01_vault.md'), 'w', encoding='utf-8') as f:
    f.write('\n'.join(L))

print(json.dumps(R, ensure_ascii=False, indent=2))
