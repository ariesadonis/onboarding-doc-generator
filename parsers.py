import json
import re
from pathlib import Path

import yaml

# Directories to skip when scanning recursively
_IGNORE_DIRS = {
    "node_modules", ".git", ".github", "vendor", "dist", "build",
    ".venv", "venv", "__pycache__", ".tox", "coverage", ".nyc_output",
    "target", ".gradle", "bazel-out", ".next", ".nuxt", "out",
}

MAX_SCAN_DEPTH = 3


def _find_files(repo_path: Path, filename: str, max_depth: int = MAX_SCAN_DEPTH) -> list[Path]:
    """Return all matching files up to max_depth, root-first, skipping ignored dirs."""
    results = []

    def _walk(path: Path, depth: int):
        if depth > max_depth:
            return
        candidate = path / filename
        if candidate.exists():
            results.append(candidate)
        for child in sorted(path.iterdir()):
            if child.is_dir() and child.name not in _IGNORE_DIRS and not child.name.startswith("."):
                _walk(child, depth + 1)

    _walk(repo_path, 0)
    return results


def _find_file(repo_path: Path, filename: str, max_depth: int = MAX_SCAN_DEPTH) -> Path | None:
    """Return the first (shallowest) matching file, preferring root."""
    matches = _find_files(repo_path, filename, max_depth)
    return matches[0] if matches else None


def _find_any(repo_path: Path, filenames: list[str], max_depth: int = MAX_SCAN_DEPTH) -> Path | None:
    """Return the shallowest match across multiple candidate filenames."""
    candidates = []
    for name in filenames:
        match = _find_file(repo_path, name, max_depth)
        if match:
            candidates.append(match)
    if not candidates:
        return None
    return min(candidates, key=lambda p: len(p.parts))


def detect_languages(repo_path: Path) -> list[str]:
    markers = {
        "package.json": "JavaScript/Node.js",
        "requirements.txt": "Python",
        "pyproject.toml": "Python",
        "Gemfile": "Ruby",
        "pom.xml": "Java (Maven)",
        "build.gradle": "Java/Kotlin (Gradle)",
        "go.mod": "Go",
        "Cargo.toml": "Rust",
    }
    found = set()
    langs = []
    for fname, name in markers.items():
        if name not in found and _find_file(repo_path, fname):
            langs.append(name)
            found.add(name)
    return langs


def _read_text(path: Path) -> str:
    try:
        return path.read_text(errors="ignore")
    except OSError:
        return ""


def _best_package_json(repo_path: Path) -> Path | None:
    """Pick the package.json with the most dependencies (most informative)."""
    candidates = _find_files(repo_path, "package.json")
    if not candidates:
        return None
    # Prefer root-level if it has deps; otherwise pick by dep count
    def _dep_count(p: Path) -> int:
        try:
            data = json.loads(_read_text(p))
            return len(data.get("dependencies", {})) + len(data.get("devDependencies", {}))
        except (json.JSONDecodeError, OSError):
            return 0

    root = repo_path / "package.json"
    if root in candidates:
        root_count = _dep_count(root)
        # Only prefer a deeper file if it has significantly more deps and root is basically empty
        if root_count > 0:
            return root
    # Fall back to the one with most deps
    return max(candidates, key=_dep_count)


def parse_dependencies(repo_path: Path) -> dict:
    deps = {}

    pkg_json = _best_package_json(repo_path)
    if pkg_json:
        try:
            data = json.loads(_read_text(pkg_json))
        except json.JSONDecodeError:
            data = {}
        deps["node"] = {
            "install_command": "npm install",
            "dependencies": list(data.get("dependencies", {}).keys()),
            "dev_dependencies": list(data.get("devDependencies", {}).keys()),
            "scripts": data.get("scripts", {}),
            "source_file": str(pkg_json.relative_to(repo_path)),
        }

    requirements = _find_file(repo_path, "requirements.txt")
    if requirements:
        lines = [l.strip() for l in _read_text(requirements).splitlines() if l.strip() and not l.startswith("#")]
        deps["python"] = {"install_command": "pip install -r requirements.txt", "dependencies": lines}

    pyproject = _find_file(repo_path, "pyproject.toml")
    if pyproject and "python" not in deps:
        deps["python"] = {"install_command": "pip install .", "dependencies": []}

    gemfile = _find_file(repo_path, "Gemfile")
    if gemfile:
        gems = re.findall(r"gem\s+['\"]([^'\"]+)['\"]", _read_text(gemfile))
        deps["ruby"] = {"install_command": "bundle install", "dependencies": gems}

    go_mod = _find_file(repo_path, "go.mod")
    if go_mod:
        requires = re.findall(r"^\s*(?:require\s+)?([\w.-]+(?:/[\w.-]+)+)\s+v[\w.\-+]+", _read_text(go_mod), re.MULTILINE)
        deps["go"] = {"install_command": "go build ./...", "dependencies": requires}

    cargo_toml = _find_file(repo_path, "Cargo.toml")
    if cargo_toml:
        deps["rust"] = {"install_command": "cargo build", "dependencies": []}

    pom_xml = _find_file(repo_path, "pom.xml")
    if pom_xml:
        deps["java_maven"] = {"install_command": "mvn install", "dependencies": []}

    build_gradle = _find_any(repo_path, ["build.gradle", "build.gradle.kts"])
    if build_gradle:
        deps["java_gradle"] = {"install_command": "./gradlew build", "dependencies": []}

    return deps


def parse_env_setup(repo_path: Path) -> dict:
    setup = {}

    for version_file in [".nvmrc", ".python-version", ".tool-versions"]:
        f = _find_file(repo_path, version_file)
        if f:
            setup[version_file] = _read_text(f).strip()

    dockerfile = _find_file(repo_path, "Dockerfile")
    if dockerfile:
        setup["dockerfile"] = True

    compose = _find_any(repo_path, ["docker-compose.yml", "docker-compose.yaml"])
    if compose:
        try:
            data = yaml.safe_load(_read_text(compose))
            setup["docker_compose_services"] = list((data or {}).get("services", {}).keys())
        except yaml.YAMLError:
            setup["docker_compose_services"] = []

    # Collect env vars from ALL .env.example files found across the repo
    env_files = _find_files(repo_path, ".env.example")
    if not env_files:
        env_files = _find_files(repo_path, ".env.sample")
    if env_files:
        env_vars = []
        seen = set()
        for env_file in env_files:
            for line in _read_text(env_file).splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key = line.split("=", 1)[0]
                    if key not in seen:
                        env_vars.append(key)
                        seen.add(key)
        setup["env_vars"] = env_vars

    return setup


def _collect_start_commands(repo_path: Path) -> list[str]:
    """Scan all package.json files and return unique start/dev commands with their package context."""
    commands = []
    seen = set()
    for pkg_json in _find_files(repo_path, "package.json"):
        try:
            data = json.loads(_read_text(pkg_json))
        except (json.JSONDecodeError, OSError):
            continue
        scripts = data.get("scripts", {})
        pkg_name = data.get("name", "")
        rel = pkg_json.parent.relative_to(repo_path)
        is_root = rel == Path(".")
        for candidate in ("dev", "start"):
            if candidate in scripts:
                if is_root:
                    cmd = f"npm run {candidate}"
                else:
                    cmd = f"npm run {candidate}  # in {rel}/" if pkg_name == "" else f"npm run {candidate}  # {pkg_name}"
                if cmd not in seen:
                    commands.append(cmd)
                    seen.add(cmd)
                break  # one command per package.json
    return commands


def detect_start_command(repo_path: Path, deps: dict) -> str | None:
    if "node" in deps:
        commands = _collect_start_commands(repo_path)
        if commands:
            # Root-level single command: return as plain string
            if len(commands) == 1:
                return commands[0]
            # Multiple (monorepo): return newline-joined list
            return "\n".join(commands)

    if "python" in deps:
        for candidate in ("app.py", "main.py", "manage.py"):
            f = _find_file(repo_path, candidate)
            if f:
                if candidate == "manage.py":
                    return "python manage.py runserver"
                return f"python {candidate}"

    if "ruby" in deps and _find_file(repo_path, "config.ru"):
        return "rails server"

    if "go" in deps:
        return "go run ."

    if "rust" in deps:
        return "cargo run"

    if "java_maven" in deps:
        return "mvn spring-boot:run"

    if "java_gradle" in deps:
        return "./gradlew run"

    return None


def get_readme_summary(repo_path: Path, max_chars: int = 500) -> str | None:
    for name in ("README.md", "README.rst", "README.txt", "README"):
        f = repo_path / name
        if f.exists():
            text = _read_text(f).strip()
            text = re.sub(r"#+\s*", "", text)
            return text[:max_chars] + ("..." if len(text) > max_chars else "")
    return None
