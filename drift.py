"""
Drift detection: compare what existing docs claim against what config files actually say.
Produces a structured report in the 5-point format:
  1. What source files imply (file:line)
  2. What the current doc says (file:line)
  3. Why it matters / exact conflict
  4. Proposed patch (minimal diff)
  5. Confidence + unchecked assumptions + reviewer action
"""
import re
from dataclasses import dataclass, field
from pathlib import Path

# ── helpers ────────────────────────────────────────────────────────────────────

_ENV_VAR_RE = re.compile(r'\b([A-Z][A-Z0-9_]{2,})\b')
_CODE_BLOCK_RE = re.compile(r'```[^\n]*\n(.*?)```', re.DOTALL)
_INLINE_CODE_RE = re.compile(r'`([^`]+)`')
_VERSION_RE = re.compile(r'(?:node|nodejs|npm|python|ruby|go)\s*[>=v]*\s*(\d+[\d.]*)', re.IGNORECASE)
_SERVICE_KEYWORDS = {"postgres", "postgresql", "mysql", "redis", "mongo", "mongodb",
                     "rabbitmq", "kafka", "elasticsearch", "localstack", "mailhog", "minio"}

# Vars that are almost certainly not required for local dev
_DEPLOYMENT_PATTERNS = ("SENTRY_", "CDN_", "SSL_", "CLOUDFRONT", "CLOUDFLARE",
                        "RATE_LIMITER_", "WEB_CONCURRENCY", "FORCE_HTTPS", "ENABLE_UPDATES")
_SECRET_PATTERNS = ("SECRET", "PRIVATE_KEY", "PASSWORD", "SIGNING")
_OPTIONAL_PATTERNS = ("DISCORD_", "DROPBOX_", "FIGMA_", "IFRAMELY_", "LINEAR_",
                      "NOTION_", "SLACK_", "AZURE_", "GITHUB_APP_", "GITLAB_",
                      "OIDC_", "SENDGRID_", "SMTP_")
_LOCAL_REQUIRED_PATTERNS = ("DATABASE_URL", "REDIS_URL", "PORT", "NODE_ENV",
                             "SECRET_KEY", "UTILS_SECRET", "URL", "FILE_STORAGE")

_FALSE_POSITIVES = {"HTTP", "URL", "API", "CI", "CD", "PR", "EOF",
                    "TRUE", "FALSE", "NULL", "NONE", "PATH", "HOME",
                    "USER", "SHELL", "TERM", "PWD", "IFS", "AWS", "GCP"}


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


def _find_section(text: str, section_name: str) -> tuple[int, int] | None:
    """Return (start_line, end_line) of a markdown section by heading name."""
    lines = text.splitlines()
    start = None
    for i, line in enumerate(lines):
        if re.search(rf'#+\s+{re.escape(section_name)}', line, re.IGNORECASE):
            start = i + 1
        elif start is not None and re.match(r'^#+\s', line):
            return (start, i)
    if start is not None:
        return (start, len(lines))
    return None


def _line_range_of_pattern(text: str, pattern: str) -> str:
    """Return ':start-end' line range where pattern first appears, or ''."""
    lines = text.splitlines()
    for i, line in enumerate(lines, 1):
        if pattern in line:
            return f":{i}"
    return ""


# ── env var categorization ─────────────────────────────────────────────────────

def _categorize_vars(vars: set[str]) -> dict[str, list[str]]:
    cats: dict[str, list[str]] = {
        "local_required": [],
        "optional_integrations": [],
        "deployment_only": [],
        "secrets": [],
        "unknown": [],
    }
    for v in sorted(vars):
        if any(p in v for p in _SECRET_PATTERNS):
            cats["secrets"].append(v)
        elif any(v.startswith(p) or p in v for p in _DEPLOYMENT_PATTERNS):
            cats["deployment_only"].append(v)
        elif any(v.startswith(p) for p in _OPTIONAL_PATTERNS):
            cats["optional_integrations"].append(v)
        elif any(v.startswith(p) or p == v for p in _LOCAL_REQUIRED_PATTERNS):
            cats["local_required"].append(v)
        else:
            cats["unknown"].append(v)
    return cats


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
    # file:line references for key doc locations
    setup_section_ref: str = ""
    env_section_ref: str = ""


def extract_doc_claims(repo_path: Path) -> DocClaims:
    claims = DocClaims()
    doc_files = _find_doc_files(repo_path)
    claims.source_files = [str(f.relative_to(repo_path)) for f in doc_files]

    for doc_file in doc_files:
        text = _read(doc_file)
        rel = str(doc_file.relative_to(repo_path))

        # find setup/env section line ranges
        for heading in ("setup", "getting started", "installation", "environment"):
            loc = _find_section(text, heading)
            if loc and not claims.setup_section_ref:
                claims.setup_section_ref = f"{rel}:{loc[0]+1}-{loc[1]}"

        for heading in ("environment", "env", "configuration"):
            loc = _find_section(text, heading)
            if loc and not claims.env_section_ref:
                claims.env_section_ref = f"{rel}:{loc[0]+1}-{loc[1]}"

        # env vars in code blocks and inline code
        for block in _CODE_BLOCK_RE.findall(text):
            claims.env_vars.update(_ENV_VAR_RE.findall(block))
        for inline in _INLINE_CODE_RE.findall(text):
            claims.env_vars.update(_ENV_VAR_RE.findall(inline))
        claims.env_vars = {
            v for v in claims.env_vars
            if len(v) > 3 and v not in _FALSE_POSITIVES
        }

        # services
        text_lower = text.lower()
        for svc in _SERVICE_KEYWORDS:
            if svc in text_lower:
                claims.services.add(svc)

        # start commands in code blocks
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
    category: str
    source_implies: str      # file:line + extracted fact
    doc_says: str            # file:line + current instruction/gap
    why_it_matters: str      # local setup failure? security confusion? stale command?
    proposed_patch: str      # minimal README diff
    confidence: str          # "high" | "medium" | "low"
    unchecked: list[str] = field(default_factory=list)
    reviewer_actions: list[str] = field(default_factory=lambda: [
        "Accept patch", "Mark intentional", "Map to deployment-only", "Ignore with reason"
    ])


# ── drift computation ───────────────────────────────────────────────────────────

def compute_drift(
    repo_path: Path,
    env_setup: dict,
    dependencies: dict,
    doc_claims: DocClaims,
) -> list[DriftItem]:
    items: list[DriftItem] = []

    # ── 1. Env vars ──────────────────────────────────────────────────────────
    config_vars = set(env_setup.get("env_vars", []))
    env_file_ref = ""
    # find line range of env vars in .env.example
    for env_file in repo_path.rglob(".env.example"):
        if ".git" not in env_file.parts:
            content = _read(env_file)
            lines = content.splitlines()
            first = next((i+1 for i, l in enumerate(lines) if "=" in l and not l.startswith("#")), None)
            last = next((i+1 for i, l in enumerate(reversed(lines)) if "=" in l and not l.startswith("#")), None)
            if first and last:
                env_file_ref = f".env.example:{first}-{len(lines)-last+1}"
            else:
                env_file_ref = str(env_file.relative_to(repo_path))
            break

    if config_vars:
        undocumented = config_vars - doc_claims.env_vars
        if undocumented:
            cats = _categorize_vars(undocumented)
            local_req = cats["local_required"]
            secrets = cats["secrets"]
            optional = cats["optional_integrations"]
            deploy = cats["deployment_only"]
            unknown = cats["unknown"]

            source_ref = env_file_ref or ".env.example"
            doc_ref = doc_claims.env_section_ref or doc_claims.setup_section_ref or (
                doc_claims.source_files[0] if doc_claims.source_files else "README.md"
            )

            # Only flag local_required + unknown as high-confidence drift
            actionable = local_req + unknown
            if actionable:
                patch_lines = []
                if local_req:
                    patch_lines.append("**Required for local dev** — add to Environment Setup section:")
                    patch_lines += [f"- `{v}`" for v in local_req]
                if unknown:
                    patch_lines.append("\n**Unclassified** — verify with team whether required locally:")
                    patch_lines += [f"- `{v}`" for v in unknown]
                if optional:
                    patch_lines.append(f"\n**Optional integrations** (skip if not using): {', '.join(f'`{v}`' for v in optional)}")
                if deploy:
                    patch_lines.append(f"\n**Deployment-only** (not needed locally): {', '.join(f'`{v}`' for v in deploy)}")

                items.append(DriftItem(
                    category="env_vars",
                    source_implies=f"`{source_ref}` defines {len(config_vars)} vars. "
                                   f"Local-required: {', '.join(f'`{v}`' for v in local_req) or 'none detected'}. "
                                   f"Secrets: {len(secrets)}. Optional integrations: {len(optional)}. "
                                   f"Deployment-only: {len(deploy)}. Unclassified: {len(unknown)}.",
                    doc_says=f"`{doc_ref}` mentions {len(doc_claims.env_vars)} var(s): "
                             + (', '.join(f'`{v}`' for v in sorted(doc_claims.env_vars)) or "none"),
                    why_it_matters=f"{len(actionable)} var(s) likely needed for local setup are undocumented. "
                                   "A new engineer cloning this repo will hit failures without knowing which vars are required.",
                    proposed_patch="\n".join(patch_lines),
                    confidence="high" if local_req else "medium",
                    unchecked=[f"`{v}` — may be deployment-only" for v in unknown[:4]],
                ))

    elif doc_claims.has_env_example_mention:
        items.append(DriftItem(
            category="env_example",
            source_implies="No .env.example found anywhere in the repo",
            doc_says=f"`{doc_claims.source_files[0] if doc_claims.source_files else 'README.md'}` mentions .env.example",
            why_it_matters="New engineer will follow doc instructions and hit a missing file error immediately.",
            proposed_patch="Create a .env.example listing all required variables (values can be blank or example strings).",
            confidence="high",
            unchecked=[],
        ))

    # ── 2. Docker Compose services ────────────────────────────────────────────
    compose_services = set(env_setup.get("docker_compose_services", []))
    compose_file = next(
        (str(p.relative_to(repo_path)) for p in [repo_path / "docker-compose.yml", repo_path / "docker-compose.yaml"] if p.exists()),
        "docker-compose.yml"
    )
    if compose_services and not doc_claims.has_docker_compose_mention:
        doc_ref = doc_claims.setup_section_ref or (doc_claims.source_files[0] if doc_claims.source_files else "README.md")
        items.append(DriftItem(
            category="services",
            source_implies=f"`{compose_file}` defines {len(compose_services)} service(s): "
                           + ", ".join(f"`{s}`" for s in sorted(compose_services)),
            doc_says=f"`{doc_ref}` — no mention of docker-compose or local service startup",
            why_it_matters="Engineer clones repo, skips `docker compose up`, app fails to connect to "
                           + " and ".join(sorted(compose_services)[:2])
                           + ". This is a concrete onboarding break, not a cosmetic gap.",
            proposed_patch=f"Add to the Setup section in `{doc_claims.source_files[0] if doc_claims.source_files else 'README.md'}`:\n\n"
                           "```\n# Start required services\ndocker compose up -d\n```\n\n"
                           f"Services started: {', '.join(f'`{s}`' for s in sorted(compose_services))}",
            confidence="high",
            unchecked=[],
        ))

    # ── 3. Start command ──────────────────────────────────────────────────────
    if "node" in dependencies:
        scripts = dependencies["node"].get("scripts", {})
        pkg_file = dependencies["node"].get("source_file", "package.json")
        config_commands = {f"npm run {cmd}" for cmd in ("dev", "start") if cmd in scripts}

        if config_commands and doc_claims.start_commands:
            doc_npm = {c for c in doc_claims.start_commands if c.startswith("npm run")}
            missing = config_commands - doc_npm
            if missing:
                doc_ref = doc_claims.setup_section_ref or (doc_claims.source_files[0] if doc_claims.source_files else "README.md")
                items.append(DriftItem(
                    category="start_command",
                    source_implies=f"`{pkg_file}` scripts define: {', '.join(f'`{c}`' for c in sorted(config_commands))}",
                    doc_says=f"`{doc_ref}` instructs: {', '.join(f'`{c}`' for c in doc_claims.start_commands[:3])}",
                    why_it_matters="Engineer runs documented command, which may be a wrapper (make/yarn) "
                                   "that invokes npm internally — or may be stale.",
                    proposed_patch="Verify which command is canonical, then update the Running section:\n"
                                   + "\n".join(f"```\n{c}\n```" for c in sorted(missing)),
                    confidence="medium",
                    unchecked=["`make`/`yarn` wrappers may be the intended entry point — confirm with team before patching"],
                ))

    return items


# ── public entry point ──────────────────────────────────────────────────────────

def run_drift(repo_path: Path, env_setup: dict, dependencies: dict) -> tuple[DocClaims, list[DriftItem]]:
    doc_claims = extract_doc_claims(repo_path)
    items = compute_drift(repo_path, env_setup, dependencies, doc_claims)
    return doc_claims, items
