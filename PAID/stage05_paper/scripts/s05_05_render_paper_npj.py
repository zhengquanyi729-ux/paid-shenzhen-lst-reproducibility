"""
S05.5 合稿（npj Urban Sustainability 版）
=========================================================================
把分节英文正文重排为目标期刊 **npj Urban Sustainability（Nature Portfolio）**
稿件，输出：
  - `manuscript/manuscript_npj_en.md`               母本（可审阅）
  - `manuscript/PAID_Shenzhen_LST_manuscript_npj.docx`  投稿用 Word

与 S05.4（通用合稿）相比，本脚本只改**版式与结构**，不改任何数字或结论。
它完成的、逐节草稿里没有的事：

  1. **章节顺序改为 Nature Portfolio 体例**：
     Title → Abstract（单段、无小标题）→ Keywords → Introduction
     → Results（合并原 Results 1–4）→ Discussion（合并原 §7 与 Limitations）
     → Methods（移到 Discussion 之后）→ 声明 → References。
     Nature 系不编号章节，因此去掉所有 "1./2./3." 与 "5.1" 式小标题编号。
  2. **摘要改为单段、无小标题**，长度压到约 200 词（npj 要求 single paragraph,
     无参考文献、无小标题）。
  3. **正文引文改为 Nature 上标数字**（`<sup>n</sup>`），参考文献表改为 `n. ` 序。
     数字引文只出现在 Introduction；Results/Discussion 中的 `[129, 622]` 等是格网
     单元号，不是引文，故上标化只作用于 Introduction 文本。
  4. **图随文重排、按出现顺序编号**（旧 Fig 0–6 → 新 Fig 1–7）：
       旧 0（研究总览）    → 新 Fig 1（正文首页）
       旧 1（防火墙分区）  → 新 Fig 2（正文首页，设计图）
       旧 3（搜索轨迹）    → 新 Fig 3（Results·发现）
       旧 4（规格曲线）    → 新 Fig 4（Results·锁定区验证）
       旧 5（外部复现）    → 新 Fig 5（Results·外部复现）
       旧 2（基线 B 反转） → 新 Fig 6（Results·常规模型对比）
       旧 6（基线 D 消融） → 新 Fig 7（Results·消融）
     并补齐原稿缺失的图内引文（新 Fig 4/6/7 在正文各引一次）。
  5. **声明按 npj 排布**：Data availability 置于 References 之前；其余声明紧随其后。

图件文件仍沿用 `figures/fig0_..fig6_*.png`，本脚本只重排"标签与位置"，不改文件；
Stage 05 清单校验（V5/V11）检查文件存在性，因此不受重编号影响。
用法：python3 stage05_paper/scripts/s05_05_render_paper_npj.py
"""
import os
import re

from docx import Document
from docx.shared import Pt, Inches, Mm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK

_HERE = os.path.dirname(os.path.abspath(__file__))
S05 = os.path.dirname(_HERE)
MS = os.path.join(S05, 'manuscript')
OUT_MD = os.path.join(MS, 'manuscript_npj_en.md')
OUT_DOCX = os.path.join(MS, 'PAID_Shenzhen_LST_manuscript_npj.docx')


def read(name):
    with open(os.path.join(MS, name), encoding='utf-8') as f:
        return f.read().rstrip('\n')


def block(md, heading):
    """Return the body (heading stripped) of a `## heading` subsection."""
    i = md.index('## ' + heading)
    j = md.find('\n## ', i)
    seg = md[i:j] if j >= 0 else md[i:]
    return seg.split('\n', 1)[1].strip('\n')


def drop_headings(md, headings):
    for h in headings:
        md = md.replace(h + '\n', '')
    return re.sub(r'\n{3,}', '\n\n', md)


def unnumber_subsections(md):
    return re.sub(r'(?m)^## \d+\.\d+ ', '## ', md)


def insert_after(text, anchor, blk):
    i = text.find(anchor)
    if i < 0:
        raise SystemExit('[err] anchor not found: %r' % anchor[:70])
    j = text.find('\n\n', i)
    if j < 0:
        j = len(text)
    return text[:j] + '\n\n' + blk + text[j:]


# ---------------------------------------------------------------- captions
CAP = {
 'Fig. 1': ('figures/fig0_study_overview.png',
  'Study overview and graphical abstract. (a) The five protocol stages — data and spatial '
  'partition, discovery-side sandbox, freeze and hash, separated evaluation, and protocol audit '
  '— joined by the frozen product each stage hands to the next. (b) The three adversarial '
  'checks applied to the frozen candidates: conventional learners (Baseline B), external '
  'replication on Changchun 2021, and the constraint-and-firewall stress test (Baseline D). '
  '(c) The verdict, stated at the same weight as the positive primary endpoint: no new urban '
  'LST law is established; the reproducible contributions are methodological. The locked-region '
  'evaluation is reported under a documented protocol deviation; the Changchun replication and '
  'the Stage-05 adversarial benchmarks are post-hoc.'),
 'Fig. 2': ('figures/fig1_protocol_split.png',
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
 'Fig. 6': ('figures/fig2_baselineB.png',
  'The candidate does not beat a conventional learner on the locked region. (a) Locked-region '
  'ΔRMSE against Baseline A with 95% spatial-block bootstrap confidence intervals, sorted. '
  '(b) Region-A CV, B and C RMSE trajectories, showing the inversion: the candidate leads on '
  'the selection region and is overtaken on the locked region (C, post-hoc).'),
 'Fig. 7': ('figures/fig6_baselineD.png',
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


# --------------------------------------------------------------- front matter
TITLE = ('Auditable autonomous symbolic discovery of urban thermal relationships with '
         'admissibility constraints and separated validation')

SUB = ('[Authors to be completed] · [Affiliations to be completed] · [Corresponding author to be '
       'completed] · Prepared for npj Urban Sustainability (Nature Portfolio) · '
       'Initial submission draft')

ABSTRACT = (
 'Agentic, structure-agnostic symbolic search can propose interpretable expressions from data, '
 'but on spatially autocorrelated environmental targets a flexible search can exploit the '
 'evaluation protocol, and the contribution of an agent’s admissibility constraints is usually '
 'entangled with its fitting ability. Here we ask what physics-aware admissibility constraints '
 'and a separated locked-region evaluation actually contribute when an autonomous agent is asked '
 'to discover how urban morphology and surface characteristics relate to land surface '
 'temperature (LST). Using '
 'a 100 m grid of Shenzhen, China (31,760 cells), we partitioned the city into a discovery '
 'region, a development-validation region and an encrypted region separated by a 1.5 km buffer; '
 'a symbolic search with admissibility constraints ran inside a sandbox restricted to the '
 'development regions. The leading candidate met a pre-registered endpoint on the locked region '
 '(ΔRMSE +0.3791 °C, permutation p = 0.005, the minimum attainable value at 199 permutations), '
 'but an implementation audit found that validation-side self-tests had decrypted Region-C '
 'targets before candidate discovery, so the evaluation is reported as a locked-region '
 'evaluation under a documented protocol deviation rather than a pristine confirmatory test. '
 'The effect did not survive a conservative contiguity criterion (R = 25: +0.1375 °C, '
 'p = 0.085), rested on a weak comparator, and was beaten by a random forest on the same '
 'covariates. A post-hoc external replication on a second city was partial. No portable urban '
 'thermal law was established; the stronger contribution is methodological.'
)

KEYWORDS = ('**Keywords:** physics-aware admissibility constraints; symbolic regression; '
            'autonomous scientific discovery; urban land surface temperature; '
            'urban morphology and surface characteristics; '
            'separated validation; data leakage; spatial cross-validation; preregistration')


# --------------------------------------------------------------- assembly
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

    # ---- Introduction: flatten subheadings, rewrite roadmap, renumber figure cites,
    #      convert numeric citations to Nature superscripts
    intro = intro.replace('# 1. Introduction', '# Introduction', 1)
    intro = drop_headings(intro, [
        '## 1.1 Motivation',
        '## 1.2 Physics-constrained and knowledge-informed machine learning',
        '## 1.3 Automated model discovery and symbolic regression',
        '## 1.4 The validation problem',
        '## 1.5 This study'])
    intro = intro.replace(
        'The remainder of the paper is organised as follows. Section 2 describes the data, the '
        'admissibility constraints, the separation of discovery from evaluation, and the '
        'discovery loop. Section 3 reports the discovery process and the candidate registry. '
        'Section 4 reports the locked-region evaluation of the frozen candidates. Section 5 '
        'reports the post-hoc external replication. Section 6 compares the candidate against '
        'conventional and ablated baselines. Section 7 discusses what the protocol did and did '
        'not establish, and Section 8 states its limitations.',
        'The remainder of the paper is organised as follows. Results reports the discovery '
        'process and the candidate registry, the locked-region evaluation of the frozen '
        'candidates, the post-hoc external replication on an independent city, and the '
        'comparison against conventional and ablated baselines. The Discussion states what the '
        'protocol did and did not establish and its limitations, and Methods describes the '
        'data, the admissibility constraints, the separation of discovery from evaluation, and '
        'the discovery loop.')
    intro = intro.replace('(Fig. 0 gives the overall design)', '(Fig. 1 gives the overall design)')
    intro = intro.replace('each may be unsealed at most once (Fig. 1).',
                          'each may be unsealed at most once (Fig. 2).')
    intro = intro.replace('The ablation shows quantitatively what the firewall is preventing '
                          '(Fig. 6).',
                          'The ablation shows quantitatively what the firewall is preventing.')
    intro = intro.replace('reproduces, while the specific frozen expression does not transfer '
                          '(Fig. 5).',
                          'reproduces, while the specific frozen expression does not transfer.')
    intro = re.sub(r'\[(\d{1,2}(?:\s*[,–]\s*\d{1,2})*)\]', r'<sup>\1</sup>', intro)

    # ---- Methods: de-number subsections, drop its Data/code subsection (moved to decls),
    #      add the partition-figure citation, move Methods to after Discussion at assembly
    methods = unnumber_subsections(methods)
    i_dc = methods.index('## Data and code availability')
    methods = methods[:i_dc].rstrip('\n')
    methods = methods.replace('between C and the discovery regions.',
                              'between C and the discovery regions (Fig. 2).')

    # ---- Results: merge r1–r4 under one heading, de-number subsections, fix cross-refs,
    #      add figure citations and (re)insert figure blocks in appearance order
    r1 = r1.replace('# Results 1 — The discovery process\n', '', 1)
    r2 = r2.replace('# Results 2 — Locked-region evaluation of frozen candidates\n', '', 1)
    r3 = r3.replace('# Results 3 — Post-hoc partial replication on an independent city '
                    '(Changchun, 2021)\n', '', 1)
    r4 = r4.replace('# Results 4 — Fair comparison with conventional models\n', '', 1)
    r1, r2, r3, r4 = (unnumber_subsections(x) for x in (r1, r2, r3, r4))

    r1 = r1.replace('the candidate-specific evaluation is reported in Results 2',
                    'the candidate-specific evaluation is reported in Results')
    r1 = r1.replace('it is also the placebo in the validation stage (Section 2.1).',
                    'it is also the placebo in the validation stage.')
    r1 = insert_after(r1, 'Subsequent terms yield diminishing returns.', fig('Fig. 3'))

    r2 = r2.replace('The primary result therefore depends on the spatial criterion used to '
                    'define the locked region.',
                    'The primary result therefore depends on the spatial criterion used to '
                    'define the locked region (Fig. 4).')
    r2 = insert_after(r2, 'but that comparison was not the pre-registered endpoint.', fig('Fig. 4'))

    r3 = r3.replace('the single unsealing event reported in Results 2.',
                    'the single unsealing event reported in Results.')
    r3 = r3.replace('Taken with Results 2 and 4, the replication reinforces',
                    'Taken together with the validation and comparison results, the replication '
                    'reinforces')
    r3 = insert_after(r3, 'the pipeline yields only **partial cross-city directional '
                          'concordance, not replication of a transferable quantitative '
                          'structure**.', fig('Fig. 5'))

    r4 = r4.replace('reported separately in §4.6.', 'reported separately below.')
    r4 = r4.replace('not a matter of significance but of magnitude.',
                    'not a matter of significance but of magnitude (Fig. 6).')
    r4 = insert_after(r4, 'so the gap is not explained by a missing transform.', fig('Fig. 6'))
    r4 = r4.replace('As with all region-C numbers in this section, these are post-hoc and '
                    'exploratory.',
                    'As with all region-C numbers in this section, these are post-hoc and '
                    'exploratory (Fig. 7).')
    r4 = insert_after(r4, 'As with all region-C numbers in this section, these are post-hoc and '
                          'exploratory (Fig. 7).', fig('Fig. 7'))

    # ---- Discussion: merge §7 + Limitations + Outlook, flatten subheads, fix cross-refs
    disc = re.sub(r'(?m)^## 5\.\d+ .*$\n', '', disc)
    disc = re.sub(r'\n{3,}', '\n\n', disc)
    disc = disc.replace('a combined-pipeline stress test, not a controlled isolation of either '
                        'factor.',
                        'a combined-pipeline stress test, not a controlled isolation of either '
                        'factor (Fig. 7).')
    disc = disc.replace('Fourth, and most directly, a random forest',
                        'Fourth, and most directly (Fig. 6), a random forest')
    disc = disc.replace('both are quantified in Results 2 and both reduce confidence',
                        'both are quantified in the validation results and both reduce '
                        'confidence')

    # ---- Declarations, reordered for npj (availability statements first, then the rest)
    decls = []
    for h in ['Data availability', 'Code availability', 'Author contributions',
              'Competing interests', 'Funding', 'Acknowledgements', 'Ethics',
              'AI usage disclosure']:
        decls.append('# %s\n\n%s' % (h, block(decl, h)))

    # ---- References: Nature-style numbered list
    refs = re.sub(r'(?m)^\[(\d+)\]\s+', r'\1. ', refs)

    parts = []
    parts.append('@@TITLE %s' % TITLE)
    parts += ['', '@@SUB %s' % SUB, '']
    parts += ['# Abstract', '', ABSTRACT, '', KEYWORDS, '']
    parts += [fig('Fig. 1'), '', fig('Fig. 2'), '']
    parts += [intro, '']
    parts += ['# Results', '', r1, '', r2, '', r3, '', r4, '']
    parts += [disc, '']
    parts += ['@@PB', '', methods, '']
    parts += ['@@PB', '', '\n\n'.join(decls), '']
    parts += ['@@PB', '', refs]
    return '\n'.join(parts) + '\n'


# --------------------------------------------------------------- rendering
INLINE = re.compile(r'(<sup>.+?</sup>|\*\*.+?\*\*|\*[^*]+?\*|`[^`]+?`)')


def add_runs(par, text, size=None):
    for tok in INLINE.split(text):
        if not tok:
            continue
        if tok.startswith('<sup>') and tok.endswith('</sup>'):
            r = par.add_run(tok[5:-6]); r.font.superscript = True
        elif tok.startswith('**') and tok.endswith('**') and len(tok) > 4:
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
    doc.core_properties.comments = 'PAID Stage 05 manuscript formatted for npj Urban Sustainability'
    doc.save(OUT_DOCX)
    print('[docx] wrote %s' % os.path.relpath(OUT_DOCX, os.path.dirname(S05)))


if __name__ == '__main__':
    main()
