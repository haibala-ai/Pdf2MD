# 扫描件测试样例

`pipnn-page3-scan.pdf` 由 `examples/pdfs/pipnn_kdd2026_best_research_v3.pdf` 第 3 页以 108 dpi 渲染后制作，是单页、无原生文本层的图像 PDF。用于手工验证 OCR 回退与英文覆盖率不适用的处理，不代表所有扫描质量。

原论文：Tobias Rubel 等，*PiPNN: Ultra-Scalable Graph-Based Nearest Neighbor Indexing*，[arXiv 2602.21247v3](https://arxiv.org/abs/2602.21247v3)，CC BY 4.0。原 PDF SHA-256：`75e9048e910590a6a998ee8b43a1bd498779aecaf90352f6a93da022dbe5a0d9`。

运行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run.ps1 -InputPath .\tests\fixtures\pipnn-page3-scan.pdf -ModelSource modelscope
```
