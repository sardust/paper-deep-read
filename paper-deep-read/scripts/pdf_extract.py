#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""PDF 文本抽取为按页分节的 Markdown，保留页码锚点。

用法:
    python pdf_extract.py <pdf路径> [--out 输出.md] [--start 1] [--end 9999]
                          [--max-chars 200000] [--ocr-hint]

优先使用 PyMuPDF (pymupdf)，缺失时回退 pypdf。
输出中每页以 <!-- page N --> 标记，便于把证据锚定到具体页码。

若 PDF 为扫描件（抽取文本极少），脚本会打印提示，请改用 Read 工具
直接读取 PDF（Read 工具支持视觉解析）或先做 OCR。
"""

import argparse
import os
import sys


def extract_with_fitz(path, start, end):
    try:
        import pymupdf as fitz  # PyMuPDF >= 1.24 推荐入口
    except ImportError:
        import fitz  # 旧版入口

    pages = []
    with fitz.open(path) as doc:
        total = doc.page_count
        for i in range(total):
            page_no = i + 1
            if page_no < start or page_no > end:
                continue
            text = doc[i].get_text("text")
            pages.append((page_no, text))
    return pages, len(pages)


def extract_with_pypdf(path, start, end):
    from pypdf import PdfReader

    reader = PdfReader(path)
    total = len(reader.pages)
    pages = []
    for i in range(total):
        page_no = i + 1
        if page_no < start or page_no > end:
            continue
        try:
            text = reader.pages[i].extract_text() or ""
        except Exception as exc:  # 单页失败不终止整体
            text = f"<<本页抽取失败: {exc}>>"
        pages.append((page_no, text))
    return pages, total


def clean(text):
    """压缩多余空行，但保留段落分隔与代码块缩进。"""
    lines = [ln.rstrip() for ln in text.replace("\r\n", "\n").split("\n")]
    out = []
    blank = 0
    for ln in lines:
        if not ln.strip():
            blank += 1
            if blank > 2:
                continue
        else:
            blank = 0
        out.append(ln)
    return "\n".join(out).strip()


def main():
    ap = argparse.ArgumentParser(description="PDF -> Markdown（按页保留页码锚点）")
    ap.add_argument("pdf", help="PDF 文件路径")
    ap.add_argument("--out", "-o", default="", help="输出 Markdown 路径，默认打印到 stdout")
    ap.add_argument("--start", type=int, default=1, help="起始页（含），默认 1")
    ap.add_argument("--end", type=int, default=99999, help="结束页（含），默认全部")
    ap.add_argument("--max-chars", type=int, default=200000,
                    help="输出字符上限，超出则截断并提示分段，默认 200000")
    ap.add_argument("--ocr-hint", action="store_true",
                    help="即使抽取成功也打印扫描件排查提示")
    args = ap.parse_args()

    if not os.path.isfile(args.pdf):
        print(f"[ERR] 文件不存在: {args.pdf}", file=sys.stderr)
        return 2

    backend = ""
    try:
        pages, total = extract_with_fitz(args.pdf, args.start, args.end)
        backend = "PyMuPDF"
    except ImportError:
        try:
            pages, total = extract_with_pypdf(args.pdf, args.start, args.end)
            backend = "pypdf"
        except ImportError:
            print("[ERR] 需要 PyMuPDF 或 pypdf。请先安装其一：\n"
                  "  pip install pymupdf\n"
                  "  或 pip install pypdf", file=sys.stderr)
            return 3

    chunks = [f"<!-- source: {os.path.basename(args.pdf)} | backend: {backend} | total_pages: {total} -->"]
    total_chars = 0
    truncated_at = None
    for page_no, text in pages:
        body = clean(text)
        if not body:
            body = "<!-- 本页无可抽取文本（可能是图/表/扫描图） -->"
        piece = f"\n<!-- page {page_no} -->\n\n{body}\n"
        if total_chars + len(piece) > args.max_chars:
            truncated_at = page_no
            chunks.append(piece[: max(0, args.max_chars - total_chars)])
            break
        chunks.append(piece)
        total_chars += len(piece)

    result = "".join(chunks)

    if args.out:
        out_dir = os.path.dirname(os.path.abspath(args.out))
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(result)
        print(f"[OK] {args.pdf} -> {args.out}  ({len(result)} chars, {len(pages)} pages, backend={backend})")
    else:
        sys.stdout.reconfigure(encoding="utf-8")
        print(result)

    if truncated_at:
        print(f"[WARN] 达到 --max-chars={args.max_chars} 上限，在第 {truncated_at} 页截断。"
              f"建议提高上限或用 --start/--end 分段抽取。", file=sys.stderr)
    if args.ocr_hint:
        print("[HINT] 若关键章节显示「无可抽取文本」，该 PDF 可能是扫描件，"
              "请改用 Read 工具读取 PDF（支持视觉解析）或先做 OCR。", file=sys.stderr)

    avg = sum(len(t) for _, t in pages) / max(1, len(pages))
    if avg < 100:
        print(f"[WARN] 平均每页仅 {avg:.0f} 字符，很可能不是文本型 PDF（扫描件/纯图片）。"
              f"请改用 Read 工具读取 PDF。", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
