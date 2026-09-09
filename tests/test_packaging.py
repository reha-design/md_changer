"""Guard the package data and PyInstaller inputs required for offline PDFs."""

import ast
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import tomllib
import unittest


ROOT = Path(__file__).resolve().parents[1]


class PackagingTests(unittest.TestCase):
    def test_wheel_package_data_includes_runtime_and_license(self):
        config = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
        patterns = config["tool"]["setuptools"].get("package-data", {}).get("md_changer", [])
        packaged = {path.name for pattern in patterns for path in (ROOT / "src/md_changer").glob(pattern)}
        self.assertTrue(
            {"mermaid.min.js", "mermaid.LICENSE.txt"}.issubset(packaged),
            f"Wheel package data is missing Mermaid assets: {packaged}",
        )

    def test_pyinstaller_analyzes_existing_unified_entrypoint(self):
        tree = ast.parse((ROOT / "md_changer.spec").read_text(encoding="utf-8"))
        analysis = next(node for node in ast.walk(tree) if isinstance(node, ast.Call)
                        and isinstance(node.func, ast.Name) and node.func.id == "Analysis")
        self.assertEqual(ast.literal_eval(analysis.args[0]), ["main.py"])
        self.assertTrue((ROOT / "main.py").is_file())


@unittest.skipUnless(shutil.which("pwsh") or shutil.which("powershell"), "PowerShell is required")
class BuildScriptTests(unittest.TestCase):
    def run_build(self, *, missing=None, fail_tests=False):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            shutil.copyfile(ROOT / "build.ps1", root / "build.ps1")
            assets = root / "src/md_changer/assets"
            assets.mkdir(parents=True)
            for name in ("mermaid.min.js", "mermaid.LICENSE.txt"):
                if name != missing:
                    (assets / name).write_text("fixture", encoding="utf-8")
            (root / "ms-playwright/chromium-fixture").mkdir(parents=True)
            # Stub only the external package manager. Execute the real script's
            # checks and error handling without downloading or building an EXE.
            command = """
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
function uv {
    Write-Output ('UV: ' + ($args -join ' '))
    Write-Output ('PYTHON: ' + $env:UV_PYTHON)
    $global:LASTEXITCODE = 0
    if ($env:TEST_FAIL_UNITTEST -eq '1' -and $args -contains 'unittest') {
        $global:LASTEXITCODE = 37
    }
}
& ./build.ps1
"""
            environment = dict(os.environ, UV_PYTHON=sys.executable,
                               TEST_FAIL_UNITTEST="1" if fail_tests else "0")
            return subprocess.run(
                [shutil.which("pwsh") or shutil.which("powershell"),
                 "-NoProfile", "-NonInteractive", "-Command", command],
                cwd=root, env=environment, capture_output=True, text=True, encoding="utf-8",
            )

    def test_build_preserves_explicit_compatible_python_selection(self):
        result = self.run_build()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(f"PYTHON: {sys.executable}", result.stdout)

    def test_failed_unittests_stop_packaging(self):
        result = self.run_build(fail_tests=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("exit code 37", result.stderr)
        self.assertNotIn("UV: run pyinstaller", result.stdout)

    def test_missing_runtime_or_license_fails_before_sync(self):
        for name in ("mermaid.min.js", "mermaid.LICENSE.txt"):
            with self.subTest(asset=name):
                result = self.run_build(missing=name)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("Required Mermaid asset is missing or empty", result.stderr)
                self.assertIn(name, result.stderr)
                self.assertNotIn("UV:", result.stdout)


if __name__ == "__main__":
    unittest.main()
