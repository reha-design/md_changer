$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectRoot

$env:UV_CACHE_DIR = Join-Path $projectRoot ".uv-cache"
$env:UV_NO_MANAGED_PYTHON = "1"
$env:UV_PYTHON_DOWNLOADS = "never"
# Let uv select an installed Python compatible with requires-python, while
# honoring an explicit UV_PYTHON supplied by the caller.

function Invoke-NativeCommand {
    param(
        [Parameter(Mandatory = $true)]
        [string] $Description,
        [Parameter(Mandatory = $true)]
        [scriptblock] $Command
    )

    Write-Host $Description
    & $Command
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed with exit code $LASTEXITCODE"
    }
}

foreach ($asset in @("mermaid.min.js", "mermaid.LICENSE.txt")) {
    $assetPath = Join-Path $projectRoot "src\md_changer\assets\$asset"
    if (!(Test-Path -LiteralPath $assetPath -PathType Leaf) -or (Get-Item -LiteralPath $assetPath).Length -eq 0) {
        throw "Required Mermaid asset is missing or empty: $assetPath"
    }
}

Invoke-NativeCommand "Syncing Python environment with uv..." {
    uv sync --group build
}

$env:PLAYWRIGHT_BROWSERS_PATH = Join-Path $projectRoot "ms-playwright"
if (Test-Path "ms-playwright\chromium-*") {
    Write-Host "Bundled Chromium already exists. Skipping browser install."
} else {
    Invoke-NativeCommand "Installing bundled Chromium into ./ms-playwright..." {
        uv run playwright install chromium
    }
}

Invoke-NativeCommand "Running the full unittest suite..." {
    uv run python -m unittest discover -s tests -v
}

Invoke-NativeCommand "Building portable Windows app..." {
    uv run pyinstaller --clean --noconfirm md_changer.spec
}

Write-Host ""
Write-Host "Build complete."
Write-Host "Portable app folder: dist\md_changer"
Write-Host "Executable: dist\md_changer\md_changer.exe"
