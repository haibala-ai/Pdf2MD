#!/usr/bin/env bash
set -euo pipefail
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
project_root="$(cd -- "$script_dir/.." && pwd)"
model_source=auto
mineru_home="$project_root/.mineru"
tier=basic
offline=false
output_set=false
setup_args=()
parse_args=()
while (($#)); do
    case "$1" in
        --model-source) model_source="${2:?--model-source requires a value}"; shift 2 ;;
        --mineru-home) mineru_home="${2:?--mineru-home requires a directory}"; shift 2 ;;
        --offline) offline=true; setup_args+=(--offline); shift ;;
        --python|--index-url|--wheelhouse) setup_args+=("$1" "${2:?Missing option value}"); shift 2 ;;
        --tier) tier="${2:?--tier requires a value}"; parse_args+=("$1" "$2"); shift 2 ;;
        --tier=*) tier="${1#*=}"; parse_args+=("$1"); shift ;;
        --output-dir|--output-dir=*) output_set=true; parse_args+=("$1"); shift ;;
        -h|--help)
            cat <<'HELP'
Usage: bash scripts/run.sh --input PDF_OR_DIR [options]
Core: --tier basic|flash --recursive --output-dir DIR --force
      --no-page-images --keep-archive --timeout SECONDS
      --algorithm-text native|ocr --ocr-mode auto|txt|ocr
Setup: --python PATH --index-url URL --offline --wheelhouse DIR
Models: --model-source auto|modelscope|huggingface --mineru-home DIR
HELP
            exit 0 ;;
        *) parse_args+=("$1"); shift ;;
    esac
done
if ((${#parse_args[@]}==0)); then printf '%s\n' 'Pass --input PDF_OR_DIR; use --help for options.' >&2; exit 2; fi
case "$model_source" in auto|modelscope|huggingface) ;; *) printf '%s\n' 'Invalid --model-source.' >&2; exit 2 ;; esac
case "$tier" in basic|flash) ;; *) printf '%s\n' 'Invalid --tier.' >&2; exit 2 ;; esac
bash "$script_dir/setup.sh" "${setup_args[@]}"
venv_root="${PDF2MD_VENV:-$project_root/.venv}"
if [[ "$venv_root" != /* ]]; then venv_root="$project_root/$venv_root"; fi
venv_python="$venv_root/bin/python"
export MINERU_HOME
MINERU_HOME="$("$venv_python" -c 'from pathlib import Path; import sys; print(Path(sys.argv[1]).resolve())' "$mineru_home")"
export MINERU_MODEL_SOURCE="$model_source" MINERU_MODEL_SMALL_BACKEND=onnx MINERU_DEVICE_MODE=cpu
export PYTHONUTF8=1 PYTHONIOENCODING=utf-8
if "$offline" && [[ "$tier" == basic ]]; then
    if ! "$venv_root/bin/mineru-kit" models verify --tier basic --small-backend onnx; then
        printf '%s\n' 'Offline Basic models are incomplete. Run scripts/models.sh online first.' >&2
        exit 1
    fi
fi
if ! "$output_set"; then parse_args+=(--output-dir "$project_root/output"); fi
exec "$venv_python" -m pdf2md "${parse_args[@]}"
