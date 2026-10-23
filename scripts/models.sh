#!/usr/bin/env bash
set -euo pipefail
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
project_root="$(cd -- "$script_dir/.." && pwd)"
model_source=modelscope
mineru_home="$project_root/.mineru"
verify_only=false
check_hashes=false
offline=false
setup_args=()
while (($#)); do
    case "$1" in
        --model-source) model_source="${2:?--model-source requires a value}"; shift 2 ;;
        --mineru-home) mineru_home="${2:?--mineru-home requires a directory}"; shift 2 ;;
        --verify-only) verify_only=true; shift ;;
        --check-hashes) check_hashes=true; shift ;;
        --offline) offline=true; setup_args+=(--offline); shift ;;
        --python|--index-url|--wheelhouse) setup_args+=("$1" "${2:?Missing option value}"); shift 2 ;;
        -h|--help)
            printf '%s\n' 'Usage: bash scripts/models.sh [--model-source modelscope|huggingface|auto] [--verify-only] [--check-hashes] [--mineru-home DIR] [--offline --wheelhouse DIR]'
            exit 0 ;;
        *) printf 'Unknown model option: %s\n' "$1" >&2; exit 2 ;;
    esac
done
case "$model_source" in auto|modelscope|huggingface) ;; *) printf '%s\n' 'Invalid --model-source.' >&2; exit 2 ;; esac
if "$offline" && ! "$verify_only"; then printf '%s\n' 'Offline mode requires --verify-only.' >&2; exit 2; fi
bash "$script_dir/setup.sh" "${setup_args[@]}"
venv_root="${PDF2MD_VENV:-$project_root/.venv}"
if [[ "$venv_root" != /* ]]; then venv_root="$project_root/$venv_root"; fi
venv_python="$venv_root/bin/python"
export MINERU_HOME
MINERU_HOME="$("$venv_python" -c 'from pathlib import Path; import sys; print(Path(sys.argv[1]).resolve())' "$mineru_home")"
export MINERU_MODEL_SOURCE="$model_source" MINERU_MODEL_SMALL_BACKEND=onnx MINERU_DEVICE_MODE=cpu
export PYTHONUTF8=1 PYTHONIOENCODING=utf-8
if ! "$verify_only"; then
    "$venv_root/bin/mineru-kit" models download --tier basic --small-backend onnx --source "$model_source"
fi
"$venv_root/bin/mineru-kit" models verify --tier basic --small-backend onnx
if "$check_hashes"; then
    "$venv_python" - "$project_root/docs/model-files.json" "$MINERU_HOME" <<'PY'
import hashlib,json,sys
from pathlib import Path
manifest=json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
root=Path(sys.argv[2])/manifest['relative_model_directory']
for item in manifest['files']:
    with (root/item['path']).open('rb') as stream:
        actual=hashlib.file_digest(stream,'sha256').hexdigest()
    if actual!=item['sha256']:
        raise SystemExit('Model differs from the documented snapshot: '+item['path']+'. See docs/MODELS.md.')
print('SHA-256 checks passed for all',len(manifest['files']),'model/config files.')
PY
fi
printf 'Basic CPU/ONNX models ready: %s/models/MinerU-4_models_onnx\n' "$MINERU_HOME"
