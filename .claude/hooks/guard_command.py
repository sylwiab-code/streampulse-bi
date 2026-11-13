"""Claude Code PreToolUse guard for shell commands (Bash and PowerShell tools).

Blocks a few dangerous commands before they run (ADR-001, D10):

- data tool commands or environment variables that mention PROD,
- skipping git hooks with --no-verify,
- force pushes and pushes to main,
- Liquibase changes without an explicit DEV target, and Liquibase drop-all.

This is a guardrail against mistakes, not a security boundary: string checks can be
bypassed. The real protection is that no PROD credentials exist on developer machines.
Exit code 2 blocks the command; the message on stderr is shown to Claude.
"""

from __future__ import annotations

import json
import re
import shlex
import sys

# Programs that can reach Snowflake, dbt targets, Airflow, or Fabric, plus generic launchers
# and commands that set environment variables.
DATA_TOOLS = frozenset(
    {
        "airflow",
        "astro",
        "dbt",
        "docker",
        "export",
        "fab",
        "liquibase",
        "py",
        "python",
        "python3",
        "set",
        "snow",
        "snowsql",
        "uv",
        "uvx",
    }
)
SEPARATORS = frozenset({";", "&&", "||", "|", "|&", "&", "(", ")"})
# Liquibase commands that change a database, normalized to lowercase without hyphens.
LIQUIBASE_CHANGES = frozenset(
    {
        "changelogsync",
        "changelogsynctotag",
        "marknextchangesetran",
        "update",
        "updatecount",
        "updateonechangeset",
        "updatetestingrollback",
        "updatetotag",
    }
)
PROD = re.compile(r"(?<![a-z0-9])prod(uction)?(?![a-z0-9])", re.IGNORECASE)
DEV = re.compile(r"(?<![a-z0-9])dev(elopment)?(?![a-z0-9])", re.IGNORECASE)
NOT_DEV = re.compile(r"(?<![a-z0-9])(prod(uction)?|test)(?![a-z0-9])", re.IGNORECASE)
ASSIGNMENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")


def split_commands(command: str) -> list[list[str]]:
    """Split a shell command line into simple commands, each a list of tokens."""
    command = re.sub(r"[\\`]\r?\n", " ", command)  # join continued lines
    command = re.sub(r"\r?\n", " ; ", command)  # each remaining line is its own command
    try:
        lexer = shlex.shlex(command, posix=True, punctuation_chars=True)
        lexer.whitespace_split = True
        tokens = list(lexer)
    except ValueError:  # unbalanced quotes: fall back to a rough split
        tokens = re.findall(r"&&|\|\||[;&|()]|[^\s;&|()]+", command)
    commands: list[list[str]] = [[]]
    for token in tokens:
        if token in SEPARATORS:
            commands.append([])
        else:
            commands[-1].append(token)
    return [tokens for tokens in commands if tokens]


def parse_command(tokens: list[str]) -> tuple[list[str], str, list[str]]:
    """Return the VAR=value prefixes, the normalized program name, and its arguments."""
    index = 0
    while index < len(tokens) and ASSIGNMENT.match(tokens[index]):
        index += 1
    if index == len(tokens):
        return tokens, "", []
    program = re.split(r"[\\/]", tokens[index])[-1].lower()
    program = re.sub(r"\.(exe|cmd|bat|ps1)$", "", program)
    return tokens[:index], program, tokens[index + 1 :]


def git_subcommand(args: list[str]) -> tuple[str, list[str]]:
    """Return the git subcommand and its arguments, skipping global options like -C."""
    index = 0
    while index < len(args) and args[index].startswith("-"):
        index += 2 if args[index] in {"-C", "-c"} else 1
    if index >= len(args):
        return "", []
    return args[index], args[index + 1 :]


def is_force_push(arg: str) -> bool:
    return (
        arg.startswith("--force")
        or re.fullmatch(r"-[A-Za-z]*f[A-Za-z]*", arg) is not None
        or (arg.startswith("+") and len(arg) > 1)
    )


def targets_main(arg: str) -> bool:
    if arg.startswith("-"):
        return False
    destination = arg.split(":")[-1].lstrip("+")
    return destination in {"main", "refs/heads/main"}


def check_git(args: list[str]) -> str | None:
    subcommand, rest = git_subcommand(args)
    if "--no-verify" in args or (subcommand == "commit" and "-n" in rest):
        return "skipping git hooks (--no-verify) is not allowed; fix the failing hook instead"
    if subcommand == "push":
        if any(is_force_push(arg) for arg in rest):
            return "force pushes are not allowed"
        if any(targets_main(arg) for arg in rest):
            return "pushing to main is not allowed; open a pull request instead"
    return None


def check_liquibase(args: list[str], text: str) -> str | None:
    normalized = [arg.lower().replace("-", "") for arg in args]
    if "dropall" in normalized:
        return "Liquibase drop-all is not allowed"
    changes = any(
        arg in LIQUIBASE_CHANGES or (arg.startswith("rollback") and not arg.endswith("sql"))
        for arg in normalized
    )
    if changes and (DEV.search(text) is None or NOT_DEV.search(text) is not None):
        return (
            "Liquibase changes run only against DEV with an explicit DEV target; "
            "use updateSQL to preview"
        )
    return None


def check(command: str) -> str | None:
    """Return the reason to block the command, or None if it may run."""
    for tokens in split_commands(command):
        assignments, program, args = parse_command(tokens)
        text = " ".join(tokens)
        touches_prod_setting = any(PROD.search(assignment) for assignment in assignments)
        is_data_tool = program in DATA_TOOLS or program.startswith("$env:")
        if touches_prod_setting or (is_data_tool and PROD.search(text)):
            return "commands that target PROD are not allowed; PROD changes go through CD"
        if program == "git":
            reason = check_git(args)
            if reason:
                return reason
        if program == "liquibase":
            reason = check_liquibase(args, text)
            if reason:
                return reason
    return None


def main() -> int:
    try:
        payload = json.loads(sys.stdin.buffer.read().decode("utf-8", errors="replace"))
    except ValueError:
        print("guard_command.py: could not read the hook input; blocking.", file=sys.stderr)
        return 2
    tool_input = payload.get("tool_input") if isinstance(payload, dict) else None
    command = tool_input.get("command") if isinstance(tool_input, dict) else None
    if not isinstance(command, str):
        return 0
    reason = check(command)
    if reason is None:
        return 0
    print(
        f"Blocked by .claude/hooks/guard_command.py: {reason}. "
        "If it is really needed, ask the user to run it.",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
