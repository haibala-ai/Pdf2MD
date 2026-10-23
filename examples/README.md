# 示例 PDF

`pdfs/` 包含两份公开论文，标题、版本、来源地址与 SHA-256 见 [manifest.json](manifest.json)，作者与许可见 [第三方说明](../THIRD_PARTY_NOTICES.md)。不需要在运行时重新下载。

从项目根目录运行：

```bash
bash scripts/run.sh --input examples/pdfs --tier basic --model-source modelscope
```

Windows PowerShell：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run.ps1 -InputPath .\examples\pdfs -Tier basic -ModelSource modelscope
```

输出位于 `output/<PDF 文件名>/basic/`。先看 `markdown.md`，再通过 `review.md` 与 `page_index.md` 核对数学内容。示例 PDF 的版式不代表所有论文或扫描件。
