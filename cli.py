import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from parsers import (
    detect_languages,
    detect_start_command,
    get_readme_summary,
    parse_dependencies,
    parse_env_setup,
)

TEMPLATE_DIR = Path(__file__).parent / "templates"
CLONE_TIMEOUT_SECONDS = 60


def check_git_available() -> None:
    if shutil.which("git") is None:
        print("Error: git is not installed or not on PATH.", file=sys.stderr)
        sys.exit(1)


def validate_output_path(output: Path) -> None:
    parent = output.parent if str(output.parent) else Path(".")
    if not parent.is_dir():
        print(f"Error: output directory does not exist: {parent}", file=sys.stderr)
        sys.exit(1)
    if not os.access(parent, os.W_OK):
        print(f"Error: cannot write to output directory: {parent}", file=sys.stderr)
        sys.exit(1)


def clone_repo(repo_url_or_path: str, dest: Path, branch: str | None = None) -> Path:
    local_path = Path(repo_url_or_path).expanduser()
    if local_path.exists():
        if not local_path.is_dir():
            print(f"Error: {local_path} is not a directory.", file=sys.stderr)
            sys.exit(1)
        return local_path

    check_git_available()

    cmd = ["git", "clone", "--depth", "1"]
    if branch:
        cmd += ["--branch", branch]
    cmd += [repo_url_or_path, str(dest)]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=CLONE_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        print(f"Error: git clone timed out after {CLONE_TIMEOUT_SECONDS}s.", file=sys.stderr)
        sys.exit(1)

    if result.returncode != 0:
        print(f"Error: git clone failed:\n{result.stderr.strip()}", file=sys.stderr)
        sys.exit(1)
    return dest


def get_commit_hash(repo_path: Path) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo_path), "rev-parse", "--short", "HEAD"],
        capture_output=True,
        text=True,
    )
    return result.stdout.strip() if result.returncode == 0 else "unknown"


def generate_doc(repo_path: Path, repo_name: str) -> str:
    languages = detect_languages(repo_path)
    dependencies = parse_dependencies(repo_path)
    env_setup = parse_env_setup(repo_path)
    start_command = detect_start_command(repo_path, dependencies)
    readme_summary = get_readme_summary(repo_path)
    commit_hash = get_commit_hash(repo_path)

    env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)))
    template = env.get_template("onboarding.md.j2")

    return template.render(
        repo_name=repo_name,
        languages=languages,
        dependencies=dependencies,
        env_setup=env_setup,
        start_command=start_command,
        readme_summary=readme_summary,
        commit_hash=commit_hash,
        generated_at=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    )


def main():
    parser = argparse.ArgumentParser(description="Generate an onboarding doc from a repo.")
    parser.add_argument("repo", help="Git URL or local path to the repo")
    parser.add_argument("-o", "--output", default="onboarding.md", help="Output file path")
    parser.add_argument("-b", "--branch", default=None, help="Branch to clone (default: repo's default branch)")
    args = parser.parse_args()

    if not args.repo.strip():
        print("Error: repo argument cannot be empty.", file=sys.stderr)
        sys.exit(1)

    output_path = Path(args.output)
    validate_output_path(output_path)

    repo_name = Path(args.repo.rstrip("/")).stem or "repo"

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            clone_dest = Path(tmpdir) / "repo"
            repo_path = clone_repo(args.repo, clone_dest, branch=args.branch)
            doc = generate_doc(repo_path, repo_name)
    except Exception as exc:
        print(f"Error: failed to generate onboarding doc: {exc}", file=sys.stderr)
        sys.exit(1)

    output_path.write_text(doc)
    print(f"Onboarding doc written to {output_path}")


if __name__ == "__main__":
    main()
