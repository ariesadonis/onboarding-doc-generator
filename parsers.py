import json
import re
from pathlib import Path

import yaml


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
    return [name for fname, name in markers.items() if (repo_path / fname).exists()]


def _read_text(path: Path) -> str:
    try:
        return path.read_text(errors="ignore")
    except OSError:
        return ""


def parse_dependencies(repo_path: Path) -> dict:
    deps = {}

    pkg_json = repo_path / "package.json"
    if pkg_json.exists():
        try:
            data = json.loads(_read_text(pkg_json))
        except json.JSONDecodeError:
            data = {}
        deps["node"] = {
            "install_command": "npm install",
            "dependencies": list(data.get("dependencies", {}).keys()),
            "dev_dependencies": list(data.get("devDependencies", {}).keys()),
            "scripts": data.get("scripts", {}),
        }

    requirements = repo_path / "requirements.txt"
    if requirements.exists():
        lines = [l.strip() for l in _read_text(requirements).splitlines() if l.strip() and not l.startswith("#")]
        deps["python"] = {"install_command": "pip install -r requirements.txt", "dependencies": lines}

    pyproject = repo_path / "pyproject.toml"
    if pyproject.exists() and "python" not in deps:
        deps["python"] = {"install_command": "pip install .", "dependencies": []}

    gemfile = repo_path / "Gemfile"
    if gemfile.exists():
        gems = re.findall(r"gem\s+['\"]([^'\"]+)['\"]", _read_text(gemfile))
        deps["ruby"] = {"install_command": "bundle install", "dependencies": gems}

    go_mod = repo_path / "go.mod"
    if go_mod.exists():
        requires = re.findall(r"^\s*(?:require\s+)?([\w.-]+(?:/[\w.-]+)+)\s+v[\w.\-+]+", _read_text(go_mod), re.MULTILINE)
        deps["go"] = {"install_command": "go build ./...", "dependencies": requires}

    cargo_toml = repo_path / "Cargo.toml"
    if cargo_toml.exists():
        deps["rust"] = {"install_command": "cargo build", "dependencies": []}

    pom_xml = repo_path / "pom.xml"
    if pom_xml.exists():
        deps["java_maven"] = {"install_command": "mvn install", "dependencies": []}

    build_gradle = repo_path / "build.gradle"
    if not build_gradle.exists():
        build_gradle = repo_path / "build.gradle.kts"
    if build_gradle.exists():
        deps["java_gradle"] = {"install_command": "./gradlew build", "dependencies": []}

    return deps


def parse_env_setup(repo_path: Path) -> dict:
    setup = {}

    for version_file in [".nvmrc", ".python-version", ".tool-versions"]:
        f = repo_path / version_file
        if f.exists():
            setup[version_file] = _read_text(f).strip()

    dockerfile = repo_path / "Dockerfile"
    if dockerfile.exists():
        setup["dockerfile"] = True

    compose = repo_path / "docker-compose.yml"
    if not compose.exists():
        compose = repo_path / "docker-compose.yaml"
    if compose.exists():
        try:
            data = yaml.safe_load(_read_text(compose))
            setup["docker_compose_services"] = list((data or {}).get("services", {}).keys())
        except yaml.YAMLError:
            setup["docker_compose_services"] = []

    env_example = repo_path / ".env.example"
    if env_example.exists():
        env_vars = []
        for line in _read_text(env_example).splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                env_vars.append(line.split("=", 1)[0])
        setup["env_vars"] = env_vars

    return setup


def detect_start_command(repo_path: Path, deps: dict) -> str | None:
    node = deps.get("node")
    if node:
        scripts = node.get("scripts", {})
        for candidate in ("start", "dev"):
            if candidate in scripts:
                return f"npm run {candidate}"

    if "python" in deps:
        for candidate in ("app.py", "main.py", "manage.py"):
            if (repo_path / candidate).exists():
                if candidate == "manage.py":
                    return "python manage.py runserver"
                return f"python {candidate}"

    if "ruby" in deps and (repo_path / "config.ru").exists():
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
