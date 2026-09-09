# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

from PyInstaller.building.build_main import Analysis, EXE, COLLECT, PYZ
from PyInstaller.utils.hooks import collect_all, collect_data_files


project_dir = Path.cwd()
playwright_datas, playwright_binaries, playwright_hiddenimports = collect_all("playwright")

datas = list(playwright_datas) + collect_data_files("md_changer")
binaries = list(playwright_binaries)
hiddenimports = list(playwright_hiddenimports)

browser_dir = project_dir / "ms-playwright"
if browser_dir.exists():
    datas.append((str(browser_dir), "ms-playwright"))


a = Analysis(
    ["main.py"],
    pathex=[str(project_dir / "src")],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="md_changer",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="md_changer",
)
