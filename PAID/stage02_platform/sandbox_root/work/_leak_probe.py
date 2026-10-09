
import sys, os, json
sys.path.insert(0, r"/sessions/friendly-awesome-turing/mnt/AI_lst/PAID/stage02_platform/lib"); sys.path.insert(0, r"/sessions/friendly-awesome-turing/mnt/AI_lst/PAID/stage02_platform/sandbox"); sys.path.insert(0, r"/sessions/friendly-awesome-turing/mnt/AI_lst/PAID/stage02_platform")
import paths02 as P
import access_guard as G
G.activate(actor="leak_probe", limits=dict(max_open_calls=100000, max_seconds=60, max_fits=50))
import numpy as np, builtins
res = {"denied": [], "leaked": [], "contained": []}
def attempt(label, fn):
    try:
        fn(); res["leaked"].append(label)
    except G.AccessDenied:
        res["denied"].append(label)
    except Exception as e:
        # 其它异常（如 InvalidTag）不计为泄漏
        res["denied"].append(label + "(" + type(e).__name__ + ")")

def attempt_ret(label, fn):
    # 某些调用（glob）会吞掉 PermissionError；判据改为**返回值是否为空**
    try:
        r = fn()
    except Exception as e:
        res["denied"].append(label + "(" + type(e).__name__ + ")"); return
    if not r:
        res["contained"].append(label)          # 抛错被吞但未获得信息
    else:
        res["leaked"].append(label)

attempt("direct_enc", lambda: open(P.VAULT_ENC,"rb").read())
attempt("direct_key", lambda: open(P.VAULT_KEY,"rb").read())
attempt("locked_C", lambda: open(os.path.join(P.S01,"locked","zone_C_targets.csv")).read())
attempt("full_csv", lambda: open(os.path.join(P.DATA,"data_原始.csv")).read())
attempt("full_raster", lambda: open(os.path.join(P.DATA,"LST_30m_Final new.tif"),"rb").read(64))
rel = os.path.join(P.SANDBOX_ROOT, "work", "..", "..", "vault", "zone_C_targets.enc")
attempt("relative_dotdot", lambda: open(os.path.relpath(rel)).read())
attempt("normalized_path", lambda: open(rel).read())
attempt("numpy_fromfile", lambda: np.fromfile(P.VAULT_ENC, dtype="uint8", count=16))
attempt("numpy_loadtxt", lambda: np.loadtxt(os.path.join(P.DATA,"data_原始.csv"), delimiter=",", max_rows=2))
attempt("listdir_vault", lambda: os.listdir(P.VAULT))
attempt("listdir_locked", lambda: os.listdir(os.path.join(P.S01,"locked")))
attempt("read_reports", lambda: open(os.path.join(P.S02,"reports","s02_validation_result.json")).read())
attempt_ret("glob_vault", lambda: __import__("glob").glob(os.path.join(P.VAULT,"*")))
attempt_ret("glob_locked", lambda: __import__("glob").glob(os.path.join(P.S01,"locked","*")))
# 对抗性诱饵：白名单内硬链接 / 白名单外改名副本 / symlink（LK8-LK10）
attempt("LK8_hardlink_open", lambda: open(r"/sessions/friendly-awesome-turing/mnt/AI_lst/PAID/stage02_platform/sandbox_root/work/lk8_payload.dat","rb").read(64))
attempt("LK8_numpy_fromfile", lambda: np.fromfile(r"/sessions/friendly-awesome-turing/mnt/AI_lst/PAID/stage02_platform/sandbox_root/work/lk8_payload.dat", dtype="uint8", count=16))
attempt("LK9_tmp_copy", lambda: open(r"/tmp/lk9_payload.dat","rb").read(64))
attempt("LK10_symlink", lambda: open(r"/sessions/friendly-awesome-turing/mnt/AI_lst/PAID/stage02_platform/sandbox_root/work/lk10_symlink.dat","rb").read(64))
st = G.shutdown("leak_probe_done")
print("__RESULT__" + json.dumps({"res":res,"status":st}))
