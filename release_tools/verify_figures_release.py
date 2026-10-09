#!/usr/bin/env python3
"""
verify_figures_release.py — verify the shipped manuscript figures
================================================================
Reads only files inside the archive. Checks, with no key / network / author tree:

  * all seven manuscript figures ship in all four formats (pdf/png/svg/tif) = 28 files;
  * every figure file is non-empty and its SHA-256 matches the entry in
    `MANIFEST_SHA256.csv` (when that manifest is present);
  * `figures_source/FIGURE_SOURCE_INDEX.csv` lists the same seven figure basenames and
    every basename it names exists in `PAID/stage05_paper/figures/`;
  * (optional) if a manuscript `.docx` is present in the archive, the PNG images embedded
    in it are byte-identical to the shipped figure PNGs.

Figure files are shipped in place; regeneration is *not* required by this verifier (two of
the generating scripts need the original ArcGIS shapefiles, which are not redistributed —
their outputs are shipped instead; see `figures_source/README.md`).

Run:  python3 release_tools/verify_figures_release.py
"""
import csv
import hashlib
import os
import zipfile
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import release_paths as RP                     # noqa: E402
from path_guard import guard                   # noqa: E402

FIGURES = [
    'fig0_study_overview', 'fig1_protocol_split', 'fig3_search', 'fig4_validation',
    'fig5_external', 'fig2_baselineB', 'fig6_baselineD',
]
FORMATS = ['pdf', 'png', 'svg', 'tif']


def _sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as fh:
        for b in iter(lambda: fh.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def main():
    checks = []

    def chk(cid, name, ok, detail=''):
        checks.append(dict(id=cid, name=name, ok=bool(ok), detail=detail))
        print('  %-5s %-46s %s %s' % (cid, name, 'PASS' if ok else 'FAIL', detail))

    figdir = RP.FIGURE_ROOT

    # --- F1: presence of all 7 × 4 files, all non-empty
    missing = []
    for base in FIGURES:
        for ext in FORMATS:
            p = figdir / ('%s.%s' % (base, ext))
            if not p.exists() or p.stat().st_size == 0:
                missing.append('%s.%s' % (base, ext))
    chk('F1', 'seven figures × four formats present', not missing,
        'missing=%s' % (missing or 'none'))

    # --- F2: figure SHA-256 match the release manifest (if present)
    manifest = RP.MANIFEST
    if manifest.exists():
        man = {}
        with open(guard(manifest), encoding='utf-8') as fh:
            for row in csv.DictReader(fh):
                man[row['release_path']] = row['sha256']
        ok2, det2 = True, []
        for base in FIGURES:
            for ext in FORMATS:
                rel = 'PAID/stage05_paper/figures/%s.%s' % (base, ext)
                p = figdir / ('%s.%s' % (base, ext))
                if not p.exists():
                    continue
                if man.get(rel) is None or man[rel] != _sha256(p):
                    ok2 = False
                    det2.append('%s.%s' % (base, ext))
        chk('F2', 'figure SHA-256 match MANIFEST_SHA256.csv', ok2,
            'mismatches=%s' % (det2 or 'none'))
    else:
        checks.append(dict(id='F2', name='figure SHA-256 match MANIFEST_SHA256.csv',
                           ok=True, expected=True, detail='SKIP (manifest absent)'))
        print('  %-5s %-46s %s' % ('F2', 'figure SHA-256 match MANIFEST_SHA256.csv',
                                   'SKIP (manifest absent)'))

    # --- F3: figure-source index consistency
    idx = RP.RELEASE_ROOT / 'figures_source' / 'FIGURE_SOURCE_INDEX.csv'
    listed = []
    if idx.exists():
        with open(guard(idx), encoding='utf-8') as fh:
            for row in csv.DictReader(fh):
                listed.append(row['file_basename'])
    ok3 = sorted(listed) == sorted(FIGURES) and all(
        (figdir / ('%s.png' % b)).exists() for b in listed)
    chk('F3', 'figure-source index lists the same seven figures', ok3,
        'listed=%d' % len(listed))

    # --- F4: EVERY manuscript .docx embeds the shipped figure PNGs (not just the first)
    docxs = sorted(RP.RELEASE_ROOT.rglob('*.docx'))
    name4 = 'every manuscript docx embeds shipped figure PNGs'
    if not docxs:
        checks.append(dict(id='F4', name=name4, ok=True, expected=True,
                           detail='SKIP (no .docx in archive)'))
        print('  %-5s %-46s %s' % ('F4', name4, 'SKIP (no .docx)'))
    else:
        shipped = {_sha256(figdir / ('%s.png' % b)): b for b in FIGURES}
        ok4, det4 = True, []
        for docx in docxs:
            with zipfile.ZipFile(guard(docx)) as z:
                media = [n for n in z.namelist() if n.startswith('word/media/')]
                hit = sum(1 for n in media if _sha256_bytes(z.read(n)) in shipped)
            good = hit >= len(FIGURES)
            ok4 = ok4 and good
            det4.append('%s %d/%d%s' % (docx.name, hit, len(FIGURES),
                                        '' if good else ' FAIL'))
        chk('F4', name4, ok4, '; '.join(det4))

    ok_all = all(c['ok'] for c in checks)
    npass = sum(c['ok'] for c in checks)
    print('\n== Figures (release_tools): %s (%d/%d) =='
          % ('PASS' if ok_all else 'FAIL', npass, len(checks)))
    return 0 if ok_all else 1


def _sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


if __name__ == '__main__':
    raise SystemExit(main())
