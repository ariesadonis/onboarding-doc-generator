# Self-Hosting Setup-Risk Report: Novu vs Uptrace vs Docmost
### Onboarding risk from actually trying the first hour — not a feature list

> Most "best open-source X" listicles compare features. None tell you the thing you actually need before you adopt: **how much will this hurt to stand up, and is the pain a docs problem (fixable) or a product problem (yours forever)?**
>
> This is operational-risk scoring, not feature inventory. Each tool is graded on five things:
> 1. Time to first successful run
> 2. First broken / ambiguous step
> 3. Failure class — *docs drift · product bug · environment assumption · missing prerequisite*
> 4. Evidence
> 5. Would I adopt this for a small team?
>
> **Send me the tool you're evaluating and I'll score its onboarding risk the same way.**

---

## At a glance

| Tool | Time to first run | First broken step | Failure class | Adopt for a small team? |
|------|------------------|-------------------|---------------|------------------------|
| **Docmost** (wiki) | <1 hr (w/ docs) · 2–3 hr (repo only) | Env vars undefined if you skip the external guide | Docs drift (mitigated) + missing prerequisite | **Yes** — lowest risk |
| **Novu** (notifications) | 2–4 hr → ½ day | App silently won't connect — compose step not in README | Docs drift + environment assumption | **Qualified yes** — budget ½ day |
| **Uptrace** (OTel APM) | 3–5 hr → full day | Telemetry pipeline produces no data, no error | Docs drift + missing prerequisite | **Only with OTel/ClickHouse experience** |

---

## Novu — notification infrastructure

- **1. Time to first successful run:** 2–4 hrs for an experienced engineer; most of a day if unfamiliar with the stack.
- **2. First broken/ambiguous step:** You follow the README, skip `docker compose up`, and the app silently fails to connect — no clear error telling you 6 services need to be running.
- **3. Failure class:** **Docs drift** (the README never documents the 6-service compose: api, worker, ws, dashboard, mongodb, redis) **+ environment assumption** (`.env.example` has 88 vars; ~5 are explained — you can't tell required-for-local from deployment-only).
- **4. Evidence:** [GitHub issue #11657](https://github.com/novuhq/novu/issues/11657) — acknowledged by Novu's co-founder, triaged internally. Independent confirmation: a DevOps walkthrough notes Novu deployment "involves a massive amount of configuration values and lacks straightforward documentation."
- **5. Would I adopt for a small team?** **Qualified yes.** The software is solid; the friction is one-time and doc-shaped, not a stability risk. Budget half a day, don't schedule the eval review same-day.

## Uptrace — OpenTelemetry APM

- **1. Time to first successful run:** 3–5 hrs if you know OTel/ClickHouse; a full day or more otherwise.
- **2. First broken/ambiguous step:** You bring up a subset of services and get **no telemetry and no error** — the value is in a pipeline (vector → otelcol → clickhouse → grafana) the README never maps.
- **3. Failure class:** **Docs drift** (README has zero mention of the 9-service topology) **+ missing prerequisite** (ClickHouse must be healthy before any data flows; nothing tells you to check).
- **4. Evidence:** [GitHub issue #601](https://github.com/uptrace/uptrace/issues/601). Independent confirmation: observability comparisons note Uptrace "adds operational overhead for teams that don't want to manage a ClickHouse cluster."
- **5. Would I adopt for a small team?** **Only with existing OTel/ClickHouse experience.** The friction is real and front-loaded. For a tracing-led team that knows the stack, it's a one-time spike. For everyone else, the time-to-value is too long to evaluate casually.

## Docmost — Confluence-style wiki

- **1. Time to first successful run:** Under 1 hr following the external install guide; 2–3 hrs from the bare repo.
- **2. First broken/ambiguous step:** If you self-host straight from the cloned repo (not the website), you hit undefined env vars with no in-repo guidance.
- **3. Failure class:** **Docs drift, mitigated** (repo README documents 0 setup, but a detailed external guide at docmost.com/docs/installation covers it well) **+ missing prerequisite** (3 of 35 env vars are required for local: DATABASE_URL, PORT, REDIS_URL).
- **4. Evidence:** [GitHub issue #2310](https://github.com/docmost/docmost/issues/2310) — maintainer confirmed they prefer users follow the external docs.
- **5. Would I adopt for a small team?** **Yes — lowest risk of the three.** Only 3 services, good external docs, and the failure mode is avoidable if you read them. Fine for a same-day evaluation.

---

### How to read this
All three failures are **docs/environment-shaped, not product bugs** — meaning the friction is predictable and front-loaded, not a sign of an unstable tool. That distinction is the whole point: a tool that's hard to set up because the README is stale is a very different bet from one that's hard because it breaks after you set it up right.

*Evaluating something not on this list? Send the repo — I'll score its onboarding risk the same way.*
