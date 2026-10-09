"""
Stage 02 追加日志（append-only，哈希链）
=======================================
框架依据：§4.3「每轮实验必须生成只追加记录，不得覆盖失败结果」；
Table 12 Experiment protocol「失败记录策略」；Table 20 候选登记。

每条记录：
  {seq, ts, actor, action, detail, prev, hash}
其中 hash = SHA-256( canonical_json(除 hash 外的全部字段) )，prev = 上一条的 hash。
因此任何删改、重排、插入都会被 `verify()` 检出。

接口：
  append(actor, action, **detail) -> record
  verify(path) -> dict(ok, n, first_bad, head, tail)
本模块不导入任何项目外部依赖，便于在沙箱内外共用。
"""
import os, json, time, hashlib

S02 = '/sessions/friendly-awesome-turing/mnt/AI_lst/PAID/stage02_platform'
LOG_FILE = os.path.join(S02, 'logs', 'experiment_log.jsonl')
GENESIS = '0' * 64


def _canon(rec):
    return json.dumps({k: v for k, v in rec.items() if k != 'hash'},
                      ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def _hash(rec):
    return hashlib.sha256(_canon(rec).encode('utf-8')).hexdigest()


def _last_hash(path):
    if not os.path.exists(path):
        return GENESIS, 0
    last = None
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                last = line
    if last is None:
        return GENESIS, 0
    rec = json.loads(last)
    return rec['hash'], rec['seq']


def append(actor, action, logpath=LOG_FILE, **detail):
    d = os.path.dirname(logpath)
    if d and not os.path.isdir(d):
        os.makedirs(d, exist_ok=True)      # 仅在缺失时创建，避免触达沙箱写入守卫
    prev, seq = _last_hash(logpath)
    rec = dict(seq=seq + 1, ts=time.strftime('%Y-%m-%dT%H:%M:%S'),
               actor=actor, action=action, detail=detail, prev=prev)
    rec['hash'] = _hash(rec)
    with open(logpath, 'a', encoding='utf-8') as f:
        f.write(json.dumps(rec, ensure_ascii=False, sort_keys=True) + '\n')
        f.flush()
        os.fsync(f.fileno())
    return rec


def read_all(path=LOG_FILE):
    if not os.path.exists(path):
        return []
    out = []
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                out.append(json.loads(line))
    return out


def verify(path=LOG_FILE):
    recs = read_all(path)
    prev = GENESIS
    for i, r in enumerate(recs):
        if r.get('seq') != i + 1 or r.get('prev') != prev or _hash(r) != r.get('hash'):
            return dict(ok=False, n=len(recs), first_bad=i + 1,
                        head=recs[0]['hash'][:16] if recs else None,
                        tail=recs[-1]['hash'][:16] if recs else None)
        prev = r['hash']
    return dict(ok=True, n=len(recs), first_bad=None,
                head=recs[0]['hash'][:16] if recs else None,
                tail=recs[-1]['hash'][:16] if recs else None)


if __name__ == '__main__':
    import sys
    r = verify(sys.argv[1] if len(sys.argv) > 1 else LOG_FILE)
    print(json.dumps(r, ensure_ascii=False, indent=2))
