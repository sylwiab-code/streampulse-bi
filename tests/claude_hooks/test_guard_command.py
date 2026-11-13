"""Tests for the Claude Code command guard in .claude/hooks/guard_command.py."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

GUARD_PATH = Path(__file__).resolve().parents[2] / ".claude" / "hooks" / "guard_command.py"
_spec = importlib.util.spec_from_file_location("guard_command", GUARD_PATH)
assert _spec is not None and _spec.loader is not None
guard = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(guard)


@pytest.mark.parametrize(
    "command",
    [
        # PROD
        "snow sql -c prod -q 'select 1'",
        "uv run dbt build --target prod",
        "dbt run --target production",
        "SNOWFLAKE_DATABASE=PROD dbt run",
        "export SNOWFLAKE_DATABASE=STREAMPULSE_PROD",
        "$env:SNOWFLAKE_DATABASE = 'PROD'",
        "git status && snow sql -c prod",
        "git status\nsnow sql -c prod",
        "uv run dbt build \\\n  --target prod",
        # Skipping git hooks
        "git commit --no-verify -m 'wip'",
        "git commit -n -m 'wip'",
        "git push --no-verify",
        # Force pushes and pushes to main
        "git push --force",
        "git push -f origin feat/x",
        "git push --force-with-lease origin feat/x",
        "git push origin +feat/x",
        "git push origin main",
        "git push origin HEAD:main",
        "git -C repo push origin main",
        "(cd repo && git push --force)",
        # Liquibase
        "liquibase update",
        "liquibase --contexts=test update",
        "liquibase --contexts=dev --url=jdbc:snowflake://x/?db=STREAMPULSE_TEST update",
        "liquibase rollback-count 1",
        "liquibase drop-all --contexts=dev",
    ],
)
def test_blocks(command: str) -> None:
    assert guard.check(command) is not None


@pytest.mark.parametrize(
    "command",
    [
        "git commit -m 'docs: describe the PROD deployment approval'",
        "git commit -F - <<'EOF'\nci: add CD workflow\n\nDeploys to PROD after approval.\nEOF",
        "gh pr create --title 'ci: add PROD approval gate'",
        "git push -u origin chore/claude-code-guardrails",
        "git push origin feat/main-menu",
        "uv run pytest",
        "uv run pre-commit run --all-files",
        "uv run dbt build --target dev",
        "dbt run --select product_catalog",
        "liquibase updateSQL",
        "liquibase rollbackSQL v1",
        "liquibase update --contexts=dev",
        "liquibase --defaults-file=liquibase.dev.properties update",
    ],
)
def test_allows(command: str) -> None:
    assert guard.check(command) is None


def run_guard(stdin: str) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        [sys.executable, str(GUARD_PATH)],
        input=stdin.encode("utf-8"),
        capture_output=True,
        check=False,
    )


def hook_input(command: str) -> str:
    return json.dumps({"tool_name": "Bash", "tool_input": {"command": command}})


def test_hook_blocks_with_exit_code_2_and_reason() -> None:
    result = run_guard(hook_input("git push --force"))
    assert result.returncode == 2
    assert b"force pushes are not allowed" in result.stderr


def test_hook_allows_with_exit_code_0() -> None:
    result = run_guard(hook_input("gh pr create --body 'Generated with Claude Code 🤖'"))
    assert result.returncode == 0
    assert result.stderr == b""


def test_hook_ignores_input_without_a_command() -> None:
    result = run_guard(json.dumps({"tool_name": "Bash", "tool_input": {}}))
    assert result.returncode == 0


def test_hook_blocks_unreadable_input() -> None:
    result = run_guard("not json")
    assert result.returncode == 2
