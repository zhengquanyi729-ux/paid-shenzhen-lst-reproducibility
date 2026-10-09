"""
release_paths.py — central, portable root resolution for the review layer
=========================================================================
Every path a reviewer needs is derived from the location of *this file*, so the
archive can be unzipped anywhere and the tooling still works. No absolute path,
no author HOME, no mount point, no environment variable is required.

    RELEASE_ROOT
    ├── PAID/            the frozen Stage 00–05 implementation (historical record)
    ├── data/
    │   ├── shenzhen/    analysis-ready Shenzhen tables (incl. Region C)
    │   └── changchun/   analysis-ready Changchun replication table
    ├── audit/           protocol-audit index and key artefacts
    ├── verification/    verify_manifest.py + VERIFICATION_INDEX.md
    └── release_tools/   this portable layer

Nothing in this module reads the AES vault key, calls the network, or imports the
historical `paths02` / `paths03` / `config` modules.
"""
from pathlib import Path

# release_tools/ lives at the archive root, so the root is one level up from this file.
RELEASE_ROOT = Path(__file__).resolve().parents[1]

PAID_ROOT = RELEASE_ROOT / 'PAID'

DATA_ROOT = RELEASE_ROOT / 'data'
SHENZHEN_ROOT = DATA_ROOT / 'shenzhen'
CHANGCHUN_ROOT = DATA_ROOT / 'changchun'

AUDIT_ROOT = RELEASE_ROOT / 'audit'
FIGURE_ROOT = PAID_ROOT / 'stage05_paper' / 'figures'
VERIFICATION_ROOT = RELEASE_ROOT / 'verification'
RELEASE_TOOLS_ROOT = RELEASE_ROOT / 'release_tools'
REPORTS_ROOT = RELEASE_ROOT / 'release_tools' / 'reports'

# --- frequently used frozen inputs -------------------------------------------------
ZONE_A = SHENZHEN_ROOT / 'zone_A_open.csv'
ZONE_B = SHENZHEN_ROOT / 'zone_B_devval.csv'
ZONE_C_TARGETS = SHENZHEN_ROOT / 'zone_C_targets.csv'
ZONE_C_ANALYSIS_READY = SHENZHEN_ROOT / 'zone_C_analysis_ready.csv'
ANALYSIS_SPLIT = SHENZHEN_ROOT / 'analysis_split.csv'
SPATIAL_MASK = SHENZHEN_ROOT / 'spatial_mask.csv'

CHANGCHUN_TABLE = CHANGCHUN_ROOT / 'changchun_analysis_ready.csv'

STAGE03_CAND_DIR = PAID_ROOT / 'stage03_discovery' / 'registry' / 'candidates'
STAGE03_FROZEN = PAID_ROOT / 'stage03_discovery' / 'registry' / 'frozen_candidates.json'
STAGE04_RESULTS = PAID_ROOT / 'stage04_validation' / 'reports' / 's04_validation_results.json'
STAGE05_BASELINEB = PAID_ROOT / 'stage05_paper' / 'reports' / 'baselineB.json'
STAGE05_BASELINED = PAID_ROOT / 'stage05_paper' / 'reports' / 'baselineD.json'
STAGE05_EXTERNAL = PAID_ROOT / 'stage05_paper' / 'reports' / 'external_replication.json'
VAULT_MANIFEST = PAID_ROOT / 'stage02_platform' / 'vault' / 'vault_manifest.json'

MANIFEST = RELEASE_ROOT / 'MANIFEST_SHA256.csv'


def describe():
    """Print the resolved roots (used by run_all_release.py as a smoke test)."""
    for name, value in (
        ('RELEASE_ROOT', RELEASE_ROOT),
        ('PAID_ROOT', PAID_ROOT),
        ('SHENZHEN_ROOT', SHENZHEN_ROOT),
        ('CHANGCHUN_ROOT', CHANGCHUN_ROOT),
        ('FIGURE_ROOT', FIGURE_ROOT),
        ('VERIFICATION_ROOT', VERIFICATION_ROOT),
    ):
        print('  %-18s %s' % (name, value))
    print('  RELEASE_ROOT exists:', RELEASE_ROOT.is_dir())


if __name__ == '__main__':
    describe()
