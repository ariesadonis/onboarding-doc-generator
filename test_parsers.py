import json
from pathlib import Path

from parsers import (
    detect_languages,
    detect_start_command,
    get_readme_summary,
    parse_dependencies,
    parse_env_setup,
)


def test_detect_languages_node(tmp_path: Path):
    (tmp_path / "package.json").write_text("{}")
    assert "JavaScript/Node.js" in detect_languages(tmp_path)


def test_parse_dependencies_node(tmp_path: Path):
    (tmp_path / "package.json").write_text(
        '{"dependencies": {"express": "^4.0.0"}, "scripts": {"start": "node index.js"}}'
    )
    deps = parse_dependencies(tmp_path)
    assert deps["node"]["install_command"] == "npm install"
    assert "express" in deps["node"]["dependencies"]


def test_parse_dependencies_malformed_package_json(tmp_path: Path):
    (tmp_path / "package.json").write_text("{not valid json")
    deps = parse_dependencies(tmp_path)
    assert deps["node"]["dependencies"] == []


def test_parse_dependencies_python_requirements(tmp_path: Path):
    (tmp_path / "requirements.txt").write_text("flask==2.0\n# comment\n\nrequests\n")
    deps = parse_dependencies(tmp_path)
    assert deps["python"]["dependencies"] == ["flask==2.0", "requests"]


def test_parse_dependencies_go(tmp_path: Path):
    (tmp_path / "go.mod").write_text("module example.com/foo\n\nrequire github.com/pkg/errors v0.9.1\n")
    deps = parse_dependencies(tmp_path)
    assert "go" in deps
    assert "github.com/pkg/errors" in deps["go"]["dependencies"]


def test_parse_env_setup_env_example(tmp_path: Path):
    (tmp_path / ".env.example").write_text("API_KEY=\nDB_URL=postgres://localhost\n# comment\n")
    setup = parse_env_setup(tmp_path)
    assert setup["env_vars"] == ["API_KEY", "DB_URL"]


def test_parse_env_setup_docker_compose(tmp_path: Path):
    (tmp_path / "docker-compose.yml").write_text("services:\n  web:\n    image: nginx\n  db:\n    image: postgres\n")
    setup = parse_env_setup(tmp_path)
    assert set(setup["docker_compose_services"]) == {"web", "db"}


def test_parse_env_setup_malformed_compose_file(tmp_path: Path):
    (tmp_path / "docker-compose.yml").write_text(": this is not : valid yaml :::")
    setup = parse_env_setup(tmp_path)
    assert setup["docker_compose_services"] == []


def test_detect_start_command_node_start_script(tmp_path: Path):
    (tmp_path / "package.json").write_text(json.dumps({"scripts": {"start": "node index.js"}}))
    deps = {"node": {"scripts": {"start": "node index.js"}}}
    assert detect_start_command(tmp_path, deps) == "npm run start"


def test_detect_start_command_python_app(tmp_path: Path):
    (tmp_path / "app.py").write_text("")
    deps = {"python": {}}
    assert detect_start_command(tmp_path, deps) == "python app.py"


def test_detect_start_command_none_found(tmp_path: Path):
    assert detect_start_command(tmp_path, {}) is None


def test_get_readme_summary(tmp_path: Path):
    (tmp_path / "README.md").write_text("# My Project\nA cool project.")
    summary = get_readme_summary(tmp_path)
    assert "My Project" in summary
    assert "A cool project." in summary


def test_get_readme_summary_missing(tmp_path: Path):
    assert get_readme_summary(tmp_path) is None
