#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""由结构化 JSON 生成精读报告 Word 文档（含自制图示 + 论文原图引用）。

用法:
    python build_report_docx.py <report.json> --out <报告.docx>

report.json 结构（顶层均为可选，除 meta / sections 外均可省略）:
{
  "meta": {"title": "...", "subtitle": "...", "authors": "...", "venue": "...",
           "date": "2026-10-19", "pdf": "xxx.pdf", "tags": ["AI4S","天文CV"]},
  "summary": ["要点1", "要点2"],
  "figures": [                       # 自制图示（由 make_figures.py 预先生成）
    {"path": "fig1.png", "caption": "图1  ...", "note": "..."}
  ],
  "sections": [
    {"heading": "一、问题层", "level": 1,
     "blocks": [
       {"type": "para", "text": "..."},
       {"type": "bullets", "items": ["...", "..."]},
       {"type": "numbered", "items": ["..."]},
       {"type": "kv", "items": [["键","值"], ...]},          # 表格
       {"type": "quote", "text": "...", "source": "论文 §3.2"},
       {"type": "evidence", "claim": "...", "evidence": "...", "boundary": "...", "level": "A"},
       {"type": "boundary", "kind": "能力边界", "text": "..."},
       {"type": "table", "header": ["...","..."], "rows": [["a","b"], ...]},
       {"type": "image", "path": "fig2.png", "caption": "图2  ...",
        "source": "论文 Figure 4（第7 页）", "highlight": "..."},
       {"type": "callout", "tone": "warn|info|ok", "title": "...", "text": "..."},
       {"type": "pagebreak"}
     ]}
  ]
}

设计要点:
  - 论文原图必须带 source（页码/图号），实现「引用」而非「搬运」。
  - highlight 字段会在图下渲染一段加粗的「核心结论」提示。
  - 中文使用 Microsoft YaHei，西文 Calibri。
"""

import json
import os
import sys

from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.section import WD_SECTION
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

CN_FONT = "Microsoft YaHei"
EN_FONT = "Calibri"

C_PRIMARY = RGBColor(0x1A, 0x1A, 0x1A)
C_MUTED = RGBColor(0x5F, 0x5E, 0x5A)
C_ACCENT = RGBColor(0x1F, 0x4E, 0x79)
C_DANGER = RGBColor(0xA3, 0x2D, 0x2D)
C_OK = RGBColor(0x0F, 0x6E, 0x56)
C_WARN = RGBColor(0x85, 0x4F, 0x0B)

SH_HEAD = "DCE6F1"
SH_INFO = "E6F1FB"
SH_WARN = "FAEEDA"
SH_OK = "E1F5EE"
SH_DANGER = "FCEBEB"
SH_GRAY = "F1EFE8"


def set_run_font(run, size=None, bold=None, color=None, italic=None):
    if size is not None:
        run.font.size = Pt(size)
    if bold is not None:
        run.font.bold = bold
    if italic is not None:
        run.font.italic = italic
    if color is not None:
        run.font.color.rgb = color
    run.font.name = EN_FONT
    rpr = run._element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.append(rfonts)
    rfonts.set(qn("w:ascii"), EN_FONT)
    rfonts.set(qn("w:hAnsi"), EN_FONT)
    rfonts.set(qn("w:eastAsia"), CN_FONT)


def shade(cell_or_para, hex_color):
    el = cell_or_para._tc if hasattr(cell_or_para, "_tc") else cell_or_para._p.get_or_add_pPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_color)
    if hasattr(cell_or_para, "_tc"):
        cell_or_para._tc.get_or_add_tcPr().append(shd)
    else:
        el.append(shd)


def set_cell_borders(cell, color="BFBFBF", sz="4"):
    tcPr = cell._tc.get_or_add_tcPr()
    borders = OxmlElement("w:tcBorders")
    for edge in ("top", "left", "bottom", "right"):
        e = OxmlElement(f"w:{edge}")
        e.set(qn("w:val"), "single")
        e.set(qn("w:sz"), sz)
        e.set(qn("w:color"), color)
        borders.append(e)
    tcPr.append(borders)


def para_shade(paragraph, hex_color):
    pPr = paragraph._p.get_or_add_pPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_color)
    pPr.append(shd)


def left_bar(paragraph, color="1F4E79", sz="18"):
    pPr = paragraph._p.get_or_add_pPr()
    pbdr = OxmlElement("w:pBdr")
    e = OxmlElement("w:left")
    e.set(qn("w:val"), "single")
    e.set(qn("w:sz"), sz)
    e.set(qn("w:space"), "8")
    e.set(qn("w:color"), color)
    pbdr.append(e)
    pPr.append(pbdr)


def setup_document(doc):
    sec = doc.sections[0]
    sec.top_margin = Cm(2.2)
    sec.bottom_margin = Cm(2.2)
    sec.left_margin = Cm(2.6)
    sec.right_margin = Cm(2.6)

    style = doc.styles["Normal"]
    style.font.name = EN_FONT
    style.font.size = Pt(10.5)
    style.element.rPr.rFonts.set(qn("w:eastAsia"), CN_FONT)
    pf = style.paragraph_format
    pf.line_spacing = 1.5
    pf.space_after = Pt(6)

    for lvl, size in ((1, 16), (2, 13), (3, 11.5)):
        st = doc.styles[f"Heading {lvl}"]
        st.font.name = EN_FONT
        st.font.size = Pt(size)
        st.font.bold = True
        st.font.color.rgb = C_ACCENT if lvl <= 2 else C_PRIMARY
        st.element.rPr.rFonts.set(qn("w:eastAsia"), CN_FONT)


def add_footer(doc, text):
    footer = doc.sections[0].footer
    p = footer.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(text)
    set_run_font(r, size=8, color=C_MUTED)


def add_para(doc, text, size=10.5, bold=False, color=C_PRIMARY,
             align=None, space_after=6, indent=None, italic=False):
    p = doc.add_paragraph()
    if align is not None:
        p.alignment = align
    p.paragraph_format.space_after = Pt(space_after)
    if indent is not None:
        p.paragraph_format.left_indent = Cm(indent)
    # 支持 **加粗** 片段
    parts = str(text).split("**")
    for i, seg in enumerate(parts):
        if not seg:
            continue
        r = p.add_run(seg)
        set_run_font(r, size=size, bold=(bold or i % 2 == 1), color=color, italic=italic)
    return p


def add_heading(doc, text, level=1):
    h = doc.add_heading(level=level)
    r = h.add_run(text)
    size = {1: 16, 2: 13, 3: 11.5}.get(level, 11)
    color = C_ACCENT if level <= 2 else C_PRIMARY
    set_run_font(r, size=size, bold=True, color=color)
    h.paragraph_format.space_before = Pt(14 if level == 1 else 10)
    h.paragraph_format.space_after = Pt(6)
    return h


def add_table(doc, header, rows, widths=None):
    t = doc.add_table(rows=1, cols=len(header))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    hdr = t.rows[0].cells
    for i, htxt in enumerate(header):
        shade(hdr[i], SH_HEAD)
        set_cell_borders(hdr[i])
        p = hdr[i].paragraphs[0]
        r = p.add_run(str(htxt))
        set_run_font(r, size=9.5, bold=True, color=C_PRIMARY)
    for row in rows:
        cells = t.add_row().cells
        for i, val in enumerate(row):
            if i >= len(header):
                break
            set_cell_borders(cells[i])
            p = cells[i].paragraphs[0]
            p.paragraph_format.space_after = Pt(2)
            parts = str(val).split("**")
            for j, seg in enumerate(parts):
                if not seg:
                    continue
                r = p.add_run(seg)
                set_run_font(r, size=9.5, bold=(j % 2 == 1), color=C_PRIMARY)
    if widths:
        for row in t.rows:
            for i, w in enumerate(widths):
                if i < len(row.cells):
                    row.cells[i].width = Cm(w)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)
    return t


def add_image(doc, path, caption=None, source=None, highlight=None, width_cm=15.0):
    if not os.path.isfile(path):
        add_para(doc, f"[图片缺失: {path}]", size=9.5, color=C_DANGER, italic=True)
        return
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(6)
    p.paragraph_format.space_after = Pt(2)
    p.add_run().add_picture(path, width=Cm(width_cm))

    if caption:
        cap = doc.add_paragraph()
        cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
        cap.paragraph_format.space_after = Pt(2)
        r = cap.add_run(caption)
        set_run_font(r, size=9, bold=True, color=C_PRIMARY)

    if source:
        s = doc.add_paragraph()
        s.alignment = WD_ALIGN_PARAGRAPH.CENTER
        s.paragraph_format.space_after = Pt(2)
        r = s.add_run(f"图片来源：{source}")
        set_run_font(r, size=8.5, color=C_MUTED, italic=True)

    if highlight:
        hp = doc.add_paragraph()
        hp.paragraph_format.left_indent = Cm(0.4)
        hp.paragraph_format.space_before = Pt(2)
        hp.paragraph_format.space_after = Pt(8)
        para_shade(hp, SH_INFO)
        left_bar(hp, "1F4E79")
        r1 = hp.add_run("核心结论：")
        set_run_font(r1, size=9.5, bold=True, color=C_ACCENT)
        parts = str(highlight).split("**")
        for i, seg in enumerate(parts):
            if not seg:
                continue
            r = hp.add_run(seg)
            set_run_font(r, size=9.5, bold=(i % 2 == 1), color=C_PRIMARY)


def add_callout(doc, tone, title, text):
    palette = {
        "info": (SH_INFO, "1F4E79", C_ACCENT),
        "warn": (SH_WARN, "854F0B", C_WARN),
        "ok": (SH_OK, "0F6E56", C_OK),
        "danger": (SH_DANGER, "A32D2D", C_DANGER),
        "gray": (SH_GRAY, "5F5E5A", C_MUTED),
    }
    bg, bar, fg = palette.get(tone, palette["gray"])
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Cm(0.3)
    p.paragraph_format.space_before = Pt(6)
    p.paragraph_format.space_after = Pt(8)
    para_shade(p, bg)
    left_bar(p, bar)
    if title:
        r0 = p.add_run(f"{title}  ")
        set_run_font(r0, size=10, bold=True, color=fg)
    parts = str(text).split("**")
    for i, seg in enumerate(parts):
        if not seg:
            continue
        r = p.add_run(seg)
        set_run_font(r, size=10, bold=(i % 2 == 1), color=C_PRIMARY)


def add_evidence(doc, claim, evidence, boundary, level="A"):
    lv_color = {"A": C_OK, "B": C_ACCENT, "C": C_WARN, "D": C_MUTED, "E": C_DANGER}
    lv_name = {"A": "A级（主结果表）", "B": "B级（消融）", "C": "C级（敏感性/复杂度）",
               "D": "D级（可视化）", "E": "E级（仅作者自述）"}
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Cm(0.3)
    p.paragraph_format.space_before = Pt(8)
    p.paragraph_format.space_after = Pt(3)
    r = p.add_run(f"【证据强度 {lv_name.get(level, level)}】")
    set_run_font(r, size=9.5, bold=True, color=lv_color.get(level, C_MUTED))

    rows = [
        ["主张", claim],
        ["最强证据", evidence],
        ["边界", boundary],
    ]
    t = doc.add_table(rows=0, cols=2)
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for k, v in rows:
        cells = t.add_row().cells
        set_cell_borders(cells[0])
        set_cell_borders(cells[1])
        shade(cells[0], SH_GRAY)
        rk = cells[0].paragraphs[0].add_run(k)
        set_run_font(rk, size=9.5, bold=True, color=C_PRIMARY)
        pv = cells[1].paragraphs[0]
        pv.paragraph_format.space_after = Pt(2)
        parts = str(v).split("**")
        for i, seg in enumerate(parts):
            if not seg:
                continue
            r = pv.add_run(seg)
            set_run_font(r, size=9.5, bold=(i % 2 == 1), color=C_PRIMARY)
        cells[0].width = Cm(2.4)
        cells[1].width = Cm(12.6)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)


def add_boundary(doc, kind, text):
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Cm(0.3)
    p.paragraph_format.space_before = Pt(4)
    p.paragraph_format.space_after = Pt(4)
    para_shade(p, SH_WARN)
    left_bar(p, "854F0B", "12")
    r1 = p.add_run(f"【{kind}】")
    set_run_font(r1, size=9.5, bold=True, color=C_WARN)
    parts = str(text).split("**")
    for i, seg in enumerate(parts):
        if not seg:
            continue
        r = p.add_run(seg)
        set_run_font(r, size=9.5, bold=(i % 2 == 1), color=C_PRIMARY)


def render_blocks(doc, blocks, base_dir=""):
    for b in blocks or []:
        t = b.get("type", "para")
        if t == "para":
            add_para(doc, b.get("text", ""))
        elif t == "bullets":
            for it in b.get("items", []):
                p = doc.add_paragraph(style="List Bullet")
                p.paragraph_format.space_after = Pt(3)
                parts = str(it).split("**")
                for i, seg in enumerate(parts):
                    if not seg:
                        continue
                    r = p.add_run(seg)
                    set_run_font(r, size=10.5, bold=(i % 2 == 1), color=C_PRIMARY)
        elif t == "numbered":
            for it in b.get("items", []):
                p = doc.add_paragraph(style="List Number")
                p.paragraph_format.space_after = Pt(3)
                parts = str(it).split("**")
                for i, seg in enumerate(parts):
                    if not seg:
                        continue
                    r = p.add_run(seg)
                    set_run_font(r, size=10.5, bold=(i % 2 == 1), color=C_PRIMARY)
        elif t == "table":
            add_table(doc, b.get("header", []), b.get("rows", []), b.get("widths"))
        elif t == "kv":
            add_table(doc, [b.get("key_header", "项"), b.get("val_header", "说明")],
                      [list(x) for x in b.get("items", [])], b.get("widths"))
        elif t == "image":
            path = b.get("path", "")
            if base_dir and not os.path.isabs(path):
                path = os.path.join(base_dir, path)
            add_image(doc, path, b.get("caption"), b.get("source"),
                      b.get("highlight"), b.get("width_cm", 15.0))
        elif t == "callout":
            add_callout(doc, b.get("tone", "info"), b.get("title", ""), b.get("text", ""))
        elif t == "evidence":
            add_evidence(doc, b.get("claim", ""), b.get("evidence", ""),
                         b.get("boundary", ""), b.get("level", "A"))
        elif t == "boundary":
            add_boundary(doc, b.get("kind", "边界"), b.get("text", ""))
        elif t == "quote":
            p = doc.add_paragraph()
            p.paragraph_format.left_indent = Cm(0.8)
            p.paragraph_format.space_before = Pt(4)
            p.paragraph_format.space_after = Pt(4)
            r = p.add_run(b.get("text", ""))
            set_run_font(r, size=10, italic=True, color=C_MUTED)
            if b.get("source"):
                add_para(doc, f"— {b['source']}", size=8.5, color=C_MUTED, indent=0.8)
        elif t == "pagebreak":
            doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)
        else:
            add_para(doc, f"[未知 block 类型: {t}]", color=C_DANGER)


def build(report, out_path):
    doc = Document()
    setup_document(doc)

    meta = report.get("meta", {})
    base_dir = os.path.dirname(os.path.abspath(out_path))

    # 标题区
    add_para(doc, meta.get("title", "论文精读报告"),
             size=20, bold=True, color=C_ACCENT, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=4)
    if meta.get("subtitle"):
        add_para(doc, meta["subtitle"], size=11.5, color=C_MUTED,
                 align=WD_ALIGN_PARAGRAPH.CENTER, space_after=4)
    info_bits = [meta.get(k, "") for k in ("authors", "venue", "date") if meta.get(k)]
    if info_bits:
        add_para(doc, "  |  ".join(info_bits), size=9.5, color=C_MUTED,
                 align=WD_ALIGN_PARAGRAPH.CENTER, space_after=4)
    if meta.get("pdf"):
        add_para(doc, f"原文：{meta['pdf']}", size=9, color=C_MUTED,
                 align=WD_ALIGN_PARAGRAPH.CENTER, space_after=2)
    if meta.get("tags"):
        add_para(doc, " · ".join(meta["tags"]), size=9, color=C_MUTED,
                 align=WD_ALIGN_PARAGRAPH.CENTER, space_after=10)

    for sec in report.get("sections", []):
        add_heading(doc, sec.get("heading", ""), sec.get("level", 1))
        render_blocks(doc, sec.get("blocks", []), base_dir)

    add_footer(doc, report.get("footer", "论文精读报告 · 三层分析法"))
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    doc.save(out_path)
    return out_path


def main():
    if len(sys.argv) < 2:
        print("用法: python build_report_docx.py <report.json> --out <报告.docx>", file=sys.stderr)
        return 2
    src = sys.argv[1]
    out = ""
    if "--out" in sys.argv:
        out = sys.argv[sys.argv.index("--out") + 1]
    if not out:
        base = os.path.splitext(os.path.basename(src))[0]
        out = os.path.join(os.path.dirname(os.path.abspath(src)), base + ".docx")

    with open(src, "r", encoding="utf-8") as f:
        report = json.load(f)
    path = build(report, out)
    n_img = sum(1 for s in report.get("sections", []) for b in s.get("blocks", [])
                if b.get("type") == "image")
    print(f"[OK] 报告 -> {path}（{len(report.get('sections', []))} 节，内嵌图片 {n_img} 张）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
