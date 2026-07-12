param(
    [string]$Name = "aircraft-design",
    [switch]$SkipInstall,
    [switch]$OneFile
)

$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $repoRoot

if (-not (Test-Path "pyproject.toml")) {
    throw "pyproject.toml not found. Run this script from the repository scripts folder."
}

Write-Host "Repository: $repoRoot"
Write-Host "Build name:  $Name"

if (-not $SkipInstall) {
    Write-Host "Installing project and PyInstaller..."
    python -m pip install --upgrade pip
    python -m pip install -e .
    python -m pip install --upgrade pyinstaller
}

$modeArg = if ($OneFile) { "--onefile" } else { "--onedir" }

$pyinstallerArgs = @(
    "--noconfirm",
    "--clean",
    $modeArg,
    "--name", $Name,
    "--paths", "src",
    "--collect-all", "PySide6",
    "--collect-all", "matplotlib",
    "--collect-submodules", "aircraft_design",
    "--exclude-module", "pytest",
    "--exclude-module", "tests",
    "--console",
    "src\aircraft_design\cli.py"
)

Write-Host "Running PyInstaller..."
python -m PyInstaller @pyinstallerArgs

if ($OneFile) {
    $exePath = Join-Path $repoRoot "dist\$Name.exe"
} else {
    $exePath = Join-Path $repoRoot "dist\$Name\$Name.exe"
}

if (-not (Test-Path $exePath)) {
    throw "EXE was not created at expected path: $exePath"
}

Write-Host ""
Write-Host "Build completed successfully."
Write-Host "EXE: $exePath"
Write-Host ""
Write-Host "Run smoke checks:"
Write-Host "powershell -ExecutionPolicy Bypass -File scripts\smoke_windows_exe.ps1"
