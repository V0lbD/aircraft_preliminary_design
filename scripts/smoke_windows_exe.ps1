param(
    [string]$ExePath = "dist\aircraft-design\aircraft-design.exe",
    [string]$InputPath = "examples\inputs\AN14.json",
    [switch]$LaunchGui
)

$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $repoRoot

if (-not (Test-Path $ExePath)) {
    throw "EXE not found: $ExePath"
}

$outputDir = "outputs\exe_smoke"
New-Item -ItemType Directory -Force -Path $outputDir | Out-Null

function Invoke-CheckedCommand {
    param(
        [string]$Title,
        [scriptblock]$Command
    )

    Write-Host ""
    Write-Host "== $Title =="
    & $Command
    if ($LASTEXITCODE -ne 0) {
        throw "$Title failed with exit code $LASTEXITCODE"
    }
}

Invoke-CheckedCommand "help" { & $ExePath --help }
Invoke-CheckedCommand "schema" { & $ExePath --mode schema --output "$outputDir\schema.json" }
Invoke-CheckedCommand "template" { & $ExePath --mode template --output "$outputDir\template.json" }

if (Test-Path $InputPath) {
    Invoke-CheckedCommand "validate" { & $ExePath --mode validate --input $InputPath }
    Invoke-CheckedCommand "batch txt" { & $ExePath --mode batch --input $InputPath --output "$outputDir\result.txt" --trace-md "$outputDir\trace.md" }
    Invoke-CheckedCommand "batch json" { & $ExePath --mode batch --input $InputPath --output "$outputDir\result.json" --output-format json --trace-json "$outputDir\trace.json" }
} else {
    Write-Host ""
    Write-Host "Input file not found, validate/batch checks skipped: $InputPath"
}

if ($LaunchGui) {
    Write-Host ""
    Write-Host "Launching GUI. Close the window manually when it opens."
    Start-Process -FilePath $ExePath -ArgumentList "--mode", "gui" -Wait
}

Write-Host ""
Write-Host "Smoke checks completed successfully."
