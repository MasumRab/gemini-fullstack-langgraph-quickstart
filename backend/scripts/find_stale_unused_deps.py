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


def check_js_deps():
    print("Checking JS dependencies in frontend/package.json...")
    try:
        with open("frontend/package.json") as f:
            package_json = json.load(f)

        deps = list(package_json.get("dependencies", {}).keys()) + list(
            package_json.get("devDependencies", {}).keys()
        )

        # Read the file again to find line numbers
        with open("frontend/package.json") as f:
            lines = f.readlines()

        stale_threshold = datetime.now() - timedelta(days=90)

        for dep in deps:
            # Find line number
            line_num = -1
            for i, line in enumerate(lines):
                if f'"{dep}"' in line:
                    line_num = i + 1
                    break

            if line_num != -1:
                date = get_git_blame_date("frontend/package.json", line_num)
                if date < stale_threshold:
                    # Check if used (simple grep)
                    try:
                        # Exclude node_modules and package.json itself
                        subprocess.run(  # noqa: S603
                            [
                                "/bin/grep",
                                "-r",
                                "--exclude-dir=node_modules",
                                "--exclude=package.json",
                                dep,
                                "frontend/src",
                            ],
                            capture_output=True,
                            check=True,
                        )
                    except subprocess.CalledProcessError:
                        print(
                            f"Stale/Unused JS Dep: {dep} (Added: {date.strftime('%Y-%m-%d')})"
                        )
    except Exception as e:  # noqa: BLE001, S110
        print(f"Error checking JS deps: {e}")


def check_py_deps():
    print("\nChecking Python dependencies in backend/pyproject.toml...")
    try:
        with open("backend/pyproject.toml") as f:
            lines = f.readlines()

        deps = []
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
                deps.append((dep, i + 1))

        stale_threshold = datetime.now() - timedelta(days=90)

        for dep, line_num in deps:
            date = get_git_blame_date("backend/pyproject.toml", line_num)
            if date < stale_threshold:
                # Check if used (simple grep)
                # Convert dash to underscore for python imports
                import_name = dep.replace("-", "_")
                try:
                    subprocess.run(  # noqa: S603
                        [
                            "/bin/grep",
                            "-E",
                            "-r",
                            "--exclude-dir=.venv",
                            f"import {import_name}|from {import_name}",
                            "backend/src",
                        ],
                        capture_output=True,
                        check=True,
                    )
                except subprocess.CalledProcessError:
                    print(
                        f"Stale/Unused Py Dep: {dep} (Added: {date.strftime('%Y-%m-%d')})"
                    )

    except Exception as e:  # noqa: BLE001, S110
        print(f"Error checking Py deps: {e}")


if __name__ == "__main__":
    # Determine project root
    root_dir = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )
    os.chdir(root_dir)
    check_js_deps()
    check_py_deps()
