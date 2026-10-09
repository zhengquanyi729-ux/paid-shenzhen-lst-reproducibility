# CROSS-ENVIRONMENT NUMERICS — status

```
SECOND_ENVIRONMENT_TEST: NOT AVAILABLE
```

The frozen numbers were certified in exactly **one** environment:
`runtime_environment.txt` (Python 3.10.12; numpy 2.2.6, pandas 2.3.3, matplotlib 3.10.8,
Pillow 12.1.1; scipy-openblas 0.3.29). A second, independent interpreter/BLAS environment was
**not** available when this release was built, so no cross-environment numeric agreement is claimed.

What this means:

- `release_tools/verify_manifest.py` (hashes) and the structural verifiers (path, schema, counts)
  are environment-independent and are expected to pass anywhere.
- The **numeric** verifiers (Stage 04/05, Changchun) reproduce the frozen values to the policy
  tolerances *in the certified environment*. On a different BLAS a last-bit difference is expected;
  continuous quantities are compared at 1e-9 and definitional identities exactly
  (`NUMERICAL_TOLERANCE_POLICY.md`), which absorbs last-bit rounding without hiding a real change.

Honest statement: agreement across two independent environments was **not** established. If it is
required, run `release_tools/run_all_release.py` on a second machine and record the result here.
