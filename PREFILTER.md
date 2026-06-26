# DevDocs Repo Prefilter — 5-Point Scoring Table

Score each repo 0/1 per point. Only run full drift scan at **4+**, unless there's an unusually obvious activation bug.

## Points

**1. Commercial ownership**
Pricing/cloud page, company domain, sponsored/open-core posture, or obvious business behind the repo.

**2. Setup-state complexity**
8+ services, multiple compose files, required external services, migrations, queues/workers, or env bootstrap scripts.

**3. README mismatch**
Quickstart skips compose/services/env entirely, or describes a path that cannot create the running system implied by the repo.

**4. Recent setup pain**
Issues/discussions in the last 90 days mention: cannot run, docker, env, postgres, redis, migration, quickstart, localhost, setup failed, docs outdated.

**5. Human owner reachable**
Founder/core maintainer/DevRel recently commits, replies to issues, writes release notes, or answers setup questions publicly.

## Scoring rules

| Score | Action |
|-------|--------|
| 5 | Scan + outreach if HIGH finding exists |
| 4 | Scan, unless missing ownership or pain signal |
| 3 | Only scan if README mismatch is visually obvious |
| 0–2 | Skip |

## Negative override

If docs already have a detailed local-dev guide naming every service, env var, and migration step — **skip even if compose is huge**. This avoids PostHog/Supabase-style false positives.

## Founder/DevRel signal — check order

1. Commit authors / GitHub activity first: repeated commits from founder or core maintainer in last 30–90 days, especially around docs, setup, releases, and issue replies.
2. DevRel / public-facing activity second: blog posts, changelogs, launch posts, docs videos, conference talks, repo discussions, or someone from the company answering setup questions in public.

- Strong: founder/maintainer commits + issue replies + release notes in last 60 days
- Medium: engineering team active, but no public-facing docs/marketing signal
- Weak: company account only, no clear human owner

## Outreach rule

Never mention the score in outreach. Only expose the concrete activation leak:
> "README says X, compose/runtime requires Y, likely first-run failure is Z."
