#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""从论文 PDF 中裁剪导出实验图（Figure），用于精读报告插图。

用法:
    python pdf_figures.py <pdf路径> --out-dir <输出目录>
                         [--pages 4,5,6,7]
                         [--dpi 200]
                         [--fig1 Fig.1 --fig2 Fig.2]

工作原理:
    1. 扫描页面上的矢量绘图与内嵌位图，聚类成候选图区。
    2. 裁剪并导出为 PNG，默认只导出「面积足够大且非页眉页脚」的图区。
    3. 输出一个JSON 清单，记录每张图对应的页码与裁剪框，便于在报告里引用。

只导出图片区域，不做 OCR。若论文是扫描件，请改用 Read 工具读取 PDF。
"""

import argparse
import json
import os
import sys

import pymupdf


def page_drawings_bbox(page, min_area_ratio=0.03):
    """收集页面上的矢量绘图簇，返回候选 bbox 列表。"""
    boxes = []
    try:
        drawings = page.get_drawings()
    except Exception:
        return boxes
    for dr in drawings:
        r = dr.get("rect")
        if r is None or r.is_empty:
            continue
        page_area = page.rect.width * page.rect.height
        if page_area <= 0:
            continue
        if (r.width * r.height) / page_area < min_area_ratio:
            continue
        boxes.append(pymupdf.Rect(r))
    return boxes


def merge_boxes(boxes, gap=8):
    """把相互重叠/邻近的 bbox 合并成簇。"""
    merged = []
    for b in sorted(boxes, key=lambda r: -r.width * r.height):
        placed = False
        for i, m in enumerate(merged):
            if not (b.x0 > m.x1 + gap or b.x1 < m.x0 - gap
                    or b.y0 > m.y1 + gap or b.y1 < m.y0 - gap):
                m |= b
                placed = True
                break
        if not placed:
            merged.append(pymupdf.Rect(b))
    # 二次合并
    changed = True
    while changed and len(merged) > 1:
        changed = False
        for i in range(len(merged)):
            for j in range(i + 1, len(merged)):
                if not (merged[i].x0 > merged[j].x1 + gap or merged[i].x1 < merged[j].x0 - gap
                        or merged[i].y0 > merged[j].y1 + gap or merged[i].y1 < merged[j].y0 - gap):
                    merged[i] |= merged[j]
                    del merged[j]
                    changed = True
                    break
            if changed:
                break
    return merged


def caption_hint(page, rect, max_dy=90):
    """读取图区上/下方最近的图注文本，用于自动命名。"""
    band = pymupdf.Rect(rect.x0, rect.y1, rect.x1, min(page.rect.height, rect.y1 + max_dy))
    try:
        txt = page.get_text("text", clip=band).strip()
    except Exception:
        txt = ""
    for line in txt.split("\n"):
        s = line.strip()
        if s.lower().startswith("fig"):
            return " ".join(s.split())[:80]
    return ""


def export_figures(pdf, out_dir, dpi, only_pages=None, min_area_ratio=0.03):
    os.makedirs(out_dir, exist_ok=True)
    doc = pymupdf.open(pdf)
    manifest = []
    idx = 0
    zoom = dpi / 72.0

    for pno in range(doc.page_count):
        page = doc[pno]
        if only_pages and (pno + 1) not in only_pages:
            continue
        candidates = []

        for im in page.get_images(full=True):
            try:
                bb = page.get_image_bbox(im)
            except Exception:
                continue
            if bb and not bb.is_empty:
                candidates.append(pymupdf.Rect(bb))

        candidates.extend(page_drawings_bbox(page, min_area_ratio))
        clusters = merge_boxes(candidates)

        page_area = page.rect.width * page.rect.height
        for r in sorted(clusters, key=lambda x: (round(x.y0 / 40), x.x0)):
            area_ratio = (r.width * r.height) / page_area
            if area_ratio < min_area_ratio:
                continue
            # 过滤整页宽但极扁的页眉分隔线
            if r.height < 60:
                continue
            pad = 3
            clip = pymupdf.Rect(
                max(0, r.x0 - pad), max(0, r.y0 - pad),
                min(page.rect.width, r.x1 + pad),
                min(page.rect.height, r.y1 + pad),
            )
            pix = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), clip=clip, alpha=False)
            idx += 1
            name = f"fig{idx}_p{pno + 1}.png"
            path = os.path.join(out_dir, name)
            pix.save(path)
            manifest.append({
                "file": name,
                "page": pno + 1,
                "clip": [round(v, 1) for v in clip],
                "px": [pix.width, pix.height],
                "caption_hint": caption_hint(page, r),
            })
    doc.close()
    return manifest


def main():
    ap = argparse.ArgumentParser(description="从论文 PDF 裁剪导出实验图")
    ap.add_argument("pdf", help="论文 PDF 路径")
    ap.add_argument("--out-dir", required=True, help="图片输出目录")
    ap.add_argument("--pages", default="", help="仅导出指定页（逗号分隔，如 4,5,6）")
    ap.add_argument("--dpi", type=int, default=200, help="导出 DPI，默认 200")
    ap.add_argument("--min-area", type=float, default=0.03,
                    help="最小面积占比，低于此值视为装饰元素丢弃，默认 0.03")
    args = ap.parse_args()

    if not os.path.isfile(args.pdf):
        print(f"[ERR] 文件不存在: {args.pdf}", file=sys.stderr)
        return 2

    only_pages = None
    if args.pages:
        only_pages = set()
        for tok in args.pages.split(","):
            tok = tok.strip()
            if tok:
                only_pages.add(int(tok))

    manifest = export_figures(args.pdf, args.out_dir, args.dpi, only_pages, args.min_area)

    mf_path = os.path.join(args.out_dir, "manifest.json")
    with open(mf_path, "w", encoding="utf-8") as f:
        json.dump({"pdf": os.path.basename(args.pdf), "figures": manifest},
                  f, ensure_ascii=False, indent=2)

    print(f"[OK] 导出 {len(manifest)} 张图-> {args.out_dir}")
    for m in manifest:
        hint = m["caption_hint"] or "(无图注)"
        print(f"  {m['file']}  p{m['page']}  {m['px'][0]}x{m['px'][1]}  {hint}")
    print(f"[OK] 清单-> {mf_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
