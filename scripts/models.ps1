param(
    [ValidateSet('auto','huggingface','modelscope')][string]$ModelSource = 'modelscope',
    [string]$MineruHome = '',
    [string]$PythonPath = '',
    [string]$IndexUrl = 'https://pypi.org/simple',
    [switch]$VerifyOnly,
    [switch]$CheckHashes,
    [switch]$Offline,
    [string]$Wheelhouse = ''
)
$ErrorActionPreference = 'Stop'
$taskProjectRoot = Split-Path -Parent $PSScriptRoot
if ($Offline -and !$VerifyOnly) { throw 'Offline mode requires -VerifyOnly; downloading needs a connection.' }
$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'
$env:MINERU_HOME = if ($MineruHome) { [IO.Path]::GetFullPath($MineruHome) } else { Join-Path $taskProjectRoot '.mineru' }
$env:MINERU_MODEL_SOURCE = $ModelSource
$env:MINERU_MODEL_SMALL_BACKEND = 'onnx'
$env:MINERU_DEVICE_MODE = 'cpu'
& (Join-Path $PSScriptRoot 'setup.ps1') -PythonPath $PythonPath -IndexUrl $IndexUrl -Offline:$Offline -Wheelhouse $Wheelhouse
$taskCli = Join-Path $taskProjectRoot '.venv\Scripts\mineru-kit.exe'
if (!$VerifyOnly) {
    & $taskCli models download --tier basic --small-backend onnx --source $ModelSource
    if ($LASTEXITCODE -ne 0) { throw 'Model download failed. Retry or choose another -ModelSource; see docs/MODELS.md.' }
}
& $taskCli models verify --tier basic --small-backend onnx
if ($LASTEXITCODE -ne 0) { throw 'Required Basic model files are missing. See docs/MODELS.md.' }
if ($CheckHashes) {
    $taskManifest = Get-Content -LiteralPath (Join-Path $taskProjectRoot 'docs\model-files.json') -Raw -Encoding UTF8 | ConvertFrom-Json
    $taskModelRoot = Join-Path $env:MINERU_HOME $taskManifest.relative_model_directory
    foreach ($taskFile in $taskManifest.files) {
        $taskPath = Join-Path $taskModelRoot $taskFile.path
        $taskDigest = (Get-FileHash -LiteralPath $taskPath -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($taskDigest -ne $taskFile.sha256) {
            throw ('Model differs from the documented snapshot: ' + $taskFile.path + '. See docs/MODELS.md before replacing files.')
        }
    }
    Write-Host ('SHA-256 checks passed for all ' + $taskManifest.files.Count + ' model/config files.')
}
Write-Host ('Basic CPU/ONNX models ready: ' + (Join-Path $env:MINERU_HOME 'models\MinerU-4_models_onnx'))
