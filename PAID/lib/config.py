"""PAID 项目路径配置。"""
import os

DATA = '/sessions/friendly-awesome-turing/mnt/data'
PROJ = '/sessions/friendly-awesome-turing/mnt/AI_lst/PAID'
LIB = os.path.join(PROJ, 'lib')
S00 = os.path.join(PROJ, 'stage00_data_audit')
S01 = os.path.join(PROJ, 'stage01_protocol')

S00_SCRIPTS = os.path.join(S00, 'scripts')
S00_REPORTS = os.path.join(S00, 'reports')
S00_MASK = os.path.join(S00, 'mask')
S00_MANIFEST = os.path.join(S00, 'manifest')

S01_SCRIPTS = os.path.join(S01, 'scripts')
S01_REPORTS = os.path.join(S01, 'reports')
S01_MANIFEST = os.path.join(S01, 'manifest')
S01_CONSTRAINTS = os.path.join(S01, 'constraints')

CSV = os.path.join(DATA, 'data_原始.csv')
