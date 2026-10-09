"""
S02.3 五 Agent 骨架与系统提示词（Table 10 / Table 12 Agent manifest / §3.2）
============================================================================
生成：
  prompts/system_prompts.json / .md  —— 注入提示词（含 §3.2 无方向预设禁令）
  agent/agent_manifest.json          —— 权限、工具白名单、预算、提示词哈希
  reports/s02_03_agents.json / .md
"""
import sys, os, json, hashlib
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lib'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'agents'))
import paths02 as P
import registry as REG

CREATED = '2026-09-24'
VERSION = 'stage02-agents-v1'
os.makedirs(P.S02_PROMPTS, exist_ok=True)
os.makedirs(os.path.join(P.S02, 'agent'), exist_ok=True)
os.makedirs(P.S02_REPORTS, exist_ok=True)

prompts = {a['agent']: a['system_prompt'] for a in REG.AGENTS}
with open(os.path.join(P.S02_PROMPTS, 'system_prompts.json'), 'w', encoding='utf-8') as f:
    json.dump(prompts, f, ensure_ascii=False, indent=2)

L = ['# Stage 02 系统提示词（发现侧）\n',
     '> 依 §3.2：不注入任何方向性结论；仅注入数据边界、物理约束与计算工具。\n']
for name, p in prompts.items():
    L.append('## %s\n\n%s\n' % (name, p))
with open(os.path.join(P.S02_PROMPTS, 'system_prompts.md'), 'w', encoding='utf-8') as f:
    f.write('\n'.join(L))


def sha(s):
    return hashlib.sha256(s.encode('utf-8')).hexdigest()


manifest = dict(
    version=VERSION, created=CREATED,
    framework_ref='Table 10 / Table 11 / Table 12 Agent manifest / §3.2 / §4.3 / §5.3',
    model_version=REG.MODEL_VERSION,
    system_prompt_policy=dict(
        injects_target_domain_conclusions=False,
        injects_data_dictionary=True, injects_physics_constraints=True,
        injects_compute_budget=True, injects_tool_whitelist=True,
        forbidden_claims=[a for a in [
            'NDVI 必须单调降温/升温', 'SVF 必须升温或降温', '建筑高度必须产生某一方向响应',
            '预设唯一最优空间尺度', '预设固定函数形式', '预设单一显著阈值', '预设特定交互组合',
            '注入旧论文结论/相关矩阵']],
        audit='Physics Auditor 逐候选审计 PA4（正/负双向检查）；提示词哈希登记如下。'),
    agents=[dict(agent=a['agent'], purpose=a['purpose'],
                 data_access=a['data_access'], forbidden_access=a['forbidden_access'],
                 tools=a['tools'], budget=a['budget'], sandboxed=a['sandboxed'],
                 system_prompt_sha256=sha(a['system_prompt'])) for a in REG.AGENTS])
with open(os.path.join(P.S02, 'agent', 'agent_manifest.json'), 'w', encoding='utf-8') as f:
    json.dump(manifest, f, ensure_ascii=False, indent=2)

R = dict(version=VERSION, created=CREATED, status='OK',
         n_agents=len(manifest['agents']),
         sandboxed=[a['agent'] for a in REG.AGENTS if a['sandboxed']],
         not_sandboxed=[a['agent'] for a in REG.AGENTS if not a['sandboxed']],
         prompt_hashes={a['agent']: sha(a['system_prompt']) for a in REG.AGENTS})
with open(os.path.join(P.S02_REPORTS, 's02_03_agents.json'), 'w', encoding='utf-8') as f:
    json.dump(R, f, ensure_ascii=False, indent=2)

M = ['# S02.3 五 Agent 骨架与权限\n', '版本 %s。状态 **OK**。\n' % VERSION,
     '| Agent | 沙箱内 | 可访问 | 禁访问 |', '|---|---|---|---|']
for a in REG.AGENTS:
    M.append('| %s | %s | %s | %s |' % (a['agent'], '是' if a['sandboxed'] else '**否（独立进程）**',
                                        '、'.join(a['data_access']), '；'.join(a['forbidden_access'])))
M += ['', '提示词哈希：', '', '| Agent | SHA-256（前 16） |', '|---|---|']
for a in REG.AGENTS:
    M.append('| %s | `%s` |' % (a['agent'], sha(a['system_prompt'])[:16]))
M.append('\n> Independent Validator 必须在沙箱**之外**独立运行，不得接受发现方的参数更新请求。')
with open(os.path.join(P.S02_REPORTS, 's02_03_agents.md'), 'w', encoding='utf-8') as f:
    f.write('\n'.join(M))

print(json.dumps(R, ensure_ascii=False, indent=2))
