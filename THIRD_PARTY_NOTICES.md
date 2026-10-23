# 第三方材料与来源

日期：2026-10-23。项目只从 PDF 解析内容，转换结果不代表作者发布的原始 Markdown，也不表示作者认可识别结果。转发时保留本说明、论文署名及相应原始许可。

## 附带 PDF

1. **PiPNN: Ultra-Scalable Graph-Based Nearest Neighbor Indexing**，Tobias Rubel、Richard Wen、Laxman Dhulipala、Lars Gottesbüren、Rajesh Jayaram、Jakub Łącki。使用 [arXiv 2602.21247v3](https://arxiv.org/abs/2602.21247v3) 的 [PDF](https://arxiv.org/pdf/2602.21247v3)，18 页。
2. **Characterizing the Expressivity of Local Attention in Transformers**，Jiaoda Li、Ryan Cotterell。使用 [ACL Anthology 正式版本](https://aclanthology.org/2026.acl-long.1739/) 的 [PDF](https://aclanthology.org/2026.acl-long.1739.pdf)，23 页。

PDF 版本与 SHA-256 见 [示例清单](examples/manifest.json)。相应公开论文页面标注 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)。项目中的 Markdown、JSON、页面截图和局部截图来自这些论文，改变了格式和排版，可能包含识别错误。

`tests/fixtures/` 中若有样例扫描 PDF，它来自 PiPNN 第 3 页的渲染图，仅用于验证无文本层时的 OCR 回退，仍应保留上述论文来源及许可。

## 解析器与模型

[MinerU](https://github.com/opendatalab/MinerU) 4.0.12 及其传递依赖通过 `requirements/locked.txt` 安装，模型首次使用时下载至 `.mineru/`。各代码包和模型权重适用各自发布的许可证；本说明不替代这些许可证。

[BioMiner](https://github.com/jiaxianyan/BioMiner) 是最初调研参考，本项目只复用了 PDF 解析与结构化证据保留的思路，没有部署其生物抽取模型。

当前项目不包含作者源码重建、Pandoc 或 KaTeX 渲染组件。
