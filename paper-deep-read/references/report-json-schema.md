# report.json 完整示例

配合 `scripts/build_report_docx.py` 使用。所有路径相对于 **Word 输出文件所在目录**，或写绝对路径。

## 最小可用示例

```json
{
  "meta": {
    "title": "论文标题（英文原文）",
    "subtitle": "中文一句话定位：领域 = ... × ...",
    "authors": "X. Liu, J. Liu, ... Y. Wang",
    "venue": "ApJS, 283, 29 (2026)",
    "date": "2026-10-19",
    "pdf": "Liu_2026_ApJS_283_29.pdf",
    "tags": ["AI4S", "天文CV", "日冕物质抛射"]
  },
  "sections": [
    {
      "heading": "核心摘要",
      "level": 1,
      "blocks": [
        {"type": "callout", "tone": "info", "title": "主线",
         "text": "现有缺口 → 作者手段 → 能力跃迁"},
        {"type": "callout", "tone": "ok", "title": "值得跟",
         "text": "少样本适配路线值得借鉴"},
        {"type": "callout", "tone": "danger", "title": "需警惕",
         "text": "LoRA 选型无消融证据"}
      ]
    }
  ]
}
```

## 完整示例（含所有 block 类型）

```json
{
  "meta": {
    "title": "Automated Detection of Coronal Mass Ejections with Few-shot Learning",
    "subtitle": "领域 = 日冕仪白光成像 × CME 像素级分割",
    "authors": "Xin Liu, Jiajia Liu, Shuhua Song, ... Yimin Wang",
    "venue": "The Astrophysical Journal Supplement Series, 283, 29 (2026)",
    "date": "2026-10-19",
    "pdf": "Liu_2026_ApJS_283_29.pdf",
    "tags": ["AI4S", "天文图像处理", "CME", "基础模型适配", "少样本学习"]
  },
  "footer": "SAM-LoRA 精读报告 · 三层分析法",
  "sections": [
    {
      "heading": "核心摘要",
      "level": 1,
      "blocks": [
        {"type": "callout", "tone": "info", "title": "主线",
         "text": "标注瓶颈 → LoRA 把 SAM 微调到只需 **32 张**标注 → 从「全量标注的专用分割模型」推进到「少样本可用的通用基础模型适配」"},
        {"type": "callout", "tone": "ok", "title": "值得跟",
         "text": "**少样本适配路线**这个判断值得借鉴；标签极稀缺的天文领域普遍适用。"},
        {"type": "callout", "tone": "danger", "title": "需警惕",
         "text": "全文**无 LoRA 消融实验**；Table 2 作者自陈测试集不同、数值不可直接比较。"}
      ]
    },
    {
      "heading": "一、问题层",
      "level": 1,
      "blocks": [
        {"type": "para", "text": "作者认为最深的问题是**「通用基础模型无法零样本迁移到日冕域，根源是缺乏领域先验」**，而不是「CNN/Transformer 分割精度不够」。"},
        {"type": "callout", "tone": "info", "title": "为什么这个判断重要",
         "text": "SegFormer（300 张）与 TransCME（100 张）精度已够高，作者没去拼精度而是承认**瓶颈是标签而非模型**——这与「换backbone 提升 2 个点」是相反的思路。"}
      ]
    },
    {
      "heading": "二、机制层",
      "level": 1,
      "blocks": [
        {"type": "image",
         "path": "figs/mindmap.png",
         "caption": "图1  论文思维导图：主矛盾与四层修补链（自制）",
         "highlight": "每一次修补都由上一层的不足逼出，链条在「时序上下文 + CME/激波区分」处中断——这是这篇论文真正的天花板。"},
        {"type": "kv",
         "key_header": "模块",
         "val_header": "解决什么 → 不解决什么",
         "widths": [4.0, 11.0],
         "items": [
           ["LoRA 挂在图像编码器 Q/V 投影", "解决零样本定位失败 + 全量微调算力贵；不解决掩膜边界精度"],
           ["只挂编码器不解码器", "编码器计算最重且聚合位置信息，改它最能提升定位；不解决边界粗糙"],
           ["全帧 bounding box 作 prompt", "免去逐帧交互，使批处理训练可行；引入空掩膜判定新问题"],
           ["BDI + RDI 多通道伪 RGB", "强化暗弱包络与尖锐前缘，解决低对比漏检；不解决窄 CME 与喷流的形态歧义"],
           ["全帧 1024×1024 不切块", "匹配 SAM 默认输入，保留 CME 全局包络；限制可处理视场范围"]
         ]}
      ]
    },
    {
      "heading": "三、证据层",
      "level": 1,
      "blocks": [
        {"type": "evidence",
         "claim": "这套方法整体有效",
         "evidence": "Table 2，CME-only 测试集（100 张）：仅用 **32 张**训练取得 IoU 0.80、MIoU 0.89",
         "boundary": "证明的是**LASCO C2 单台仪器、单帧、二值掩膜任务**上有效，不是 CME 分割任务整体有效",
         "level": "A"},
        {"type": "image",
         "path": "figs/fig2_p4.png",
         "caption": "图2  论文 Figure 1（第 4 页）：全参数微调与 LoRA 微调的结构对比",
         "source": "论文 Figure 1（第 4 页）",
         "width_cm": 11.0,
         "highlight": "这是**方案原理示意**，不是实验结果。它解释了为什么 LoRA 能省算力，但**不构成**「LoRA 优于全量微调」的证据——后者本文未做对照实验。"},
        {"type": "evidence",
         "claim": "不仅有效，而且在数据效率上更优",
         "evidence": "Table 2 训练集规模列：SAM-LoRA **32 张** vs SegFormer **300 张** vs TransCME **100 张**；MIoU 0.89 > SegFormer 0.83",
         "boundary": "作者自己在 §4.1 写明「Table 2 因测试集不同不可直接比较」。为公平起见另做了 Figure 4 逐例对比，但那**只是定性可视化，不是定量表**——严格的定量公平对比论文并未给出",
         "level": "A"},
        {"type": "image",
         "path": "figs/fig4_p7.png",
         "caption": "图3  论文 Figure 4（第 7 页）：SAM-LoRA 与 SegFormer、TransCME 的逐例掩膜对比",
         "source": "论文 Figure 4（第 7 页）",
         "width_cm": 15.0,
         "highlight": "重点看 **(d)(e)(f)** 三列：SegFormer 与 TransCME 在 halo 与宽 CME 上明显漏检或边界破碎，而 SAM-LoRA 给出完整包络。但注意 (a)(b) 列 SAM-LoRA 的掩膜明显更大更粗糙——**这正是「二值掩膜无法区分 CME 本体与激波前沿」的直接证据**，即下方能力边界 1 的图示印证。"},
        {"type": "evidence",
         "claim": "BDI+RDI 多通道设计不是装饰",
         "evidence": "Table 1 输入消融（5 组）：BDI only IoU 0.74 / RDI only 0.75 / **混合 0.80**；加原始强度通道反降至 0.77",
         "boundary": "证明的是**多通道复合优于单模态**，不是「BDI:RDI = 2:1 配比最优」——Table 1 中 2:1、1:2、均值三种配置 IoU **都是 0.80**，通道配比没有差异证据",
         "level": "B"},
        {"type": "callout", "tone": "danger", "title": "关键证据缺口",
         "text": "全文四张表**没有任何实验回答「为什么是 LoRA 而不是全量微调或 adapter」**。rank 取多少、为何只挂 Q/V 而非 K/O、为何只改编码器，均为「我们测了若干值取最优」的叙述而无数据。按证据分级属 **E 级（仅作者自述）**。摘要中「parameter-efficient design reduces cost」靠的是「8 分钟训练完成」这一单点事实，不是对照实验。"}
      ]
    },
    {
      "heading": "四、三重边界",
      "level": 1,
      "blocks": [
        {"type": "boundary", "kind": "能力边界",
         "text": "可做到**二值 CME 包络分割**，但**不能区分 CME 本体与激波前沿**。因为训练使用二值掩膜，作者明确写道分离 CME 与 shock 需要专门的激波标注与多类目标或实例级掩膜头。因此 Figure 4(d)–(f) 中「只有本方法识别出的微弱白色包络」很可能把激波一并框入——这是**能力边界，不是精度优势**。"},
        {"type": "boundary", "kind": "系统边界",
         "text": "解决的是**单帧像素级分割**，没有覆盖**时序关联、跟踪、参数反演与预报**。作者在摘要与结论中均将其表述为「a basis for」「future work will」，即尚未验证。"},
        {"type": "boundary", "kind": "场景/假设边界",
         "text": "依赖 **SOHO/LASCO C2 单一仪器**、单帧、二值掩膜。Table 3 显示性能系统性依赖 CME 角宽度：窄事件 IoU 0.78、halo 事件 0.76 均为最差。作者承认 halo 前缘弥散、背景复杂，且**未在 MLSO K-Cor、STEREO/SECCHI COR1 等低信噪比日冕仪上验证**。此外「掩膜非空即判 CME」的分类规则（Table 4，F1 0.98）**依赖空掩膜阈值，而该阈值全文未给出**，构成复现暗坑。"}
      ]
    },
    {
      "heading": "五、创新点",
      "level": 1,
      "blocks": [
        {"type": "para", "text": "**创新点1（标签效率）**：现有 CME 分割方法需 100–300 张标注才能达可用精度（SegFormer 300、TransCME 100），作者通过 **LoRA 参数高效微调 SAM 编码器**解决了 **32 张标注即达 IoU 0.80 的少样本分割能力**，但仍未解决 **LoRA 选型缺乏对照验证**（对应上文 E 级证据缺口）。"},
        {"type": "para", "text": "**创新点2（低对比前缘）**：现有方法在低对比度 CME 前缘存在漏检，作者通过 **BDI + RDI 多通道伪 RGB 复合**将 IoU 从 0.74 提升到 **0.80**，但仍未解决**单帧无法区分窄 CME 与喷流**（对应能力边界 1、场景边界）。"},
        {"type": "callout", "tone": "info", "title": "自检",
         "text": "两条创新点均能落到第四节的具体边界上。若某条创新点找不到对应边界，说明它是包装而非创新点。"}
      ]
    },
    {
      "heading": "六、一句话结论",
      "level": 1,
      "blocks": [
        {"type": "callout", "tone": "ok", "title": "值得跟",
         "text": "「少样本适配路线」这个判断，而非其具体架构。标签极稀缺的天文领域普遍适用。"},
        {"type": "callout", "tone": "warn", "title": "别引用",
         "text": "**「优于 SegFormer」**——作者自己提醒测试集不可比；**「IoU 0.89 是本架构上限」**——LoRA 深度未被消融，数字可能主要来自 SAM 预训练强度。"},
        {"type": "callout", "tone": "info", "title": "跟哪条线",
         "text": "作者列出的未来工作中，**时序上下文**最有价值也最容易做：正面解决窄 CME/喷流混淆（Table 3 中窄事件 IoU 0.78 是最弱环节），且**无需新标注**，复用 CDAW 目录时间戳即可。"},
        {"type": "callout", "tone": "danger", "title": "结论何时不成立",
         "text": "换到低信噪比仪器（K-Cor、COR1）、换到时序任务、或标注量超过数百张时——前两者论文未验证，第三种情况作者承认 LoRA「capacity limited」，全量微调更优。"}
      ]
    }
  ]
}
```

## 常见写法问题

| 错误 | 正确做法 |
|---|---|
| `image` 缺 `source` | 必须写「论文 Figure X（第 N 页）」，否则是搬运不是引用 |
| `image` 缺 `highlight` | 每张原图都要配「核心结论」，说清它支撑哪条主张 |
| 图号靠抽取顺序猜 | 必须用 Read 工具逐张看图确认 |
| 自制图当原图 | 自制图不写 `source`，原图必写，两者不可混淆 |
| 所有主张都用A级 | 缺消融的应用型论文，模块必要性只能写 E 级并标注「未验证」 |
