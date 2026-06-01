$ErrorActionPreference = "Stop"

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

Invoke-NativeCommand "Syncing Python environment with uv..." {
    uv sync --group build
}

if (Test-Path "ms-playwright\chromium-*") {
    Write-Host "Bundled Chromium already exists. Skipping browser install."
} else {
    Invoke-NativeCommand "Installing bundled Chromium into ./ms-playwright..." {
        $env:PLAYWRIGHT_BROWSERS_PATH = "ms-playwright"
        uv run playwright install chromium
    }
}

Invoke-NativeCommand "Building portable Windows app..." {
    uv run pyinstaller --clean --noconfirm md_changer.spec
}

Write-Host ""
Write-Host "Build complete."
Write-Host "Portable app folder: dist\md_changer"
Write-Host "Executable: dist\md_changer\md_changer.exe"
