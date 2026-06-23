"""
Drift detection: compare what existing docs claim against what config files actually say.
Produces a structured report in the 5-point format:
  1. What source files imply
  2. What the current doc says
  3. Exact drift/conflict
  4. Proposed patch
  5. Confidence + unchecked assumptions
"""
import re
from dataclasses import dataclass, field
from pathlib import Path

# ── helpers ────────────────────────────────────────────────────────────────────

_IGNORE_DIRS = {
    "node_modules", ".git", ".github", "vendor", "dist", "build",
    ".venv", "venv", "__pycache__", ".next", ".nuxt", "out", "target",
}

_ENV_VAR_RE = re.compile(r'\b([A-Z][A-Z0-9_]{2,})\b')
_CODE_BLOCK_RE = re.compile(r'```[^\n]*\n(.*?)```', re.DOTALL)
_INLINE_CODE_RE = re.compile(r'`([^`]+)`')
_VERSION_RE = re.compile(r'(?:node|nodejs|npm|python|ruby|go)\s*[>=v]*\s*(\d+[\d.]*)', re.IGNORECASE)
_SERVICE_KEYWORDS = {"postgres", "postgresql", "mysql", "redis", "mongo", "mongodb",
                     "rabbitmq", "kafka", "elasticsearch", "localstack", "mailhog", "minio"}


def _read(path: Path) -> str:
    try:
        return path.read_text(errors="ignore")
    except OSError:
        return ""


def _find_doc_files(repo_path: Path) -> list[Path]:
    candidates = []
    for name in ("README.md", "README.rst", "README.txt", "CONTRIBUTING.md",
                 "CONTRIBUTING.rst", "docs/setup.md", "docs/development.md",
                 "docs/getting-started.md", "docs/onboarding.md"):
        p = repo_path / name
        if p.exists():
            candidates.append(p)
    return candidates


# ── doc claim extraction ────────────────────────────────────────────────────────

@dataclass
class DocClaims:
    env_vars: set[str] = field(default_factory=set)
    services: set[str] = field(default_factory=set)
    start_commands: list[str] = field(default_factory=list)
    versions: dict[str, str] = field(default_factory=dict)
    has_env_example_mention: bool = False
    has_docker_compose_mention: bool = False
    source_files: list[str] = field(default_factory=list)


def extract_doc_claims(repo_path: Path) -> DocClaims:
    claims = DocClaims()
    doc_files = _find_doc_files(repo_path)
    claims.source_files = [str(f.relative_to(repo_path)) for f in doc_files]

    for doc_file in doc_files:
        text = _read(doc_file)

        # env vars: ALL_CAPS_WITH_UNDERSCORES in code blocks and inline code
        for block in _CODE_BLOCK_RE.findall(text):
            claims.env_vars.update(_ENV_VAR_RE.findall(block))
        for inline in _INLINE_CODE_RE.findall(text):
            claims.env_vars.update(_ENV_VAR_RE.findall(inline))

        # filter out common false positives (shell commands, markdown artifacts)
        _FALSE_POSITIVE_PREFIXES = ("HTTP", "URL", "API", "CI", "CD", "PR", "EOF",
                                    "TRUE", "FALSE", "NULL", "NONE", "PATH", "HOME",
                                    "USER", "SHELL", "TERM", "PWD", "IFS")
        claims.env_vars = {
            v for v in claims.env_vars
            if len(v) > 3 and not any(v == p for p in _FALSE_POSITIVE_PREFIXES)
        }

        # services mentioned by name
        text_lower = text.lower()
        for svc in _SERVICE_KEYWORDS:
            if svc in text_lower:
                claims.services.add(svc)

        # start commands: lines inside code blocks starting with npm/yarn/python/go/etc.
        for block in _CODE_BLOCK_RE.findall(text):
            for line in block.splitlines():
                line = line.strip()
                if re.match(r'^(npm|yarn|pnpm|python|pip|go|cargo|ruby|rails|./gradlew|mvn|docker|make)\s', line):
                    if line not in claims.start_commands:
                        claims.start_commands.append(line)

        # version mentions
        for match in _VERSION_RE.finditer(text):
            runtime = match.group(0).split()[0].lower().replace("nodejs", "node")
            version = match.group(1)
            if runtime not in claims.versions:
                claims.versions[runtime] = version

        if ".env.example" in text or ".env.sample" in text:
            claims.has_env_example_mention = True
        if "docker-compose" in text_lower or "docker compose" in text_lower:
            claims.has_docker_compose_mention = True

    return claims


# ── drift item ─────────────────────────────────────────────────────────────────

@dataclass
class DriftItem:
    category: str          # "env_vars" | "services" | "start_command" | "env_example" | "version"
    source_implies: str
    doc_says: str
    conflict: str
    proposed_patch: str
    confidence: str        # "high" | "medium" | "low"
    unchecked: list[str] = field(default_factory=list)


# ── drift computation ───────────────────────────────────────────────────────────

def compute_drift(
    env_setup: dict,
    dependencies: dict,
    doc_claims: DocClaims,
) -> list[DriftItem]:
    items: list[DriftItem] = []

    # 1. Env vars: vars in config but not mentioned in docs
    config_vars = set(env_setup.get("env_vars", []))
    if config_vars:
        undocumented = config_vars - doc_claims.env_vars
        extra_in_doc = doc_claims.env_vars - config_vars
        if undocumented:
            items.append(DriftItem(
                category="env_vars",
                source_implies=f".env.example defines: {', '.join(sorted(config_vars))}",
                doc_says=f"Doc mentions: {', '.join(sorted(doc_claims.env_vars)) or 'none'}",
                conflict=f"{len(undocumented)} var(s) in .env.example not mentioned in docs: "
                         + ", ".join(sorted(undocumented)),
                proposed_patch="Add the following to the Environment Setup section:\n"
                               + "\n".join(f"- `{v}`" for v in sorted(undocumented)),
                confidence="high",
                unchecked=[v for v in sorted(undocumented) if any(
                    kw in v for kw in ("SECRET", "KEY", "TOKEN", "PASSWORD", "PRIVATE")
                )],
            ))
        if extra_in_doc and config_vars:
            items.append(DriftItem(
                category="env_vars",
                source_implies=f".env.example does NOT define: {', '.join(sorted(extra_in_doc))}",
                doc_says=f"Doc mentions these vars: {', '.join(sorted(extra_in_doc))}",
                conflict=f"{len(extra_in_doc)} var(s) mentioned in docs but missing from .env.example",
                proposed_patch="Either add these to .env.example or remove them from the docs:\n"
                               + "\n".join(f"- `{v}`" for v in sorted(extra_in_doc)),
                confidence="medium",
                unchecked=[],
            ))
    elif doc_claims.has_env_example_mention:
        items.append(DriftItem(
            category="env_example",
            source_implies="No .env.example found anywhere in the repo",
            doc_says="Docs mention .env.example or .env.sample",
            conflict="Docs reference an env example file that does not exist",
            proposed_patch="Create a .env.example with all required variables, or update docs to reflect the correct setup method",
            confidence="high",
            unchecked=[],
        ))

    # 2. Docker Compose services: services in compose not mentioned in docs
    compose_services = set(env_setup.get("docker_compose_services", []))
    if compose_services:
        doc_service_mentions = doc_claims.services
        unmentioned = {
            s for s in compose_services
            if not any(s in mention or mention in s for mention in doc_service_mentions)
        }
        if unmentioned and doc_claims.has_docker_compose_mention:
            items.append(DriftItem(
                category="services",
                source_implies=f"docker-compose defines services: {', '.join(sorted(compose_services))}",
                doc_says=f"Docs mention services: {', '.join(sorted(doc_service_mentions)) or 'none explicitly'}",
                conflict=f"Services in compose not referenced in docs: {', '.join(sorted(unmentioned))}",
                proposed_patch="Add a Services section listing:\n"
                               + "\n".join(f"- `{s}`" for s in sorted(unmentioned)),
                confidence="medium",
                unchecked=[],
            ))
        elif not doc_claims.has_docker_compose_mention and compose_services:
            items.append(DriftItem(
                category="services",
                source_implies=f"docker-compose.yml defines {len(compose_services)} services: "
                               + ", ".join(sorted(compose_services)),
                doc_says="Docs do not mention docker-compose at all",
                conflict="Setup requires docker compose but docs don't mention it",
                proposed_patch="Add to docs: 'Start all services with `docker compose up` before running the app.'",
                confidence="high",
                unchecked=[],
            ))

    # 3. Start command drift
    if "node" in dependencies:
        scripts = dependencies["node"].get("scripts", {})
        config_commands = set()
        for cmd in ("dev", "start"):
            if cmd in scripts:
                config_commands.add(f"npm run {cmd}")

        if config_commands and doc_claims.start_commands:
            doc_npm = {c for c in doc_claims.start_commands if c.startswith("npm run")}
            missing_from_docs = config_commands - doc_npm
            if missing_from_docs:
                items.append(DriftItem(
                    category="start_command",
                    source_implies=f"package.json scripts include: {', '.join(f'`{c}`' for c in sorted(config_commands))}",
                    doc_says=f"Docs show start commands: {', '.join(f'`{c}`' for c in doc_claims.start_commands[:3])}",
                    conflict=f"Commands in package.json not shown in docs: {', '.join(sorted(missing_from_docs))}",
                    proposed_patch="Update the 'Running the Project' section to include:\n"
                                   + "\n".join(f"```\n{c}\n```" for c in sorted(missing_from_docs)),
                    confidence="medium",
                    unchecked=[],
                ))

    return items


# ── public entry point ──────────────────────────────────────────────────────────

def run_drift(repo_path: Path, env_setup: dict, dependencies: dict) -> tuple[DocClaims, list[DriftItem]]:
    doc_claims = extract_doc_claims(repo_path)
    items = compute_drift(env_setup, dependencies, doc_claims)
    return doc_claims, items
