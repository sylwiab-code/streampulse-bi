"""Run the Best Practice Analyzer on the semantic model with Tabular Editor 2 (ADR-011).

From the repository root (Windows; Tabular Editor 2 is a .NET Framework tool):

    uv run python semantic/powerbi/run_bpa.py

Uses Microsoft's standard rules (pinned commit) plus bpa-rules.json from this folder. Both
downloads are pinned by SHA-256 and cached under %LOCALAPPDATA%/streampulse/tools. Exceptions
are BestPracticeAnalyzer_IgnoreRules annotations in the model, documented in the README.
Exit code 1 when any rule is violated.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFINITION = HERE / "StreamPulse.SemanticModel" / "definition"
CUSTOM_RULES = HERE / "bpa-rules.json"

TABULAR_EDITOR_VERSION = "2.29.0"
TABULAR_EDITOR_URL = (
    "https://github.com/TabularEditor/TabularEditor/releases/download/"
    f"{TABULAR_EDITOR_VERSION}/TabularEditor.Portable.zip"
)
TABULAR_EDITOR_SHA256 = "c0d3a7abda4572baaf3aeedf9cb342ce7ad4d9840e6438d6b13df02267d308a4"

MICROSOFT_RULES_COMMIT = "50e8ce5028dd7046e73974ec69cb79af225e41b0"
MICROSOFT_RULES_URL = (
    "https://raw.githubusercontent.com/microsoft/Analysis-Services/"
    f"{MICROSOFT_RULES_COMMIT}/BestPracticeRules/BPARules.json"
)
MICROSOFT_RULES_SHA256 = "ddb9cff4c2a0611a6467e2559d38319d9867381998066473ffa1e11c2d360392"


def tools_dir() -> Path:
    base = os.environ.get("LOCALAPPDATA") or str(Path.home() / ".cache")
    return Path(base) / "streampulse" / "tools"


def download(url: str, sha256: str, target: Path) -> Path:
    """Download once; refuse a file whose checksum does not match the pinned one."""
    if not target.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(url, timeout=120) as response:
            data = response.read()
        if hashlib.sha256(data).hexdigest() != sha256:
            raise SystemExit(f"Checksum mismatch for {url}; not using it.")
        target.write_bytes(data)
    elif hashlib.sha256(target.read_bytes()).hexdigest() != sha256:
        raise SystemExit(f"Cached file {target} does not match its pinned checksum.")
    return target


def tabular_editor() -> Path:
    folder = tools_dir() / f"tabular-editor-{TABULAR_EDITOR_VERSION}"
    exe = folder / "TabularEditor.exe"
    if not exe.exists():
        archive = download(TABULAR_EDITOR_URL, TABULAR_EDITOR_SHA256, folder.with_suffix(".zip"))
        with zipfile.ZipFile(archive) as content:
            content.extractall(folder)
        archive.unlink()
    return exe


def combined_rules(target: Path) -> Path:
    microsoft = download(
        MICROSOFT_RULES_URL,
        MICROSOFT_RULES_SHA256,
        tools_dir() / f"BPARules-{MICROSOFT_RULES_COMMIT[:7]}.json",
    )
    rules = json.loads(microsoft.read_text(encoding="utf-8-sig"))
    rules += json.loads(CUSTOM_RULES.read_text(encoding="utf-8"))
    target.write_text(json.dumps(rules, indent=2), encoding="utf-8")
    return target


def violations(output: str) -> list[str]:
    return [line.strip() for line in output.splitlines() if "violates rule" in line]


def main() -> int:
    if sys.platform != "win32":
        raise SystemExit("Tabular Editor 2 runs on Windows only.")
    with tempfile.TemporaryDirectory() as temp:
        rules = combined_rules(Path(temp) / "rules.json")
        result = subprocess.run(
            [str(tabular_editor()), str(DEFINITION), "-A", str(rules)],
            capture_output=True,
            text=True,
            check=False,
        )
    found = violations(result.stdout)
    if "Loading model..." not in result.stdout or (result.returncode and not found):
        print(result.stdout, result.stderr, sep="\n")
        raise SystemExit("Tabular Editor could not analyze the model.")
    for line in found:
        print(line)
    print(f"{len(found)} violation(s).")
    return 1 if found else 0


if __name__ == "__main__":
    raise SystemExit(main())
