#!/usr/bin/env python3
"""
Automated dependency analysis for the YOLO detector build.

The script surfaces the key environment details needed to understand
why wheel-only installs fail (e.g., unavailable OpenCV wheels).
"""
from __future__ import annotations

import argparse
import json
import importlib.util
import platform
import subprocess
import sys
from pathlib import Path

_packaging_spec = importlib.util.find_spec("pip._vendor.packaging.requirements")
if _packaging_spec is None:  # pragma: no cover - pip vendor should always exist
    print("Unable to import packaging; please run inside a Python environment with pip installed.", file=sys.stderr)
    sys.exit(1)
from pip._vendor.packaging.requirements import Requirement


def run_command(command: list[str]) -> tuple[int, str, str]:
    """Run a command and capture stdout/stderr."""
    proc = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return proc.returncode, proc.stdout.strip(), proc.stderr.strip()


def parse_requirements(path: Path) -> list[Requirement]:
    """Parse requirement lines, ignoring comments and empty lines."""
    requirements: list[Requirement] = []
    for line in path.read_text().splitlines():
        striped = line.strip()
        if not striped or striped.startswith("#"):
            continue
        requirements.append(Requirement(striped))
    return requirements


def summarize_environment() -> dict[str, str]:
    """Collect platform and pip configuration information."""
    pip_config_code, pip_config_out, pip_config_err = run_command([sys.executable, "-m", "pip", "config", "list"])
    pip_config = pip_config_out if pip_config_code == 0 else pip_config_err

    pip_debug_code, pip_debug_out, pip_debug_err = run_command([sys.executable, "-m", "pip", "debug", "--verbose"])
    pip_debug = pip_debug_out if pip_debug_code == 0 else pip_debug_err

    return {
        "python_version": sys.version.replace("\n", " "),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "pip_config": pip_config,
        "pip_debug": pip_debug,
    }


def check_requirement_availability(requirement: Requirement) -> dict[str, str | list[str]]:
    """Use `pip index versions` to report available releases and whether the specifier matches one."""
    name = requirement.name
    specifier = str(requirement.specifier) if requirement.specifier else ""

    code, out, err = run_command([sys.executable, "-m", "pip", "index", "versions", name])
    available_versions: list[str] = []
    note = ""

    if code == 0 and out:
        for line in out.splitlines():
            if line.strip().startswith("Available versions:"):
                versions_part = line.split(":", 1)[-1]
                available_versions = [v.strip() for v in versions_part.split(",") if v.strip()]
                break
        if requirement.specifier:
            matching = [v for v in available_versions if requirement.specifier.contains(v)]
            if matching:
                note = f"Specifier {specifier} matches: {', '.join(matching)}"
            else:
                note = f"Specifier {specifier} does not match available versions"
    else:
        note = f"pip index query failed: {err or 'unknown error'}"

    return {
        "name": name,
        "specifier": specifier,
        "available_versions": available_versions,
        "note": note,
    }


def analyze(requirements_path: Path) -> dict[str, object]:
    requirements = parse_requirements(requirements_path)
    environment = summarize_environment()
    checks = [check_requirement_availability(req) for req in requirements]
    return {
        "requirements_path": str(requirements_path),
        "environment": environment,
        "dependency_checks": checks,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze dependency availability for wheel-only installs")
    parser.add_argument(
        "--requirements",
        type=Path,
        default=Path(__file__).with_name("requirements.txt"),
        help="Path to the requirements file (default: sibling requirements.txt)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional path to write JSON output. If omitted, results are printed prettily to stdout.",
    )
    args = parser.parse_args()

    if not args.requirements.exists():
        parser.error(f"Requirements file not found: {args.requirements}")

    results = analyze(args.requirements)

    if args.output:
        args.output.write_text(json.dumps(results, indent=2))
        print(f"Analysis written to {args.output}")
    else:
        print(json.dumps(results, indent=2))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
