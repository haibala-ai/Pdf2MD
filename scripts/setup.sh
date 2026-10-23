#!/usr/bin/env bash
set -euo pipefail
project_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
python_path="${PDF2MD_PYTHON:-}"
index_url="${PIP_INDEX_URL:-https://pypi.org/simple}"
offline=false
wheelhouse=""
while (($#)); do
    case "$1" in
        --python) python_path="${2:?--python requires a path}"; shift 2 ;;
        --index-url) index_url="${2:?--index-url requires a URL}"; shift 2 ;;
        --offline) offline=true; shift ;;
        --wheelhouse) wheelhouse="${2:?--wheelhouse requires a directory}"; shift 2 ;;
        -h|--help)
            printf '%s\n' 'Usage: bash scripts/setup.sh [--python python3.12] [--index-url URL] [--offline --wheelhouse DIR]'
            exit 0 ;;
        *) printf 'Unknown setup option: %s\n' "$1" >&2; exit 2 ;;
    esac
done
export PYTHONUTF8=1 PYTHONIOENCODING=utf-8
venv_root="${PDF2MD_VENV:-$project_root/.venv}"
if [[ "$venv_root" != /* ]]; then venv_root="$project_root/$venv_root"; fi
venv_python="$venv_root/bin/python"
if [[ ! -x "$venv_python" ]]; then
    if [[ -e "$venv_root/pyvenv.cfg" ]]; then
        printf '%s\n' 'Existing environment is not a Linux venv. Use a separate checkout or set PDF2MD_VENV=.venv-linux.' >&2
        exit 1
    fi
    if [[ -z "$python_path" ]]; then
        if command -v python3.12 >/dev/null 2>&1; then python_path=python3.12
        elif command -v python3 >/dev/null 2>&1; then python_path=python3
        else printf '%s\n' 'Install 64-bit Python 3.12 and python3.12-venv first.' >&2; exit 1
        fi
    fi
    if ! "$python_path" -c 'import struct,sys; sys.exit(0 if sys.version_info[:2]==(3,12) and struct.calcsize("P")==8 else 1)'; then
        printf '%s\n' '64-bit Python 3.12 is required. Pass --python /path/to/python3.12.' >&2
        exit 1
    fi
    if ! "$python_path" -m venv "$venv_root"; then
        printf '%s\n' 'venv creation failed. On Ubuntu 24.04 install python3.12-venv; see README.md.' >&2
        exit 1
    fi
fi
if ! "$venv_python" -c 'import struct,sys; sys.exit(0 if sys.version_info[:2]==(3,12) and struct.calcsize("P")==8 else 1)'; then
    printf '%s\n' 'Existing venv is not 64-bit Python 3.12. Use a fresh environment.' >&2
    exit 1
fi
if ! "$venv_python" -c 'import importlib.util as u,importlib.metadata as m,sys; ok=all(u.find_spec(n) is not None for n in ["mineru","markdown_it","pypdf","pypdfium2"]); sys.exit(0 if ok and m.version("mineru")=="4.0.12" else 1)'; then
    pip_args=(-m pip install --disable-pip-version-check -r "$project_root/requirements/locked.txt")
    if "$offline"; then
        if [[ -z "$wheelhouse" || ! -d "$wheelhouse" ]]; then
            printf '%s\n' 'Offline install requires --wheelhouse with Linux/Python 3.12 wheels.' >&2
            exit 1
        fi
        pip_args+=(--no-index --find-links "$wheelhouse")
    else pip_args+=(--index-url "$index_url")
    fi
    "$venv_python" "${pip_args[@]}"
fi
"$venv_python" -c 'import mineru,pypdf,pypdfium2,markdown_it; print("PDF dependencies ready")'
if ! "$venv_python" -c 'import importlib.util as u,sys; from pathlib import Path; s=u.find_spec("pdf2md"); sys.exit(0 if s and s.origin and Path(s.origin).resolve()==Path(sys.argv[1]).resolve() else 1)' "$project_root/src/pdf2md/__init__.py"; then
    "$venv_python" -m pip install --disable-pip-version-check --no-deps --no-build-isolation -e "$project_root"
fi
printf '%s\n' 'Ready. Basic uses local CPU/ONNX models. Flash needs no inference models.'
