"""Command line: `powerbi refresh`, `powerbi wait`, `powerbi validate`."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

from .client import PowerBIClient, PowerBISettings
from .validate import load_checks, run_checks

# Packaged with the module, so the default also works in the Airflow image.
DEFAULT_CHECKS = Path(__file__).resolve().parent / "checks.json"


def _validate(client: PowerBIClient, checks_path: Path) -> int:
    checks = load_checks(checks_path)
    if not checks:
        print(f"No checks configured in {checks_path}; nothing to validate.")
        return 0
    from streampulse_loader.settings import connect, load_settings

    settings = load_settings("dev")
    connection = connect(settings, settings.role("reporter"), settings.warehouse("report"))
    try:

        def snowflake_value(sql: str) -> float:
            return connection.cursor().execute(sql).fetchone()[0]

        def power_bi_value(dax: str) -> float:
            return next(iter(client.execute_query(dax)[0].values()))

        results = run_checks(checks, snowflake_value, power_bi_value)
    finally:
        connection.close()
    for result in results:
        mark = "OK  " if result.passed else "FAIL"
        print(
            f"{mark} {result.check.name}: Snowflake {result.snowflake_value:,.2f}, "
            f"Power BI {result.power_bi_value:,.2f}"
        )
    return 0 if all(result.passed for result in results) else 1


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="powerbi", description="Power BI refresh and checks.")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("refresh", help="start a refresh of the semantic model")
    wait = commands.add_parser("wait", help="wait for the latest refresh to finish")
    wait.add_argument("--timeout", type=int, default=3600, help="seconds (default 3600)")
    wait.add_argument("--poll", type=int, default=30, help="seconds between checks (default 30)")
    validate = commands.add_parser("validate", help="compare Power BI with Snowflake")
    validate.add_argument("--checks", type=Path, default=DEFAULT_CHECKS)
    args = parser.parse_args(argv)

    client = PowerBIClient(PowerBISettings.from_environment())
    if args.command == "refresh":
        client.trigger_refresh()
        print("Refresh started.")
        return 0
    if args.command == "wait":
        refresh = client.wait_for_refresh(args.timeout, args.poll)
        print(f"Refresh {refresh.get('status')} at {refresh.get('endTime')}.")
        return 0
    return _validate(client, args.checks)


if __name__ == "__main__":
    raise SystemExit(main())
