"""
Stage 02 访问守卫（runtime access guard）
=========================================
框架依据：§5.1 数据隔离设计、§5.3「锁定数据应存储于发现 Agent 无权读取的独立目录」、
Table 10 权限、Table 19「空间泄漏和重复使用测试集」防范。

机制（多层防御，非单一手段）：
  L1 密文级 —— C 目标值以 AES-GCM 密封，密钥仅在 Independent Validator 进程；
  L2 路径级 —— 本守卫用 `sys.addaudithook` 拦截 `open`/`os.listdir`/`os.scandir`，
                对敏感前缀（保险库、全域原始数据、Stage 01 锁定区）一律 raise；
  L2b 身份级 —— 激活时登记受保护文件的 (dev, ino)，凡待读文件 inode 与之相同即拒；
                这堵住「以硬链接/同 inode 副本改头换面」的绕行（realpath 不能识破硬链接）；
  L2c 白名单 —— 读操作只允许白名单根（沙箱树、平台代码、/usr、/etc）；白名单之外
                （含 /tmp 中他人预置的副本）一律拒绝。DENY_PREFIXES 优先级更高；
  L3 写入级 —— 仅允许写沙箱工作树与 /tmp，保护冻结产物与平台代码不被篡改；
  L4 能力级 —— 禁止 subprocess / socket / os.system，杜绝绕行读取；
  L5 预算级 —— 打开次数、墙钟时限、fit 次数上限；
  L6 记录级 —— 每一次拒绝都写入 append-only 哈希链日志，可事后审计。

注：守卫运行于同一 OS 用户下，属**运行时+密码学**隔离而非内核级隔离；此局限已在
STAGE02_REPORT 中如实声明。跨用户/容器级隔离为生产化部署的下一步。
"""
import sys, os, time, builtins
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, '..', 'lib'))
import paths02 as P
import log_tool

_LOG_PATH = os.path.join(P.S02_LOGS, 'experiment_log.jsonl')


class AccessDenied(PermissionError):
    pass


class BudgetExceeded(RuntimeError):
    pass


_STATE = dict(active=False, actor='sandbox', opens=0, denials=0,
              fits=0, t0=None, limits={}, reason=[])
_INTERNAL = False          # 守卫自身文件操作的再入保护
_PROTECTED_IDS = set()     # 受保护文件的 (st_dev, st_ino) 身份集，激活时建立


def _log(actor, action, **detail):
    """内部记录（再入安全）：直接写日志，绕过审计钩子。"""
    global _INTERNAL
    _INTERNAL = True
    try:
        log_tool.append(actor, action, logpath=_LOG_PATH, **detail)
    finally:
        _INTERNAL = False


def _parts(path):
    try:
        rp = os.path.realpath(os.path.abspath(os.fspath(path)))
    except Exception:
        return None
    return rp


def _match_name(rp):
    low = rp.lower()
    for pat in P.DENY_NAME_PATTERNS:
        if pat in low:
            return pat
    return None


def _load_protected():
    """遍历 DENY_PREFIXES，登记受保护文件的 (dev, ino) 身份。

    关键：**硬链接与 symlink 的 realpath 不会指向源文件**，因此纯路径规则挡不住
    硬链接。按 inode 身份比对则与路径无关——硬链接与原文件同 inode，必然命中。
    """
    global _PROTECTED_IDS, _INTERNAL
    ids = set()
    _INTERNAL = True
    try:
        for pre in P.DENY_PREFIXES:
            if os.path.isdir(pre):
                for dp, _dns, fns in os.walk(pre):
                    for fn in fns:
                        try:
                            st = os.stat(os.path.join(dp, fn))
                            ids.add((st.st_dev, st.st_ino))
                        except OSError:
                            continue
            else:
                try:
                    st = os.stat(pre)
                    ids.add((st.st_dev, st.st_ino))
                except OSError:
                    continue
    finally:
        _INTERNAL = False
    _PROTECTED_IDS = ids
    return ids


def _protected_identity(path):
    """True 若 path 的 inode 与任一受保护文件相同（硬链接/同 inode）。"""
    if not _PROTECTED_IDS:
        return False
    try:
        st = os.stat(os.fspath(path))
    except (OSError, TypeError, ValueError):
        return False
    return (st.st_dev, st.st_ino) in _PROTECTED_IDS


def _core_denied(rp, path):
    """路径/名称/inode 三类与「是否在允许根之下」无关的拒绝原因。"""
    if P.rel_in(P.DENY_PREFIXES, rp):
        return 'deny_prefix'
    m = _match_name(rp)
    if m:
        return 'deny_name:%s' % m
    if _protected_identity(path):
        return 'protected_inode'
    return None


def is_denied_read(path):
    rp = _parts(path)
    if rp is None:
        return None
    why = _core_denied(rp, path)
    if why:
        return why
    # 读白名单：白名单之外一律拒绝（堵住改名副本/异位副本）
    if not P.rel_in(P.ALLOW_READ_PREFIXES, rp):
        return 'outside_read_allowlist'
    return None


def is_denied_write(path, mode):
    rp = _parts(path)
    if rp is None:
        return None
    if _core_denied(rp, path):
        return 'protected_target'
    if rp == os.path.realpath(_LOG_PATH):
        # 追加日志：仅允许追加，禁止截断/覆盖
        if 'w' in mode or '+' in mode:
            return 'log_overwrite'
        return None
    if P.rel_in([P.SANDBOX_ROOT, '/tmp'], rp):
        return None
    if rp.endswith('.pyc') or '__pycache__' in rp:
        return None
    return 'outside_sandbox'


def _check_budget():
    lim = _STATE['limits']
    if _STATE['t0'] is not None and 'max_seconds' in lim:
        if time.time() - _STATE['t0'] > lim['max_seconds']:
            raise BudgetExceeded('wall-clock budget exceeded')
    if 'max_open_calls' in lim and _STATE['opens'] > lim['max_open_calls']:
        raise BudgetExceeded('open-call budget exceeded (%d)' % _STATE['opens'])


def _hook(event, args):
    if _INTERNAL or not _STATE['active']:
        return
    if event == 'open':
        path, mode, flags = (list(args) + [None, None, None])[:3]
        if isinstance(path, int):
            return
        if mode is None:
            # os.open(path, flags) 只给 flags：据 POSIX 标志判读/写，避免把写入误判为读
            try:
                f = int(flags or 0)
            except (TypeError, ValueError):
                f = 0
            writeish = bool(f & (os.O_WRONLY | os.O_RDWR | os.O_CREAT |
                                 os.O_APPEND | os.O_TRUNC))
            mode = 'w' if writeish else 'r'
        else:
            mode = str(mode)
        _STATE['opens'] += 1
        # 读检查（含读写与只读）
        why = None
        if 'w' in mode or 'a' in mode or 'x' in mode or '+' in mode:
            why = is_denied_write(path, mode)
            kind = 'write'
        else:
            why = is_denied_read(path)
            kind = 'read'
        if why:
            _STATE['denials'] += 1
            _STATE['reason'].append((kind, why, str(path)[:200]))
            _log(_STATE['actor'], 'access_denied',
                 kind=kind, rule=why, path=str(path)[:200])
            raise AccessDenied('[sandbox] %s denied (%s): %s' % (kind, why, path))
        _check_budget()
    elif event in ('os.listdir', 'os.scandir'):
        why = is_denied_read(args[0] if args else None)
        if why:
            _STATE['denials'] += 1
            _STATE['reason'].append(('list', why, str(args[0])[:200]))
            _log(_STATE['actor'], 'access_denied', kind='list', rule=why,
                 path=str(args[0])[:200])
            raise AccessDenied('[sandbox] list denied (%s): %s' % (why, args[0]))
    elif event in ('os.remove', 'os.rename', 'os.link', 'os.symlink',
                   'os.mkdir', 'os.rmdir', 'shutil.rmtree', 'shutil.move',
                   'shutil.copyfile', 'shutil.copymode'):
        target = None
        for a in args:
            if isinstance(a, (str, bytes, os.PathLike)):
                target = a
                break
        if event == 'os.mkdir' and target is not None:
            # os.makedirs(exist_ok=True) 在目录已存在时仍会探测一次 mkdir（幂等 no-op）：
            # 不应记作越界（否则追加日志等正常操作会污染拒绝计数）。
            try:
                if os.path.isdir(os.fspath(target)):
                    return
            except OSError:
                pass
        why = is_denied_write(target, 'w') if target else None
        if why:
            _STATE['denials'] += 1
            _log(_STATE['actor'], 'access_denied', kind=event, rule=why,
                 path=str(target)[:200])
            raise AccessDenied('[sandbox] %s denied (%s)' % (event, why))
    elif event in ('subprocess.Popen', 'os.system', 'os.exec', 'os.posix_spawn',
                   'os.spawn', 'socket.connect', 'socket.getaddrinfo',
                   'socket.gethostbyname', 'urllib.Request'):
        _STATE['denials'] += 1
        _log(_STATE['actor'], 'access_denied', kind=event, rule='capability_blocked')
        raise AccessDenied('[sandbox] capability blocked: %s' % event)


def activate(actor='sandbox', limits=None, log_path=_LOG_PATH):
    """在沙箱进程内激活守卫。必须在导入业务模块**之前**调用一次。"""
    _load_protected()                       # 先登记受保护 inode 身份（硬链接防线）
    _STATE.update(active=True, actor=actor, t0=time.time(),
                  limits=limits or dict(max_open_calls=200000, max_seconds=600,
                                        max_fits=2000))
    sys.addaudithook(_hook)
    _log(actor, 'sandbox_start', limits=_STATE['limits'],
         protected_inodes=len(_PROTECTED_IDS))
    return _STATE


def count_fit(n=1):
    """实验轮次计数（预算）。"""
    _STATE['fits'] += n
    lim = _STATE['limits']
    if 'max_fits' in lim and _STATE['fits'] > lim['max_fits']:
        raise BudgetExceeded('fit budget exceeded (%d)' % _STATE['fits'])


def shutdown(verdict='done'):
    _STATE['active'] = False
    st = dict(opens=_STATE['opens'], denials=_STATE['denials'],
              fits=_STATE['fits'], verdict=verdict)
    _log(_STATE['actor'], 'sandbox_end', **st)
    return st


def status():
    return dict(opens=_STATE['opens'], denials=_STATE['denials'],
                fits=_STATE['fits'], active=_STATE['active'],
                t_elapsed=round(time.time() - _STATE['t0'], 3) if _STATE['t0'] else None)
