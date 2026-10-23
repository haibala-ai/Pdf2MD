param(
    [string]$PythonPath = '',
    [string]$IndexUrl = 'https://pypi.org/simple',
    [switch]$Offline,
    [string]$Wheelhouse = ''
)
$ErrorActionPreference = 'Stop'
$taskProjectRoot = Split-Path -Parent $PSScriptRoot
$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'
$taskPython = Join-Path $taskProjectRoot '.venv\Scripts\python.exe'

if (!(Test-Path -LiteralPath $taskPython)) {
    $taskCandidates = @()
    if ($PythonPath) {
        $taskCandidates += @{Exe=$PythonPath; Args=@()}
    } elseif ($env:PDF2MD_PYTHON) {
        $taskCandidates += @{Exe=$env:PDF2MD_PYTHON; Args=@()}
    } else {
        if (Get-Command py -ErrorAction SilentlyContinue) { $taskCandidates += @{Exe='py'; Args=@('-3.12')} }
        foreach ($taskCommand in @('python3.12','python')) {
            if (Get-Command $taskCommand -ErrorAction SilentlyContinue) {
                $taskCandidates += @{Exe=$taskCommand; Args=@()}
            }
        }
        $taskLocalPython = Join-Path $env:LOCALAPPDATA 'Programs\Python\Python312\python.exe'
        if (Test-Path -LiteralPath $taskLocalPython) { $taskCandidates += @{Exe=$taskLocalPython; Args=@()} }
        foreach ($taskKey in @('HKCU:\SOFTWARE\Python\PythonCore\3.12\InstallPath','HKLM:\SOFTWARE\Python\PythonCore\3.12\InstallPath')) {
            if (Test-Path $taskKey) {
                $taskRegistryPython = (Get-Item $taskKey).GetValue('ExecutablePath')
                if ($taskRegistryPython) { $taskCandidates += @{Exe=$taskRegistryPython; Args=@()} }
            }
        }
    }
    $taskBasePython = $null
    foreach ($taskCandidate in $taskCandidates) {
        $taskCandidateArgs = $taskCandidate.Args
        $taskVersion = & $taskCandidate.Exe @taskCandidateArgs -c "import sys,struct; print(str(sys.version_info.major)+'.'+str(sys.version_info.minor)+'/'+str(struct.calcsize('P')*8))"
        if ($LASTEXITCODE -eq 0 -and "$taskVersion".Trim() -eq '3.12/64') {
            $taskBasePython=$taskCandidate.Exe; $taskBaseArgs=$taskCandidateArgs; break
        }
    }
    if (!$taskBasePython) { throw 'No 64-bit Python 3.12 found. Pass -PythonPath or set PDF2MD_PYTHON; a Python 3.13 installation is not used.' }
    & $taskBasePython @taskBaseArgs -m venv (Join-Path $taskProjectRoot '.venv')
    if ($LASTEXITCODE -ne 0) { throw 'Failed to create the local virtual environment.' }
}

& $taskPython -c "import sys,struct; sys.exit(0 if sys.version_info[:2]==(3,12) and struct.calcsize('P')==8 else 1)"
if ($LASTEXITCODE -ne 0) { throw 'The existing .venv is not 64-bit Python 3.12. Use a fresh unpacked folder.' }
& $taskPython -c "import importlib.util as u, importlib.metadata as m, sys; ok=all(u.find_spec(n) is not None for n in ['mineru','markdown_it','pypdf','pypdfium2']); sys.exit(0 if ok and m.version('mineru')=='4.0.12' else 1)"
if ($LASTEXITCODE -ne 0) {
    $taskPipArguments = @('-m','pip','install','--disable-pip-version-check','-r',(Join-Path $taskProjectRoot 'requirements\locked.txt'))
    if ($Offline) {
        if (!$Wheelhouse -or !(Test-Path -LiteralPath $Wheelhouse -PathType Container)) {
            throw 'Offline installation requires -Wheelhouse pointing to prepared Windows/Python 3.12 wheels. See README.md.'
        }
        $taskPipArguments += @('--no-index','--find-links',([IO.Path]::GetFullPath($Wheelhouse)))
    } else {
        $taskPipArguments += @('--index-url',$IndexUrl)
    }
    & $taskPython @taskPipArguments
    if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed. Check the connection and retry setup.ps1; see README.md.' }
}
& $taskPython -c "import mineru, pypdf, pypdfium2, markdown_it; print('PDF dependencies ready')"
if ($LASTEXITCODE -ne 0) { throw 'Dependency import check failed.' }
& $taskPython -c "import importlib.util as u,sys; from pathlib import Path; s=u.find_spec('pdf2md'); sys.exit(0 if s and s.origin and Path(s.origin).resolve()==Path(sys.argv[1]).resolve() else 1)" (Join-Path $taskProjectRoot 'src\pdf2md\__init__.py')
if ($LASTEXITCODE -ne 0) {
    & $taskPython -m pip install --disable-pip-version-check --no-deps --no-build-isolation -e $taskProjectRoot
    if ($LASTEXITCODE -ne 0) { throw 'Failed to install the local pdf2md package.' }
}
Write-Host 'Ready. Basic models will download to .mineru on the first Basic conversion. Flash needs no inference models.'
