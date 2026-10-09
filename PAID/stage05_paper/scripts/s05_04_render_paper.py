"""
S05.4 合稿：把分节英文正文合成为一篇完整论文（Markdown 母本 + Word .docx）
=========================================================================
输入：`manuscript/*_en.md`（逐节草稿，各自独立编号）
输出：
  - `manuscript/manuscript_full_en.md`   合稿母本（可审阅、可版本管理）
  - `manuscript/PAID_Shenzhen_LST_manuscript.docx`  投稿用 Word（内嵌 7 图 + 图注 + 交叉引用）

合稿时完成的、逐节草稿里没有的三件事：
  1. 章节连续编号：Results 1/2/3/4 -> §3/§4/§5/§6；Discussion -> §7；Limitations 独立成 §8
     （与 `intro_en.md` §1.5 的路线图 "Section 7 ... Section 8 states its limitations" 对齐）。
  2. 七张图（Fig. 0–6）内嵌、写图注、并在正文相应位置加 "Fig. N" 交叉引用。
  3. 标题 / 结构化摘要 / 关键词（本轮补写，内容取自冻结产物与既有的诚实结论）。

图号沿用 `figures/FIGURE_CONTRACT.md` 的约定（Fig. 0 兼作图形摘要），不重排，
以保证与图件文件（fig0_..fig6_）及 Stage 05 清单校验（V5/V11）一致。
用法：python3 stage05_paper/scripts/s05_04_render_paper.py
"""
import os
import re

from docx import Document
from docx.shared import Pt, Inches, Mm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK

_HERE = os.path.dirname(os.path.abspath(__file__))
S05 = os.path.dirname(_HERE)
MS = os.path.join(S05, 'manuscript')
OUT_MD = os.path.join(MS, 'manuscript_full_en.md')
OUT_DOCX = os.path.join(MS, 'PAID_Shenzhen_LST_manuscript.docx')


def read(name):
    with open(os.path.join(MS, name), encoding='utf-8') as f:
        return f.read().rstrip('\n')


def insert_after(text, anchor, block):
    i = text.find(anchor)
    if i < 0:
        raise SystemExit('[err] anchor not found: %r' % anchor[:70])
    j = text.find('\n\n', i)
    if j < 0:
        j = len(text)
    return text[:j] + '\n\n' + block + text[j:]


# ---------------------------------------------------------------- captions
CAP = {
 'Fig. 0': ('figures/fig0_study_overview.png',
  'Study overview and graphical abstract. (a) The five protocol stages — data and spatial '
  'partition, discovery-side sandbox, freeze and hash, separated evaluation, and protocol audit '
  '— joined by the frozen product each stage hands to the next. (b) The three adversarial '
  'checks applied to the frozen candidates: conventional learners (Baseline B), external '
  'replication on Changchun 2021, and the constraint-and-firewall stress test (Baseline D). '
  '(c) The verdict, stated at the same weight as the positive primary endpoint: no new urban '
  'LST law is established; the reproducible contributions are methodological. The locked-region '
  'evaluation is reported under a documented protocol deviation; the Changchun replication and '
  'the Stage-05 adversarial benchmarks are post-hoc.'),
 'Fig. 1': ('figures/fig1_protocol_split.png',
  'Design of the discovery–validation firewall. The built-up area of Shenzhen partitioned at '
  '100 m cells into region A (discovery, 19,184 cells), region B (development validation, '
  '6,182), the locked region C (2,987) and a one-cell-width buffer (R = 15 cells ≈ 1.5 km, '
  '3,407 cells); each 100 m cell is drawn as one square, and the 988 out-of-scope / no-data '
  'cells form a named neutral class (isolated pockets below a four-cell minimum mapping unit '
  'are merged into the surrounding region for legibility) carrying no data. Administrative '
  'district boundaries inside the study area follow the authors’ '
  'community-face polygons and are drawn as vector lines over the cell mosaic; the inset locates the '
  'study footprint within Shenzhen’s nine districts. The partition is the connected-k-means split '
  '(k = 5, seed 20260924). Design only; no analysis is shown.'),
 'Fig. 2': ('figures/fig2_baselineB.png',
  'The candidate does not beat a conventional learner on the locked region. (a) Locked-region '
  'ΔRMSE against Baseline A with 95% spatial-block bootstrap confidence intervals, sorted. '
  '(b) Region-A CV, B and C RMSE trajectories, showing the inversion: the candidate leads on '
  'the selection region and is overtaken on the locked region (C, post-hoc).'),
 'Fig. 3': ('figures/fig3_search.png',
  'The greedy search improves the development metric with diminishing returns. (a) Region-A '
  'cross-validated RMSE against the number of terms, with the Baseline A reference and '
  'staggered term labels. (b) All fifteen candidates, complexity against region-A CV RMSE, '
  'coloured by status; one off-scale marker denotes the A-CV = 23.2 outlier. Region-A CV is '
  'the selection metric, not a generalisation estimate.'),
 'Fig. 4': ('figures/fig4_validation.png',
  'The locked-region improvement is positive under the primary specification but criterion-sensitive and comparator-dependent. (a) ΔRMSE across specifications — the primary '
  'endpoint, the conservative R = 25 criterion, three NDVI strata, and ±0.5 K and ±1.0 K '
  'target-noise draws — with confidence intervals where available. (b) Reference ladder placing '
  'the candidate against the constant floor and a row-shuffled pseudo-candidate. Both '
  'reservations, the R = 25 criterion and the weak comparator, are shown explicitly.'),
 'Fig. 5': ('figures/fig5_external.png',
  'Post-hoc partial external replication on Changchun 2021. Shenzhen is analysed at 100 m and '
  'Changchun at 500 m, so this is not a scale-matched replication. (a) Δ CV RMSE against the '
  'matched linear baseline A* for the frozen-form projections. (b) Single-variable pivot test: '
  'linear, quadratic and exponential NDVI, and exp(DEM). (c) Signed direction per shared '
  'covariate, with DEM flagged as non-reproducing. Changchun is external, post-hoc data; '
  'partial agreement is not confirmation.'),
 'Fig. 6': ('figures/fig6_baselineD.png',
  '(Exploratory combined-pipeline stress test.) In this run the admissibility constraints were '
  'associated with better locked-region behaviour, and the firewall prevented one concrete '
  'selection-leakage failure mode. (a) Region-A CV, B '
  'and C RMSE for Baseline A, the unconstrained agent (Baseline D, Arm 1) and the constrained '
  'candidate. (b) Firewall-off ladder: honest selection, selection directly on C, and refitting '
  'on the union of A, B and C. (c) Population profile of the unconstrained search '
  '(audit-rejected and over-cap fractions). Arm 2 touches region C only as an explicit ablation '
  'and writes nothing to the frozen logs.'),
}


def fig(label):
    path, cap = CAP[label]
    return '@@FIG %s | %s | %s' % (path, label, cap)


# --------------------------------------------------------------- assembly
TITLE = ('Auditable autonomous symbolic discovery of urban thermal relationships with '
         'admissibility constraints and separated validation')
SUB = ('[Authors to be completed] · [Affiliations to be completed] · '
       '[Corresponding author to be completed] · Working draft, Stage 05')

ABSTRACT = [
 '**Background.** Agentic, structure-agnostic symbolic search can propose interpretable '
 'expressions from data, but on spatially autocorrelated environmental targets a flexible '
 'search can exploit the evaluation protocol, and it is rarely possible to separate an '
 'agent’s fitting ability from the contribution of its constraints and its evaluation design. '
 'We ask what admissibility constraints and the separation of discovery from evaluation '
 'actually contribute when an autonomous agent is asked to discover relationships between '
 'urban morphology, surface characteristics, and land surface temperature (LST).',
 '**Methods.** Using a 100 m analysis grid of the built-up area of Shenzhen, China (31,760 '
 'cells), we partitioned the city into a discovery region A (19,184 cells), a '
 'development-validation region B (6,182) and an encrypted region C (2,987), separated by a '
 '1.5 km buffer. A symbolic search with physics-aware admissibility constraints — a curated '
 'operator pool, a complexity cap and a numerical-conditioning audit — ran inside a sandbox '
 'restricted to the development regions; candidates were frozen and hashed before any '
 'candidate-specific evaluation. A subsequent implementation audit found that validation-side '
 'self-tests had decrypted Region-C targets before Stage-03 candidate discovery, a documented '
 'protocol deviation from the intended single-access design. The frozen candidate was '
 'evaluated on the locked region, then benchmarked post hoc against conventional learners '
 '(random forest and gradient boosting) and re-examined post hoc on a second city '
 '(Changchun, 2021).',
 '**Results.** The leading candidate met the pre-registered primary endpoint on the locked '
 'region (ΔRMSE +0.3791 °C against a linear baseline, permutation p = 0.005, 95% CI '
 '[0.2761, 0.4814]); p = 0.005 is the minimum attainable value at the permutation budget of '
 '199. The effect did not survive a more conservative contiguity criterion (R = 25: +0.1375 '
 '°C, p = 0.085) and rested on a weak comparator; a random forest on the same covariates '
 'more than doubled the gain (ΔRMSE +0.7465 °C) and a gradient-boosted model reached +0.7500 '
 '°C. On Changchun the analysis, conducted post hoc, produced a partial conceptual overlap '
 'while the frozen form did not transfer. In an exploratory combined-pipeline stress test, '
 'removing the admissibility constraints improved the development regions but degraded the '
 'locked region, and removing the firewall manufactured a spurious +0.35 °C gain that '
 'vanished on the development regions.',
 '**Conclusions.** No portable urban thermal law was established. The stronger contribution '
 'is methodological: an auditable symbolic-search pipeline with admissibility constraints, '
 'evaluated on a separated locked region under a documented protocol deviation, and subjected '
 'to post-hoc adversarial benchmarking and a post-hoc external replication. The pipeline '
 'returns partial directional concordance and an audited negative methodological finding, '
 'not a portable quantitative law.',
]
KEYWORDS = ('**Keywords:** physics-aware admissibility constraints; symbolic regression; '
            'autonomous scientific discovery; urban land surface temperature; '
            'urban morphology and surface characteristics; '
            'separated validation; data leakage; spatial cross-validation')


def build_master():
    intro = read('intro_en.md')
    methods = read('methods_en.md')
    r1 = read('results1_en.md')
    r2 = read('results2_en.md')
    r3 = read('results3_en.md')
    r4 = read('results4_en.md')
    disc = read('discussion_en.md')
    decl = read('declarations_en.md')
    refs = read('references_en.md')

    # --- section-number alignment
    methods = methods.replace('# Methods', '# 2. Methods', 1)
    r1 = r1.replace('# Results 1 — The discovery process',
                    '# 3. Results 1 — The discovery process', 1)
    r1 = r1.replace('## 1.', '## 3.').replace('(Section 2.1)', '(Section 4.1)')
    r2 = r2.replace('# Results 2 — Locked-region evaluation of frozen candidates',
                    '# 4. Results 2 — Locked-region evaluation of frozen candidates', 1)
    r2 = r2.replace('## 2.', '## 4.')
    r3 = r3.replace('# Results 3 — Post-hoc partial replication on an independent city '
                    '(Changchun, 2021)',
                    '# 5. Results 3 — Post-hoc partial replication on an independent city '
                    '(Changchun, 2021)', 1)
    r3 = r3.replace('## 3.', '## 5.')
    r4 = r4.replace('# Results 4 — Fair comparison with conventional models',
                    '# 6. Results 4 — Fair comparison with conventional models', 1)
    r4 = r4.replace('## 4.', '## 6.').replace('§4.6', '§6.6')

    # --- discussion split: §7 Discussion (7.1–7.5) then §8 Limitations
    i_lim = disc.index('## 5.6 Limitations')
    head, lim = disc[:i_lim], disc[i_lim:]
    head = head.replace('# Discussion', '# 7. Discussion', 1)
    for _k in range(1, 6):
        head = head.replace('## 5.%d ' % _k, '## 7.%d ' % _k)
    lim = lim.replace('## 5.6 Limitations', '# 8. Limitations', 1)
    disc_body = head.rstrip('\n')
    limitations = lim

    # --- in-text figure cross-references
    intro = intro.replace(
        'and every access is written to a hash-chained, append-only log.',
        'and every access is written to a hash-chained, append-only log (Fig. 1 gives the '
        'design).')
    intro = intro.replace(
        'Its contributions are methodological, and one of them is deliberately negative.',
        'Its contributions are methodological, and one of them is deliberately negative '
        '(Fig. 0 gives the overall design).')
    intro = intro.replace(
        'The ablation illustrates one concrete failure mode the firewall prevented in this run.',
        'The ablation illustrates one concrete failure mode the firewall prevented in this run '
        '(Fig. 6).')
    intro = intro.replace(
        'and its expressible nonlinear components did not transfer quantitatively.',
        'and its expressible nonlinear components did not transfer quantitatively (Fig. 5).')
    methods = methods.replace(
        'between C and the discovery regions.',
        'between C and the discovery regions (Fig. 1).')
    r1 = r1.replace(
        'only from 3.0655 to 2.9139 °C (0.152 °C).',
        'only from 3.0655 to 2.9139 °C (0.152 °C; Fig. 3).')
    r4 = r4.replace(
        'not a matter of significance but of magnitude.',
        'not a matter of significance but of magnitude (Fig. 2).')
    disc_body = disc_body.replace(
        'a combined-pipeline stress test, not a controlled isolation of either factor.',
        'a combined-pipeline stress test, not a controlled isolation of either factor (Fig. 6).')
    disc_body = disc_body.replace(
        'Fourth, and most directly, a random forest',
        'Fourth, and most directly (Fig. 2), a random forest')

    # --- insert figure blocks
    methods = insert_after(methods,
        'A further 3,407 cells form a one-cell-width spatial buffer (R = 15 cells ≈ 1.5 km) '
        'between C and the discovery regions', fig('Fig. 1'))
    r1 = insert_after(r1, 'Subsequent terms yield diminishing returns.', fig('Fig. 3'))
    r2 = insert_after(r2,
        'which isolates the rejection to the effect size rather than to a mechanical failure.',
        fig('Fig. 2'))
    r2 = insert_after(r2, 'but that comparison was not the pre-registered endpoint.', fig('Fig. 4'))
    r3 = insert_after(r3,
        'the pipeline yields only **partial cross-city directional concordance, not replication '
        'of a transferable quantitative structure**.', fig('Fig. 5'))
    r4 = insert_after(r4,
        'As with all region-C numbers in this section, these are post-hoc and exploratory.',
        fig('Fig. 6'))

    parts = []
    parts.append('@@TITLE %s' % TITLE)
    parts.append('')
    parts.append('@@SUB %s' % SUB)
    parts.append('')
    parts.append('## Abstract')
    parts.append('')
    for p in ABSTRACT:
        parts.append(p)
        parts.append('')
    parts.append(KEYWORDS)
    parts.append('')
    parts.append(fig('Fig. 0'))
    parts.append('')
    parts.append(intro)
    parts.append('')
    parts.append(methods)
    parts.append('')
    parts.append(r1)
    parts.append('')
    parts.append(r2)
    parts.append('')
    parts.append(r3)
    parts.append('')
    parts.append(r4)
    parts.append('')
    parts.append(disc_body)
    parts.append('')
    parts.append(limitations)
    parts.append('')
    parts.append(decl)
    parts.append('')
    parts.append('@@PB')
    parts.append('')
    parts.append(refs)
    return '\n'.join(parts) + '\n'


# --------------------------------------------------------------- rendering
INLINE = re.compile(r'(\*\*.+?\*\*|\*[^*]+?\*|`[^`]+?`)')


def add_runs(par, text, size=None):
    for tok in INLINE.split(text):
        if not tok:
            continue
        if tok.startswith('**') and tok.endswith('**') and len(tok) > 4:
            r = par.add_run(tok[2:-2]); r.bold = True
        elif tok.startswith('*') and tok.endswith('*') and len(tok) > 2:
            r = par.add_run(tok[1:-1].replace('`', '')); r.italic = True
        elif tok.startswith('`') and tok.endswith('`') and len(tok) > 2:
            r = par.add_run(tok[1:-1]); r.font.name = 'Consolas'
        else:
            r = par.add_run(tok)
        if size:
            r.font.size = Pt(size)
    return par


def style_doc(doc):
    normal = doc.styles['Normal']
    normal.font.name = 'Arial'
    normal.font.size = Pt(10.5)
    normal.paragraph_format.space_after = Pt(6)
    normal.paragraph_format.line_spacing = 1.12
    sizes = {'Title': 16, 'Heading 1': 14, 'Heading 2': 12, 'Heading 3': 11}
    for name, sz in sizes.items():
        st = doc.styles[name]
        st.font.name = 'Arial'
        st.font.size = Pt(sz)
        st.font.bold = True
        st.font.color.rgb = RGBColor(0, 0, 0)


def render(md_text):
    doc = Document()
    style_doc(doc)
    for sec in doc.sections:
        sec.page_width = Mm(210)          # A4
        sec.page_height = Mm(297)
        sec.top_margin = sec.bottom_margin = Inches(0.85)
        sec.left_margin = sec.right_margin = Inches(0.9)

    lines = md_text.split('\n')
    i, n = 0, len(lines)
    buf = []

    def flush():
        if buf:
            txt = ' '.join(x.strip() for x in buf).strip()
            if txt:
                add_runs(doc.add_paragraph(), txt)
            buf.clear()

    while i < n:
        s = lines[i].strip()
        if s.startswith('@@TITLE '):
            flush()
            p = doc.add_paragraph(style='Title')
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            add_runs(p, s[len('@@TITLE '):])
        elif s.startswith('@@SUB '):
            flush()
            p = doc.add_paragraph()
            r = p.add_run(s[len('@@SUB '):]); r.italic = True; r.font.size = Pt(9.5)
            r.font.color.rgb = RGBColor(0x59, 0x59, 0x59)
        elif s.startswith('@@PB'):
            flush()
            doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)
        elif s.startswith('@@FIG '):
            flush()
            path, label, cap = [x.strip() for x in s[len('@@FIG '):].split('|', 2)]
            p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            width = Inches(5.0) if 'fig1_' in path else Inches(6.4)
            p.add_run().add_picture(os.path.join(S05, path), width=width)
            cp = doc.add_paragraph(); cp.alignment = WD_ALIGN_PARAGRAPH.LEFT
            r = cp.add_run(label + ' | '); r.bold = True; r.font.size = Pt(9)
            add_runs(cp, cap, size=9)
        elif s == '':
            flush()
        elif s.startswith('|'):
            flush()
            rows = []
            while i < n and lines[i].strip().startswith('|'):
                rows.append(lines[i].strip())
                i += 1
            i -= 1
            cells = [r.strip('|').split('|') for r in rows]
            cells = [[c.strip() for c in row] for row in cells]
            body = [cells[0]] + cells[2:] if len(cells) > 1 else cells
            ncol = max(len(r) for r in body)
            t = doc.add_table(rows=0, cols=ncol)
            t.style = 'Table Grid'
            t.autofit = True
            for ri, row in enumerate(body):
                rc = t.add_row().cells
                for ci in range(ncol):
                    txt = row[ci] if ci < len(row) else ''
                    par = rc[ci].paragraphs[0]
                    par.paragraph_format.space_after = Pt(1)
                    par.paragraph_format.line_spacing = 1.0
                    add_runs(par, txt, size=8)
                    if ri == 0:
                        for rr in par.runs:
                            rr.bold = True
        elif s.startswith('#'):
            flush()
            lvl = len(s) - len(s.lstrip('#'))
            doc.add_paragraph(s.lstrip('#').strip(),
                              style='Heading %d' % min(lvl, 3))
        elif s.startswith('> '):
            flush()
            p = doc.add_paragraph()
            p.paragraph_format.left_indent = Inches(0.35)
            add_runs(p, s[2:])
            for rr in p.runs:
                rr.italic = True
        elif s.startswith('- '):
            flush()
            p = doc.add_paragraph(style='List Bullet')
            add_runs(p, s[2:])
        elif re.match(r'^\d+\.\s', s):
            flush()
            p = doc.add_paragraph()
            p.paragraph_format.left_indent = Inches(0.28)
            add_runs(p, s)
        else:
            buf.append(s)
        i += 1
    flush()
    return doc


def main():
    md = build_master()
    with open(OUT_MD, 'w', encoding='utf-8') as f:
        f.write(md)
    print('[md]   wrote %s (%d chars)' % (os.path.relpath(OUT_MD, os.path.dirname(S05)),
                                          len(md)))
    doc = render(md)
    doc.core_properties.title = TITLE
    doc.core_properties.comments = 'PAID Stage 05 assembled manuscript'
    doc.save(OUT_DOCX)
    print('[docx] wrote %s' % os.path.relpath(OUT_DOCX, os.path.dirname(S05)))


if __name__ == '__main__':
    main()
