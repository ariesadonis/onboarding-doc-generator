# Contributing to DevDocs

Welcome! This guide covers how we work on DevDocs (the onboarding doc generator).
The short version: **never push straight to `main` — always branch and open a
pull request.**

## Workflow

1. **Pull the latest `main`**
   ```bash
   git checkout main
   git pull origin main
   ```

2. **Create a branch** named for what you're doing:
   ```bash
   git checkout -b feat/detect-env-drift
   # or: fix/readme-parser, chore/update-deps
   ```
   Use a prefix: `feat/` (new feature), `fix/` (bug fix), `chore/` (maintenance), `docs/` (docs).

3. **Make your change, then run it locally** (see Setup below) to confirm it works.

4. **Commit** in small, clear steps:
   ```bash
   git add <files>
   git commit -m "Detect services in docker-compose missing from README"
   ```

5. **Push your branch and open a PR**
   ```bash
   git push -u origin <your-branch>
   ```
   Then open a pull request on GitHub against `main`. In the PR description, say
   what changed and how you tested it. Samveg reviews and merges — **do not merge
   your own PR.**

## Setup

DevDocs is a Python project.

```bash
python3 -m venv .venv          # create a virtual environment
source .venv/bin/activate      # activate it (macOS/Linux)
pip install -r requirements.txt
```

See the [README](README.md) for how to run the tool against a repo. Confirm your
change works on a real repo before pushing.

## Ground rules

- **One PR = one focused change.** Don't bundle unrelated fixes.
- **Don't touch unrelated code.** If you spot a separate problem, mention it in the
  PR or tell Samveg — don't fix it silently in the same branch.
- **Ask before assuming.** If a task is unclear, ask first rather than guessing.
- **Never commit secrets** — API keys, `.env` files, tokens. They stay local.
- **Keep the `.venv/` out of git** — it should already be in `.gitignore`.
