#!/usr/bin/env python3
import json
import os
import subprocess
from datetime import datetime, timedelta


def get_git_blame_date(file_path, line_number):
    try:
        result = subprocess.run(  # noqa: S603
            [
                "/usr/bin/git",
                "blame",
                "--line-porcelain",
                "-L",
                f"{line_number},{line_number}",
                file_path,
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        for line in result.stdout.splitlines():
            if line.startswith("author-time "):
                timestamp = int(line.split(" ")[1])
                return datetime.fromtimestamp(timestamp)
    except subprocess.CalledProcessError:
        pass
    return datetime.now()


def _run_stale_check(file_path, deps_with_lines, dep_type, grep_args):
    print(f"Checking {dep_type} dependencies in {file_path}...")
    stale_threshold = datetime.now() - timedelta(days=90)

    for dep, line_num in deps_with_lines:
        date = get_git_blame_date(file_path, line_num)
        if date < stale_threshold:
            try:
                subprocess.run(grep_args(dep), capture_output=True, check=True)  # noqa: S603
            except subprocess.CalledProcessError:
                print(
                    f"Stale/Unused {dep_type} Dep: {dep} (Added: {date.strftime('%Y-%m-%d')})"
                )


def check_js_deps():
    try:
        with open("frontend/package.json", encoding="utf-8") as f:
            data = json.load(f)

        deps = list(data.get("dependencies", {}).keys()) + list(
            data.get("devDependencies", {}).keys()
        )

        with open("frontend/package.json", encoding="utf-8") as f:
            lines = f.readlines()

        deps_with_lines = [
            (d, i + 1)
            for d in deps
            for i, line_content in enumerate(lines)
            if f'"{d}"' in line_content
        ]

        _run_stale_check(
            "frontend/package.json",
            deps_with_lines,
            "JS",
            lambda dep: [
                "/bin/grep",
                "-r",
                "--exclude-dir=node_modules",
                "--exclude=package.json",
                dep,
                "frontend/src",
            ],
        )
    except Exception as e:  # noqa: BLE001, S110
        print(f"Error checking JS deps: {e}")


def check_py_deps():
    try:
        with open("backend/pyproject.toml", encoding="utf-8") as f:
            lines = f.readlines()

        deps_with_lines = []
        in_deps = False
        for i, line in enumerate(lines):
            line = line.strip()
            if line.startswith("dependencies = ["):
                in_deps = True
            elif line.startswith("]") and in_deps:
                in_deps = False
            elif in_deps and line.startswith('"'):
                dep = (
                    line.split('"')[1]
                    .split(" ")[0]
                    .split("=")[0]
                    .split("<")[0]
                    .split(">")[0]
                )
                deps_with_lines.append((dep, i + 1))

        _run_stale_check(
            "backend/pyproject.toml",
            deps_with_lines,
            "Py",
            lambda dep: [
                "/bin/grep",
                "-E",
                "-r",
                "--exclude-dir=.venv",
                f"import {dep.replace('-', '_')}|from {dep.replace('-', '_')}",
                "backend/src",
            ],
        )
    except Exception as e:  # noqa: BLE001, S110
        print(f"Error checking Py deps: {e}")


if __name__ == "__main__":
    root_dir = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )
    os.chdir(root_dir)
    check_js_deps()
    print()
    check_py_deps()
