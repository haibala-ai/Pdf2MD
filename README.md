# Pdf2MD

将单篇或批量 PDF 转换为 Markdown，并保留质量检查、算法/公式局部原图和逐页对照。支持 Windows PowerShell 与 Linux Bash，使用本地 CPU / ONNX 推理。

- **Basic**：MinerU 4.0.12 完成版面、OCR、公式与表格解析。
- **Flash**：快速提取原生 PDF 内容，不需要推理模型。
- **算法转写**：满足检查条件时优先采用 PDF 原生文字，否则保留 OCR；始终附原图。
- **可追溯输出**：原始识别稿、结构化 JSON、来源/产物哈希、日志、复核清单。

这是命令行批处理工具，执行转换命令即可开始，不需要启动 Web 服务。无需 GPU、API Key、作者 TeX、Pandoc 或 Node.js。**不承诺无损转换**：公式、表格与算法仍需对照原页抽查，详见 [质量说明](docs/QUALITY.md)。

## 1. 环境要求

| 项目 | 要求 |
|---|---|
| Python | 64 位 Python **3.12**；项目不使用 3.13 |
| Windows | Windows x86_64，提供 PowerShell 脚本；已测 Windows 11 |
| Linux | Linux x86_64，提供 Bash 脚本；已测 Ubuntu 24.04 / WSL2 |
| 推理 | CPU + ONNX；本项目入口固定使用该组合 |
| 模型空间 | Basic 的 13 个模型/配置约 **858 MB / 818 MiB** |
| 其他空间 | Python 环境约 1 GB，另为下载缓存、PDF 和输出预留数 GB |
| 网络 | 首次安装与下载模型需要联网；准备完整后可离线运行 |

其他 Linux 发行版需自行提供 Python 3.12、兼容的系统库和 glibc；本项目未验证 macOS、ARM 或 GPU 模式。Windows 与 Linux 的虚拟环境不能混用；ONNX 模型文件可以共用。

## 2. 获取项目

```bash
git clone https://github.com/haibala-ai/Pdf2MD.git
cd Pdf2MD
```

也可以从 GitHub 的 **Code → Download ZIP** 下载并完整解压，在项目根目录打开终端。示例 PDF 已放在 `examples/pdfs/`，来源及版本见 [示例清单](examples/manifest.json)。

## 3. Linux 快速开始

Ubuntu 24.04 首先安装 Python、虚拟环境组件及系统库：

```bash
sudo apt update
sudo apt install -y python3.12 python3.12-venv libgomp1 git
```

没有 sudo 权限时，使用已经带有 venv / pip 的 Python 3.12 环境，并通过 `--python` 指定解释器。

在项目根目录运行：

```bash
# 1. 创建 .venv，安装固定依赖及本地 pdf2md 包
bash scripts/setup.sh --python python3.12

# 2. 下载并检查完整 Basic 模型
bash scripts/models.sh --model-source modelscope

# 3. 转换两份示例 PDF
bash scripts/run.sh --input examples/pdfs --model-source modelscope
```

先快速验证环境、不下载推理模型：

```bash
bash scripts/run.sh --input examples/pdfs --tier flash
```

脚本通过 `bash` 调用，无需先执行 `chmod`。默认环境目录为 `.venv/`。如果在 WSL 与 Windows 共用源码目录，Linux 可先设置 `export PDF2MD_VENV=.venv-linux`，避免与 Windows 环境冲突。

## 4. Windows 快速开始

安装 [64 位 Python 3.12](https://www.python.org/downloads/)；可用 `py -3.12 --version` 检查版本。在项目根目录打开 PowerShell：

```powershell
# 1. 创建 .venv，安装固定依赖及本地 pdf2md 包
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup.ps1

# 2. 下载并检查完整 Basic 模型
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\models.ps1 -ModelSource modelscope

# 3. 转换两份示例 PDF
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run.ps1 -InputPath .\examples\pdfs -ModelSource modelscope
```

先快速验证环境、不下载推理模型：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run.ps1 -InputPath .\examples\pdfs -Tier flash
```

自动发现失败时指定 Python：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup.ps1 -PythonPath 'C:\Python312\python.exe'
```

`ExecutionPolicy Bypass` 只对该进程生效，不修改系统全局执行策略。无需激活虚拟环境；运行和模型脚本会自动检查环境。

## 5. 模型下载地址与配置

Basic 使用 **MinerU-4_models_onnx**，默认保存到：

```text
.mineru/models/MinerU-4_models_onnx/
```

| 来源 | 官方下载地址 | 脚本参数 |
|---|---|---|
| ModelScope | [OpenDataLab/MinerU-4_models_onnx](https://modelscope.cn/models/OpenDataLab/MinerU-4_models_onnx) | `modelscope` |
| Hugging Face | [opendatalab/MinerU-4_models_onnx](https://huggingface.co/opendatalab/MinerU-4_models_onnx) | `huggingface` |

脚本不要求登录或填写 Token。只下载当前 CPU / ONNX 路线需要的文件，不需要 Torch 或 VLM 权重。完整文件结构、逐文件直链、SHA-256 与手动下载方法见 [模型配置说明](docs/MODELS.md) 和 [模型清单](docs/model-files.json)。

切换下载源：

```bash
bash scripts/models.sh --model-source huggingface
```

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\models.ps1 -ModelSource huggingface
```

仅检查现有模型，并与项目记录的 SHA-256 快照比较：

```bash
bash scripts/models.sh --verify-only --check-hashes --offline
```

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\models.ps1 -VerifyOnly -CheckHashes -Offline
```

自定义缓存位置时，下载和运行需传入同一个目录，例如：

```bash
bash scripts/models.sh --mineru-home /data/pdf2md-cache
bash scripts/run.sh --input /data/papers --mineru-home /data/pdf2md-cache
```

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\models.ps1 -MineruHome 'D:\pdf2md-cache'
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run.ps1 -InputPath 'D:\papers' -MineruHome 'D:\pdf2md-cache'
```

该目录包含 `models/MinerU-4_models_onnx/`，不要把参数直接指向某个 `.onnx` 文件。脚本不会修改你的全局 MinerU 配置。

## 6. 转换自己的 PDF

Linux：

```bash
# 单篇
bash scripts/run.sh --input /data/papers/paper.pdf

# 递归处理子目录，并指定输出位置
bash scripts/run.sh --input /data/papers --recursive --output-dir /data/markdown

# 已准备好环境与模型，按离线方式运行
bash scripts/run.sh --input /data/papers --recursive --offline
```

Windows（将示例路径替换为真实 PDF 路径）：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run.ps1 -InputPath 'D:\papers\paper.pdf'
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run.ps1 -InputPath 'D:\papers' -Recursive -OutputPath 'D:\markdown'
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run.ps1 -InputPath 'D:\papers' -Recursive -Offline
```

常用参数：

| 用途 | Linux | Windows | 默认 |
|---|---|---|---|
| 输入 PDF 或目录 | `--input` | `-InputPath` | 必填 |
| 档位 | `--tier basic/flash` | `-Tier basic/flash` | `basic` |
| 递归子目录 | `--recursive` | `-Recursive` | 关闭 |
| 输出目录 | `--output-dir` | `-OutputPath` | 项目 `output/` |
| 模型源 | `--model-source` | `-ModelSource` | 运行时 `auto` |
| 缓存根目录 | `--mineru-home` | `-MineruHome` | 项目 `.mineru/` |
| 离线模式 | `--offline` | `-Offline` | 关闭 |
| 不保存整页图 | `--no-page-images` | `-NoPageImages` | 整页图默认保存 |
| 强制重跑 | `--force` | `-Force` | 缓存有效时跳过 |
| 保留原始 ZIP | `--keep-archive` | `-KeepArchive` | 关闭 |
| 每篇解析超时 | `--timeout 600` | `-TimeoutSeconds 600` | 不限制 |
| 算法文字来源 | `--algorithm-text native/ocr` | `-AlgorithmText native/ocr` | `native` |
| 底层 OCR 模式 | `--ocr-mode auto/txt/ocr` | `-OcrMode auto/txt/ocr` | `auto` |

关闭整页图片仍会保留算法、独立公式和可疑项的局部原图。强制 OCR 不保证更准确；若要原样比较算法 OCR，同时指定算法文字来源为 `ocr`。

### Python / console 入口

安装后也可直接运行包：

```bash
.venv/bin/python -m pdf2md --input examples/pdfs --tier basic
.venv/bin/pdf2md --help
```

```powershell
.\.venv\Scripts\python.exe -m pdf2md --input .\examples\pdfs --tier basic
.\.venv\Scripts\pdf2md.exe --help
```

直接运行包时，默认模型缓存和输出目录相对于**当前工作目录**；模型缓存可通过 `MINERU_HOME` 指定。Shell 脚本则使用项目目录作为默认位置。不要直接执行 `src/pdf2md/pipeline.py`。

## 7. 输出内容

每篇输出到 `output/<PDF 文件名>/<档位>/`。同名但内容不同的 PDF 会增加哈希后缀。

| 文件 | 内容 |
|---|---|
| `markdown.md` | 最终 Markdown |
| `markdown.raw.md` | 未修改的 MinerU 原稿 |
| `images/` | 解析器提取的图像 |
| `middle_json.json` / `structured_content.json` | 未修改的结构化证据，含页码、区域和内容 |
| `model_output.json` | 底层提供时保留的原始模型输出 |
| `review.md` / `review.json` | 算法对照、公式清单、可疑项及来源选择 |
| `regions/` | 算法、独立公式和可疑项的 216 dpi 原图 |
| `page_index.md` / `pages/` | 默认保存的 108 dpi 逐页原图 |
| `quality.json` | 结构检查与人工复核提示 |
| `run.json` | 来源/配置/版本、耗时和产物哈希 |

建议先看 `markdown.md`，再查看 `review.md` 和 `page_index.md`。分享 Markdown 时需保留其同目录图片，单独复制 Markdown 会丢失原图。

批次日志在 `_logs/`，不可覆盖的运行清单在 `_runs/`，重跑前的旧结果在 `_history/`。`batch_summary.json` 是最新批次汇总。某篇损坏、失败或超时后仍继续处理其余文件。来源、配置及产物哈希匹配时跳过重跑。

退出码：`0` 转换与结构检查通过/命中缓存；`1` 至少一篇运行失败；`2` 至少一篇结构检查失败。`needs_review` 表示需要核验内容，不会单独使退出码变成 2。

## 8. 完全离线准备

在**相同操作系统、架构和 Python 3.12** 的联网机器上先运行安装与模型下载，再准备依赖 wheel：

```bash
.venv/bin/python -m pip wheel -r requirements/locked.txt --wheel-dir wheelhouse
```

Windows 对应：

```powershell
.\.venv\Scripts\python.exe -m pip wheel -r .\requirements\locked.txt --wheel-dir .\wheelhouse
```

将项目源码、`wheelhouse/` 和完整 `.mineru/models/MinerU-4_models_onnx/` 复制到离线机器。系统需预先安装 Python 3.12、venv 和相应系统库；**不要复制联网机器的 `.venv`**。

Linux：

```bash
bash scripts/setup.sh --offline --wheelhouse ./wheelhouse
bash scripts/models.sh --verify-only --check-hashes --offline
bash scripts/run.sh --input /data/papers --recursive --offline
```

Windows：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup.ps1 -Offline -Wheelhouse .\wheelhouse
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\models.ps1 -VerifyOnly -CheckHashes -Offline
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run.ps1 -InputPath 'D:\papers' -Recursive -Offline
```

离线 Basic 会先检查模型是否齐全，缺失时直接报错，不在处理中尝试补下载。Windows 和 Linux 的 wheelhouse 不能互换。

## 9. 项目结构与开发

```text
Pdf2MD/
├── pyproject.toml           # Python 包与 pdf2md 命令入口
├── src/pdf2md/
│   ├── pipeline.py          # 批处理、缓存、发布、质量检查
│   ├── review.py            # 原生算法转写、公式复核与局部原图
│   └── __main__.py          # python -m pdf2md
├── scripts/                 # Windows .ps1 / Linux .sh 入口
├── requirements/locked.txt  # 固定依赖，Windows 专用包带平台条件
├── docs/                    # 模型配置、模型清单、质量说明
├── examples/                # 公开 PDF 与版本/哈希清单
└── tests/                   # 单元测试与扫描件测试样例
```

安装脚本以 editable 模式安装当前包，修改 `src/` 后无需重复安装。依赖声明在 `pyproject.toml`，脚本使用锁文件保证已测试的版本；Windows 专用 DirectML 和文件时间依赖不会在 Linux 安装。

运行测试：

```bash
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m pip check
```

Windows 将解释器换成 `.\.venv\Scripts\python.exe`。单元测试不下载模型；实际扫描件测试见 [tests/fixtures](tests/fixtures/README.md)。

`.venv*`、`.mineru/`、`output/`、`wheelhouse/`、构建缓存和运行日志均不提交 Git。仓库不包含模型权重、个人运行结果或开发实验留档。

## 10. 常见问题

- **Python 版本不符**：提供 64 位 Python 3.12，通过 `--python` / `-PythonPath` 指定；不要用 3.13 创建环境。
- **Ubuntu 提示缺少 ensurepip**：安装 `python3.12-venv`，或使用已经提供 venv / pip 的 Python 环境。
- **Linux 提示缺少 libgomp.so.1**：安装 `libgomp1`。
- **依赖下载失败**：重新执行安装脚本，或用 `--index-url` / `-IndexUrl` 指定可信包源；不建议关闭 TLS 校验。
- **模型下载失败**：切换 `modelscope` / `huggingface`，完成后执行模型校验；也可按 [手动说明](docs/MODELS.md) 准备文件。
- **哈希与模型清单不同**：上游分支可能已更新，也可能文件不完整；先核对来源，不要直接忽略警告。清单记录的是本项目已验证的快照。
- **提示找不到 pdf2md**：重新运行安装脚本，确认使用项目虚拟环境；不要直接执行包内 `.py` 文件。
- **转换结果为空或不完整**：查看 `_logs/`、`quality.json`；扫描件优先用 Basic，并检查 PDF 是否加密、损坏或本身缺页。
- **公式/算法不准确**：查看原图与 `review.md`；原生文本也会展平上下标和缩进，渲染成功或词频重叠不能证明数学正确。

论文与第三方解析器/模型的来源及许可见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。
