# 模型下载与离线目录

本项目使用 MinerU 4.0.12 的 CPU / ONNX 路线。默认模型根目录为项目 `.mineru/`，完整文件位于 `models/MinerU-4_models_onnx/`。

## 自动下载

从项目根目录执行：

```bash
bash scripts/models.sh --model-source modelscope
bash scripts/models.sh --verify-only --check-hashes --offline
```

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\models.ps1 -ModelSource modelscope
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\models.ps1 -VerifyOnly -CheckHashes -Offline
```

`--verify-only` / `-VerifyOnly` 检查文件是否齐全；加上 `--check-hashes` / `-CheckHashes` 才会逐文件校验 SHA-256。首次下载完成后建议做一次哈希校验。

## 官方地址

- [Hugging Face 仓库](https://huggingface.co/opendatalab/MinerU-4_models_onnx)。
- [ModelScope 仓库](https://modelscope.cn/models/OpenDataLab/MinerU-4_models_onnx)。

入口使用公开下载地址，不要求 API Key。以下直链来自当前解析器声明的模型仓库；不需要额外下载 Torch 或 VLM 权重。

## 必需文件

清单快照日期：2026-10-23。共 13 个文件，858,204,914 字节，约 858 MB / 818 MiB。

| 相对于模型仓库的路径 | 大小 | 下载 |
|---|---:|---|
| `Layout/PP-DocLayoutV2/inference.onnx` | 204.05 MiB | [HF](https://huggingface.co/opendatalab/MinerU-4_models_onnx/resolve/main/Layout/PP-DocLayoutV2/inference.onnx) · [ModelScope](https://modelscope.cn/api/v1/models/OpenDataLab/MinerU-4_models_onnx/repo?Revision=master&FilePath=Layout%2FPP-DocLayoutV2%2Finference.onnx) |
| `Layout/PP-DocLayoutV2/inference.yml` | 0.00 MiB | [HF](https://huggingface.co/opendatalab/MinerU-4_models_onnx/resolve/main/Layout/PP-DocLayoutV2/inference.yml) · [ModelScope](https://modelscope.cn/api/v1/models/OpenDataLab/MinerU-4_models_onnx/repo?Revision=master&FilePath=Layout%2FPP-DocLayoutV2%2Finference.yml) |
| `MFR/pp_formulanet_plus_m/PP-FormulaNet_plus-M.onnx` | 563.87 MiB | [HF](https://huggingface.co/opendatalab/MinerU-4_models_onnx/resolve/main/MFR/pp_formulanet_plus_m/PP-FormulaNet_plus-M.onnx) · [ModelScope](https://modelscope.cn/api/v1/models/OpenDataLab/MinerU-4_models_onnx/repo?Revision=master&FilePath=MFR%2Fpp_formulanet_plus_m%2FPP-FormulaNet_plus-M.onnx) |
| `MFR/pp_formulanet_plus_m/PP-FormulaNet_plus-M_inference.yml` | 2.14 MiB | [HF](https://huggingface.co/opendatalab/MinerU-4_models_onnx/resolve/main/MFR/pp_formulanet_plus_m/PP-FormulaNet_plus-M_inference.yml) · [ModelScope](https://modelscope.cn/api/v1/models/OpenDataLab/MinerU-4_models_onnx/repo?Revision=master&FilePath=MFR%2Fpp_formulanet_plus_m%2FPP-FormulaNet_plus-M_inference.yml) |
| `OCR/paddleocr/ch_PP-OCRv6_small_rec_infer.onnx` | 20.18 MiB | [HF](https://huggingface.co/opendatalab/MinerU-4_models_onnx/resolve/main/OCR/paddleocr/ch_PP-OCRv6_small_rec_infer.onnx) · [ModelScope](https://modelscope.cn/api/v1/models/OpenDataLab/MinerU-4_models_onnx/repo?Revision=master&FilePath=OCR%2Fpaddleocr%2Fch_PP-OCRv6_small_rec_infer.onnx) |
| `OCR/paddleocr/ch_PP-OCRv6_small_rec_inference.yml` | 0.14 MiB | [HF](https://huggingface.co/opendatalab/MinerU-4_models_onnx/resolve/main/OCR/paddleocr/ch_PP-OCRv6_small_rec_inference.yml) · [ModelScope](https://modelscope.cn/api/v1/models/OpenDataLab/MinerU-4_models_onnx/repo?Revision=master&FilePath=OCR%2Fpaddleocr%2Fch_PP-OCRv6_small_rec_inference.yml) |
| `OCR/paddleocr/ch_PP-OCRv6_tiny_det_infer.onnx` | 1.70 MiB | [HF](https://huggingface.co/opendatalab/MinerU-4_models_onnx/resolve/main/OCR/paddleocr/ch_PP-OCRv6_tiny_det_infer.onnx) · [ModelScope](https://modelscope.cn/api/v1/models/OpenDataLab/MinerU-4_models_onnx/repo?Revision=master&FilePath=OCR%2Fpaddleocr%2Fch_PP-OCRv6_tiny_det_infer.onnx) |
| `OCR/paddleocr/ch_PP-OCRv6_tiny_det_inference.yml` | 0.00 MiB | [HF](https://huggingface.co/opendatalab/MinerU-4_models_onnx/resolve/main/OCR/paddleocr/ch_PP-OCRv6_tiny_det_inference.yml) · [ModelScope](https://modelscope.cn/api/v1/models/OpenDataLab/MinerU-4_models_onnx/repo?Revision=master&FilePath=OCR%2Fpaddleocr%2Fch_PP-OCRv6_tiny_det_inference.yml) |
| `OCR/paddleocr/seal_PP-OCRv4_det_infer.onnx` | 4.55 MiB | [HF](https://huggingface.co/opendatalab/MinerU-4_models_onnx/resolve/main/OCR/paddleocr/seal_PP-OCRv4_det_infer.onnx) · [ModelScope](https://modelscope.cn/api/v1/models/OpenDataLab/MinerU-4_models_onnx/repo?Revision=master&FilePath=OCR%2Fpaddleocr%2Fseal_PP-OCRv4_det_infer.onnx) |
| `OCR/paddleocr/seal_PP-OCRv4_det_inference.yml` | 0.00 MiB | [HF](https://huggingface.co/opendatalab/MinerU-4_models_onnx/resolve/main/OCR/paddleocr/seal_PP-OCRv4_det_inference.yml) · [ModelScope](https://modelscope.cn/api/v1/models/OpenDataLab/MinerU-4_models_onnx/repo?Revision=master&FilePath=OCR%2Fpaddleocr%2Fseal_PP-OCRv4_det_inference.yml) |
| `Table/PP-LCNet_x1_0_table_cls.onnx` | 6.46 MiB | [HF](https://huggingface.co/opendatalab/MinerU-4_models_onnx/resolve/main/Table/PP-LCNet_x1_0_table_cls.onnx) · [ModelScope](https://modelscope.cn/api/v1/models/OpenDataLab/MinerU-4_models_onnx/repo?Revision=master&FilePath=Table%2FPP-LCNet_x1_0_table_cls.onnx) |
| `Table/slanet-plus.onnx` | 7.40 MiB | [HF](https://huggingface.co/opendatalab/MinerU-4_models_onnx/resolve/main/Table/slanet-plus.onnx) · [ModelScope](https://modelscope.cn/api/v1/models/OpenDataLab/MinerU-4_models_onnx/repo?Revision=master&FilePath=Table%2Fslanet-plus.onnx) |
| `Table/unet.onnx` | 7.95 MiB | [HF](https://huggingface.co/opendatalab/MinerU-4_models_onnx/resolve/main/Table/unet.onnx) · [ModelScope](https://modelscope.cn/api/v1/models/OpenDataLab/MinerU-4_models_onnx/repo?Revision=master&FilePath=Table%2Funet.onnx) |

SHA-256 与机器可读直链见 [model-files.json](model-files.json)。模型分支 `main` / `master` 可能随上游更新，哈希检查用于确认是否与已验证快照一致；不要把不同权重无提示地混用。

## 手动下载

保留每个文件的相对路径，将其放入以下结构；不要将所有文件平铺到同一目录：

```text
.mineru/
└── models/
    └── MinerU-4_models_onnx/
        Layout/
            PP-DocLayoutV2/inference.onnx
            PP-DocLayoutV2/inference.yml
        MFR/
            pp_formulanet_plus_m/PP-FormulaNet_plus-M.onnx
            pp_formulanet_plus_m/PP-FormulaNet_plus-M_inference.yml
        OCR/
            paddleocr/ch_PP-OCRv6_small_rec_infer.onnx
            paddleocr/ch_PP-OCRv6_small_rec_inference.yml
            paddleocr/ch_PP-OCRv6_tiny_det_infer.onnx
            paddleocr/ch_PP-OCRv6_tiny_det_inference.yml
            paddleocr/seal_PP-OCRv4_det_infer.onnx
            paddleocr/seal_PP-OCRv4_det_inference.yml
        Table/
            PP-LCNet_x1_0_table_cls.onnx
            slanet-plus.onnx
            unet.onnx
```

手动下载完成后执行模型校验。缺失的配置文件同样会导致检查失败，不能只下载 `.onnx` 权重。完整的模型目录可在 Windows 和 Linux 间复制。

## 自定义缓存位置

`--mineru-home /data/pdf2md-cache` / `-MineruHome D:\pdf2md-cache` 指向缓存根目录；实际文件应位于其下的 `models/MinerU-4_models_onnx/`。模型下载、校验和运行时都传入同一个根目录。

直接使用 Python 包时，可设置 `MINERU_HOME`；Shell 入口会根据参数设置该变量。缓存目录不上传 GitHub。

## 完全离线

先在联网机器准备模型和对应平台的 Python wheelhouse，复制源码和文件后使用 `--offline` / `-Offline` 安装及运行。模型文件可跨平台共用，虚拟环境和 wheelhouse 不可。完整步骤见 [README](../README.md#8-完全离线准备)。
