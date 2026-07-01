# Docmost vs Outline vs BookStack: First-Hour Setup Risk Notes

*Self-hosting one of these wikis? Here's what actually happens in the first hour — graded on operational risk, not features. I set each one up and recorded where setup breaks, how long it takes, and whether the pain is a docs problem (fixable) or something you'll own forever.*

> Every "best open-source wiki" listicle compares features. None answer the question you have before you adopt: **how much will this hurt to stand up, and why?** This grades the three most-compared self-hosted wikis on the thing feature tables skip — first-hour setup risk.

---

## At a glance

| | **Docmost** | **BookStack** | **Outline** |
|---|---|---|---|
| Time to first successful run | **<1 hr** (with docs) | ~2 hrs | **Half a day+** |
| First thing that breaks | Env vars if you skip the external guide | App won't boot until you generate an app key | Won't boot at all without external auth + storage configured |
| Failure class | Docs drift (mitigated) | Docs drift + missing prerequisite | **Missing prerequisite + environment assumption** |
| Config surface | 35 env vars (3 required) | 441-line complete env | 87 env vars |
| Services | 3 | 4 (dev) | 3 |
| Adopt for a small team? | **Yes** — lowest risk | **Yes**, if you're OK with PHP/Laravel | **Only if** you'll wire up OAuth + S3 first |

**Short version:** Docmost is the easiest to stand up, BookStack is a straightforward PHP app once you know the app-key step, and Outline is the most powerful but has a hard prerequisite wall that catches people evaluating it casually.

---

## Docmost — lowest setup risk

- **Time to first successful run:** Under an hour following the [official install guide](https://docmost.com/docs/installation); 2–3 hrs from the bare repo.
- **First broken / ambiguous step:** If you self-host straight from the cloned repo instead of the website, you hit undefined environment variables with no in-repo guidance.
- **Failure class:** **Docs drift, mitigated.** The repo README documents zero setup, but the external guide covers it well. Plus one *missing prerequisite* — 3 of the 35 env vars are required for local (`DATABASE_URL`, `PORT`, `REDIS_URL`).
- **Evidence:** [GitHub issue #2310](https://github.com/docmost/docmost/issues/2310) — maintainer confirmed they prefer users follow the external docs over the repo.
- **Would I adopt for a small team?** **Yes — lowest risk of the three.** 3 services, good docs, avoidable failure mode. Fine for a same-day evaluation.

## BookStack — predictable, with one gotcha

- **Time to first successful run:** ~2 hrs. Slower if you don't already run PHP/Laravel apps.
- **First broken / ambiguous step:** The app won't boot until you generate an application key (`APP_KEY`) — a Laravel step that's easy to miss coming from a Node/Go background. Most people self-host via a community docker image rather than the repo's dev compose, which adds a "which image is canonical?" moment.
- **Failure class:** **Docs drift** (repo README barely mentions the 4-service dev compose: app, db, node, mailhog) **+ missing prerequisite** (the app-key step). The full config surface is a 441-line `.env.example.complete` — most of it optional, but nothing tells you that up front.
- **Evidence:** BookStack's primary repo now mirrors from Codeberg; self-hosters largely rely on community-maintained docker images, so the "official path" is ambiguous by default.
- **Would I adopt for a small team?** **Yes**, if you're comfortable with PHP/Laravel. The friction is one-time and well-trodden; the gotcha is the app key, not stability.

## Outline — most powerful, hardest first hour

- **Time to first successful run:** Half a day or more. This is the one people underestimate.
- **First broken / ambiguous step:** It **won't start at all** until you've configured an external authentication provider (Slack/Google/OIDC) *and* S3-compatible file storage. There's no "just run it locally with defaults" path — the hard requirement isn't obvious until first boot fails.
- **Failure class:** **Missing prerequisite** (auth provider + storage are mandatory, not optional) **+ environment assumption** (87 env vars in the sample, and you can't tell which unlock the mandatory path). This is by design, not a bug — but it's the design that eats your afternoon.
- **Evidence:** [outline/outline](https://github.com/outline/outline) — recent setup issues (e.g. CSRF/config errors on fresh instances) trace back to environment and prerequisite configuration, not product defects.
- **Would I adopt for a small team?** **Only if** you're ready to stand up OAuth and object storage as part of setup. If you want a wiki running this afternoon, this isn't it. If you want the most capable option and can invest the first day, it's worth it.

---

### How to read this

All three failures are **docs- or environment-shaped, not product bugs.** That's the distinction that matters: a tool that's hard to set up because a step is undocumented is a very different bet from one that's hard because it breaks after you set it up right. None of these three are unstable — they just front-load different amounts of setup tax.

If you want the least setup risk: **Docmost.** If you're a PHP shop or want the most mature option: **BookStack.** If you want the most capable wiki and can spend the first day wiring up auth and storage: **Outline.**

---

*Evaluating a tool that's not on this list? Send me the repo and I'll score its first-hour setup risk the same way — time to first run, where it breaks, and whether the pain is docs or product.*
