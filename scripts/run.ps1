param(
    [Parameter(Mandatory=$true)][string]$InputPath,
    [ValidateSet('flash','basic')]
    [string]$Tier = 'basic',
    [ValidateSet('auto','huggingface','modelscope')][string]$ModelSource = 'auto',
    [string]$OutputPath = '',
    [string]$PythonPath = '',
    [string]$IndexUrl = 'https://pypi.org/simple',
    [string]$MineruHome = '',
    [switch]$Offline,
    [string]$Wheelhouse = '',
    [switch]$Recursive,
    [switch]$Force,
    [switch]$KeepArchive,
    [switch]$PageImages,
    [switch]$NoPageImages,
    [ValidateSet('native','ocr')][string]$AlgorithmText = 'native',
    [ValidateSet('auto','txt','ocr')][string]$OcrMode = 'auto',
    [int]$TimeoutSeconds = 0
)
$ErrorActionPreference = 'Stop'
$taskProjectRoot = Split-Path -Parent $PSScriptRoot
if ($PageImages -and $NoPageImages) { throw 'Use either -PageImages or -NoPageImages.' }
if ($TimeoutSeconds -lt 0) { throw '-TimeoutSeconds cannot be negative.' }
$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'
$env:MINERU_HOME = if ($MineruHome) { [IO.Path]::GetFullPath($MineruHome) } else { Join-Path $taskProjectRoot '.mineru' }
$env:MINERU_MODEL_SOURCE = $ModelSource
$env:MINERU_MODEL_SMALL_BACKEND = 'onnx'
$env:MINERU_DEVICE_MODE = 'cpu'
$taskPython = Join-Path $taskProjectRoot '.venv\Scripts\python.exe'
& (Join-Path $PSScriptRoot 'setup.ps1') -PythonPath $PythonPath -IndexUrl $IndexUrl -Offline:$Offline -Wheelhouse $Wheelhouse
if ($Offline -and $Tier -eq 'basic') {
    & (Join-Path $taskProjectRoot '.venv\Scripts\mineru-kit.exe') models verify --tier basic --small-backend onnx
    if ($LASTEXITCODE -ne 0) { throw 'Offline Basic models are incomplete. Run models.ps1 online first, or copy the complete model directory.' }
}
$taskArguments = @('-m', 'pdf2md', '--tier', $Tier)
$taskArguments += @('--algorithm-text', $AlgorithmText, '--ocr-mode', $OcrMode)
if ($InputPath) { $taskArguments += @('--input', $InputPath) }
$taskOutput = if ($OutputPath) { $OutputPath } else { Join-Path $taskProjectRoot 'output' }
$taskArguments += @('--output-dir', $taskOutput)
if ($Recursive) { $taskArguments += '--recursive' }
if ($Force) { $taskArguments += '--force' }
if ($KeepArchive) { $taskArguments += '--keep-archive' }
if ($PageImages) { $taskArguments += '--page-images' }
if ($NoPageImages) { $taskArguments += '--no-page-images' }
if ($TimeoutSeconds -gt 0) { $taskArguments += @('--timeout', "$TimeoutSeconds") }
& $taskPython @taskArguments
exit $LASTEXITCODE
