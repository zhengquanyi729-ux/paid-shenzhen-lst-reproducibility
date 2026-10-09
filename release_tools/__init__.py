"""
PAID reviewer release — portable verification layer (v1.2.1).

Every module here derives its paths from the location of `release_paths.py`, so the
archive can be unzipped anywhere and verified with no AES key, no network and no
knowledge of the author's environment.  `path_guard.guard()` refuses any path that
escapes the archive root.

Entry points:
    run_all_release.py            run every verifier, print readiness flags
    verify_archive_paths.py       ASCII / normalized, traversal-free archive member paths
    verify_stage01_release.py     split + R=15 buffer
    verify_stage03_release.py     frozen discovery registry
    verify_stage04_release.py     locked-region primary endpoint (+ definitional placebo)
    verify_stage05_release.py     Baselines B/D + cross-report consistency
    verify_changchun_release.py   Changchun external replication
    verify_figures_release.py     shipped figures
    verify_manuscript_submission.py  submission wording patches P1-P7
    scan_secrets.py               secret / credential scan
    scan_absolute_paths.py        author-path scan over the reviewer layer
"""
