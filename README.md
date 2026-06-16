# onboarding-doc-generator

Auto-generates an onboarding/setup doc from a repo's actual structure, instead of relying on hand-written docs that go stale.

Point it at a repo (a Git URL or a local path) and it scans dependency files, environment config, and Docker setup to produce a single `onboarding.md` with everything a new contributor needs to get running: language/runtime versions, install commands, environment variables, and a start command.

## Why

Onboarding docs are usually written once and never updated. The repo's actual config (`package.json`, `requirements.txt`, `.env.example`, `Dockerfile`, etc.) is the real source of truth, so this generates the doc from that instead of from memory.

## Install

```bash
git clone https://github.com/ariesadonis/onboarding-doc-generator
cd onboarding-doc-generator
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Usage

```bash
python cli.py <repo-url-or-local-path> -o onboarding.md
```

Options:

| Flag | Description |
|---|---|
| `-o, --output` | Output file path (default: `onboarding.md`) |
| `-b, --branch` | Branch to clone (default: the repo's default branch) |

Examples:

```bash
# Generate a doc for a remote repo
python cli.py https://github.com/pallets/flask -o flask-onboarding.md

# Generate a doc for a local checkout
python cli.py ~/code/my-project
```

## What it detects

- **Languages**: Node.js, Python, Ruby, Java (Maven/Gradle), Go, Rust
- **Dependencies**: `package.json`, `requirements.txt`, `pyproject.toml`, `Gemfile`, `go.mod`, `Cargo.toml`, `pom.xml`, `build.gradle`
- **Environment setup**: `.nvmrc`, `.python-version`, `.tool-versions`, `Dockerfile`, `docker-compose.yml`, `.env.example`
- **Start command**: inferred from `package.json` scripts, common Python entry points, or framework conventions

## Output

The generated doc includes:

- Prerequisites (language/runtime versions)
- Environment setup (env vars to copy from `.env.example`, Docker Compose services)
- Install commands per detected ecosystem
- A best-guess run command
- A "known gaps" checklist for the tribal knowledge automation can't catch (access requests, team conventions, gotchas)
- A footer noting the source commit, so staleness is visible

## Status

Early CLI prototype — repo in, markdown out. No web UI, no CI integration, no auto-update on a schedule yet. Feedback on what it gets wrong is the main thing I'm looking for right now.

## Tests

```bash
pip install -r requirements.txt
pytest
```
