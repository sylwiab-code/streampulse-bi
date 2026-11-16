"""Prepare and run the StreamPulse Astro project (ADR-010).

From the repository root:

    uv run python orchestration/airflow/run_astro.py start     # build and start Airflow locally
    uv run python orchestration/airflow/run_astro.py stop
    uv run python orchestration/airflow/run_astro.py test      # DAG tests inside the image

Before building, it exports pinned requirements and wheels from the repository's uv.lock into
build/ and refreshes the dbt manifest that Cosmos reads. It passes the repository's .env to the
containers and the host path of the DEV key file to the read-only mount
(docker-compose.override.yml); the key's content is never read.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

from streampulse_loader.settings import load_settings

PROJECT = Path(__file__).resolve().parent
REPO = PROJECT.parents[1]
BUILD = PROJECT / "build"
IMAGE = "streampulse-airflow:dev"
PACKAGES = ("streampulse-generator", "streampulse-loader", "streampulse-powerbi")


def run(command: Sequence[str], cwd: Path = REPO, env: dict[str, str] | None = None) -> None:
    subprocess.run(list(command), cwd=cwd, env=env, check=True)


def prepare_build() -> None:
    shutil.rmtree(BUILD, ignore_errors=True)
    (BUILD / "wheels").mkdir(parents=True)
    for package in PACKAGES:
        run(
            [
                "uv",
                "build",
                "--quiet",
                "--package",
                package,
                "--wheel",
                "--out-dir",
                str(BUILD / "wheels"),
            ]
        )
    export = ["uv", "export", "--quiet", "--frozen", "--no-emit-workspace", "--no-emit-project"]
    run(
        [
            *export,
            "--no-default-groups",
            "--output-file",
            str(BUILD / "requirements-streampulse.txt"),
        ]
    )
    run(
        [*export, "--only-group", "transform", "--output-file", str(BUILD / "requirements-dbt.txt")]
    )


def prepare_dbt_manifest() -> None:
    for dbt_command in ("deps", "parse"):
        run([sys.executable, "transform/run_dbt.py", dbt_command, "--quiet"])


def main(argv: Sequence[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        raise SystemExit(
            "Give a command: start, restart, stop, test, or another `astro dev` command"
        )
    command, extra = args[0], args[1:]
    settings = load_settings("dev", env_file=REPO / ".env")
    environment = {
        **os.environ,
        "STREAMPULSE_REPO_DIR": REPO.as_posix(),
        "STREAMPULSE_KEY_FILE": settings.private_key_path.resolve().as_posix(),
    }
    if command in {"start", "restart", "test"}:
        prepare_build()
        prepare_dbt_manifest()
    if command == "test":
        run(["docker", "build", "--quiet", "--tag", IMAGE, str(PROJECT)], cwd=PROJECT)
        mount = f"{(REPO / 'transform' / 'dbt').as_posix()}:/usr/local/airflow/dbt/streampulse:ro"
        test = ["docker", "run", "--rm", "--volume", mount, "--entrypoint", "python", IMAGE]
        return subprocess.run(
            [*test, "-m", "pytest", "tests", "-q", *extra], check=False
        ).returncode
    astro = ["astro", "dev", command, *extra]
    if command in {"start", "restart"}:
        astro += ["--env", str(REPO / ".env")]
    return subprocess.run(astro, cwd=PROJECT, env=environment, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
