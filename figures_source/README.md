# FIGURE SOURCE

`FIGURE_SOURCE_INDEX.csv` maps each manuscript figure to the script that generates it and the artefacts
it reads. The figure files themselves are **not copied here**; they ship in place at
`PAID/stage05_paper/figures/` (each in `.pdf`, `.png`, `.svg`, `.tif`).

Regenerate everything with:

```bash
python3 PAID/stage05_paper/scripts/s05_02_figures.py        # fig1–fig6
python3 PAID/stage05_paper/scripts/s05_06_study_overview.py  # fig0 (Fig. 1)
```

PNG and TIFF reproduce byte-for-byte; PDF/SVG are content-identical but carry a fresh producer
timestamp. Two related scripts, `s05_07_boundary.py` and `s05_08_area_audit.py`, need the original
ArcGIS shapefiles (not redistributed); their outputs
(`PAID/stage05_paper/reports/shenzhen_admin_studyarea.json`, `reports/s05_08_area_audit.json`) are
included instead.
