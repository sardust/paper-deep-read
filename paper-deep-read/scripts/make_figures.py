#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""生成精读报告用的自制图示：思维导图 + 论文结构图（matplotlib，中文字体自适应）。

用法:
    python make_figures.py --kind mindmap --out out.png --title "论文标题" \
        --node "主矛盾|问题文本" --node "补法1|文本" ...
    python make_figures.py --kind structure --out out.png --title "标题" \
        --stage "问题层|说明" --stage "机制层|说明" ...

说明:
    --kind mindmap   以中心主矛盾为根，向右展开的因果修补链（横向树状思维导图）
    --kind structure 纵向阶段流程图，用于呈现论文的三层拆解结构
"""

import argparse
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
from matplotlib import font_manager

# 中文字体候选
CJK_CANDIDATES = [
    "Microsoft YaHei", "SimHei", "SimSun", "Noto Sans CJK SC",
    "Source Han Sans SC", "WenQuanYi Zen Hei", "DengXian",
]


def pick_font():
    avail = {f.name for f in font_manager.fontManager.ttflist}
    for name in CJK_CANDIDATES:
        if name in avail:
            return name
    return None


# 配色（浅色主题）
C_ROOT = "#FCEBEB"
C_ROOT_EDGE = "#A32D2D"
C_ROOT_TXT = "#501313"
C_L1 = ["#E6F1FB", "#E1F5EE", "#FAEEDA", "#EEEDFE", "#FBEAF0", "#EAF3DE"]
C_L1_EDGE = ["#185FA5", "#0F6E56", "#854F0B", "#534AB7", "#993556", "#3B6D11"]
C_L1_TXT = ["#042C53", "#04342C", "#412402", "#26215C", "#4B1528", "#173404"]
C_GAP = "#F1EFE8"
C_GAP_EDGE = "#5F5E5A"
C_GAP_TXT = "#2C2C2A"


def wrap_cjk(text, width):
    """按显示宽度折行：CJK 字符计 1，ASCII 计 0.55。"""
    if not isinstance(text, str):
        text = str(text)
    out, cur, w = [], "", 0.0
    for ch in text:
        cw = 1.0 if ord(ch) > 0x2E80 else 0.55
        if ch == "\n":
            out.append(cur)
            cur, w = "", 0.0
            continue
        if w + cw > width:
            out.append(cur)
            cur, w = "", 0.0
        cur += ch
        w += cw
    if cur:
        out.append(cur)
    return "\n".join(out)


def draw_mindmap(ax, nodes, title, font, fontname):
    """横向思维导图：中心主矛盾 + 右侧因果链。"""
    root_label, root_sub = nodes[0]
    branches = nodes[1:]

    root_w, root_h = 3.4, 2.3
    n = len(branches)
    box_w = 6.2
    box_h = max(0.95, 15.0 / max(n, 1))
    gap = 0.42

    total_h = max(n * box_h + (n - 1) * gap, root_h)
    top = total_h / 2

    # 中心节点
    rcy = 0.0
    ax.add_patch(FancyBboxPatch(
        (-6.6, rcy - root_h / 2), root_w, root_h,
        boxstyle="round,pad=0.06,rounding_size=0.12",
        fc=C_ROOT, ec=C_ROOT_EDGE, lw=1.0, zorder=3))
    root_body = wrap_cjk(root_sub, 15)
    root_lines = root_body.count("\n") + 1
    ax.text(-6.6 + root_w / 2, rcy + root_h / 2 - 0.26, "主矛盾",
            ha="center", va="center", fontsize=11.5, color=C_ROOT_EDGE, fontname=fontname)
    ax.text(-6.6 + root_w / 2, rcy - (root_lines - 1) * 0.19 - 0.12,
            root_body,
            ha="center", va="center", fontsize=10, color=C_ROOT_TXT,
            fontname=fontname, linespacing=1.5)

    ys = []
    y = total_h / 2 - box_h / 2
    for i in range(n):
        ys.append(y)
        y -= (box_h + gap)

    for i, b in enumerate(branches):
        label = b[0]
        sub = b[1] if len(b) > 1 else ""
        fc = C_L1[i % len(C_L1)]
        ec = C_L1_EDGE[i % len(C_L1_EDGE)]
        tc = C_L1_TXT[i % len(C_L1_TXT)]

        x0 = -2.7
        ax.add_patch(FancyBboxPatch(
            (x0, ys[i] - box_h / 2), box_w, box_h,
            boxstyle="round,pad=0.06,rounding_size=0.1",
            fc=fc, ec=ec, lw=1.0, zorder=3))
        if sub:
            ax.text(x0 + 0.22, ys[i] + box_h / 2 - 0.22, label,
                    ha="left", va="center", fontsize=11, color=tc,
                    fontname=fontname, fontweight="medium")
            ax.text(x0 + 0.22, ys[i] - 0.08, wrap_cjk(sub, 50),
                    ha="left", va="center", fontsize=9.5, color=ec,
                    fontname=fontname, linespacing=1.45)
        else:
            ax.text(x0 + box_w / 2, ys[i], wrap_cjk(label, 50),
                    ha="center", va="center", fontsize=11, color=tc,
                    fontname=fontname, linespacing=1.5)

        # 连接线
        ax.add_patch(FancyArrowPatch(
            (-3.2, rcy), (x0 - 0.06, ys[i]),
            connectionstyle="arc3,rad=0.0", arrowstyle="-|>",
            mutation_scale=13, lw=1.1, color="#888780", zorder=2))

    ax.set_xlim(-7.0, x0 + box_w + 0.3)
    ax.set_ylim(-total_h / 2 - 0.35, total_h / 2 + 0.85)
    ax.axis("off")
    if title:
        ax.set_title(title, fontsize=13, color=C_GAP_TXT, fontname=fontname, pad=14)


def draw_structure(ax, stages, title, font, fontname):
    """纵向阶段流程图。"""
    n = len(stages)
    box_w, box_h = 8.4, 1.42
    gap = 0.5
    total_h = n * box_h + (n - 1) * gap

    y = total_h / 2 - box_h / 2
    for i, (label, sub) in enumerate(stages):
        if label in ("剩余缺口", "缺口", "剩余"):
            fc, ec, tc = C_GAP, C_GAP_EDGE, C_GAP_TXT
        else:
            k = i % len(C_L1)
            fc, ec, tc = C_L1[k], C_L1_EDGE[k], C_L1_TXT[k]

        wrapped = wrap_cjk(sub, 40)
        ax.add_patch(FancyBboxPatch(
            (-box_w / 2, y - box_h / 2), box_w, box_h,
            boxstyle="round,pad=0.06,rounding_size=0.12",
            fc=fc, ec=ec, lw=1.0, zorder=3))
        ax.text(-box_w / 2 + 0.3, y + box_h / 2 - 0.26, label,
                ha="left", va="center", fontsize=11.5, color=tc,
                fontname=fontname, fontweight="medium")
        ax.text(-box_w / 2 + 0.3, y - 0.06, wrapped,
                ha="left", va="center", fontsize=9.5, color=ec,
                fontname=fontname, linespacing=1.4)

        if i < n - 1:
            ax.add_patch(FancyArrowPatch(
                (0, y - box_h / 2), (0, y - box_h / 2 - gap + 0.02),
                arrowstyle="-|>", mutation_scale=14, lw=1.2, color="#888780", zorder=2))
        y -= (box_h + gap)

    ax.set_xlim(-box_w / 2 - 0.3, box_w / 2 + 0.3)
    ax.set_ylim(-total_h / 2 - 0.3, total_h / 2 + 0.5)
    ax.axis("off")
    if title:
        ax.set_title(title, fontsize=13, color=C_GAP_TXT, fontname=fontname, pad=14)


def main():
    ap = argparse.ArgumentParser(description="生成思维导图 / 结构图")
    ap.add_argument("--kind", choices=["mindmap", "structure"], required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--title", default="")
    ap.add_argument("--node", action="append", default=[], help="标签|说明")
    ap.add_argument("--stage", action="append", default=[], help="阶段名|说明")
    ap.add_argument("--json", default="",
                    help="JSON 文件传参，格式 {\"title\":\"...\",\"items\":[[\"标签\",\"说明\"],...]}。"
                         "含中文时推荐用此方式，避免 shell 拆参问题")
    ap.add_argument("--width", type=float, default=11.0)
    ap.add_argument("--height", type=float, default=7.0)
    args = ap.parse_args()

    fname = pick_font()
    if not fname:
        print("[WARN] 未找到中文字体，图中的中文可能显示为方框。"
              "可安装 Microsoft YaHei 或 Noto Sans CJK。", file=sys.stderr)
    plt.rcParams["axes.unicode_minus"] = False

    if args.json:
        import json as _json
        with open(args.json, "r", encoding="utf-8") as f:
            spec = _json.load(f)
        args.title = spec.get("title", args.title)
        raw_items = spec.get("items", [])
    else:
        raw_items = args.node if args.kind == "mindmap" else args.stage

    items = [tuple(x) for x in raw_items]
    if len(items) < 1:
        print("[ERR] 至少需要一个 --node / --stage 或非空 --json", file=sys.stderr)
        return 2

    parsed = []
    for it in items:
        parts = [str(v) for v in it]
        label = parts[0].strip() if len(parts) > 0 else ""
        sub = parts[1].strip() if len(parts) > 1 else ""
        parsed.append((label, sub))

    fig, ax = plt.subplots(figsize=(args.width, args.height), dpi=200)
    fig.patch.set_alpha(0.0)
    ax.set_facecolor("none")

    if args.kind == "mindmap":
        draw_mindmap(ax, parsed, args.title, fname, fname)
    else:
        draw_structure(ax, parsed, args.title, fname, fname)

    out_dir = os.path.dirname(os.path.abspath(args.out))
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    fig.savefig(args.out, transparent=True, bbox_inches="tight", pad_inches=0.18)
    plt.close(fig)
    print(f"[OK] {args.kind} -> {args.out}  font={fname or 'fallback'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
