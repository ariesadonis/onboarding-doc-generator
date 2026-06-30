# Dependency Onboarding Risk Memos

> Consumer-side artifact format (per Interstellar, 2026-06-30): aimed at the **engineering manager / platform team evaluating an OSS dependency**, NOT the maintainer.
> Success signal to test for: *"I wish we'd had this before we adopted X."*
>
> Each memo classifies setup pain as **doc-drift (fixable)** vs **product-bug (not our wedge)**, estimates **time-to-first-success**, and gives a **recommended safe path**.

---

## Dependency Onboarding Risk Memo — Novu (self-hosted)
*For an engineering manager evaluating Novu (notifications infra) before adoption*

**TL;DR risk rating: MEDIUM-HIGH onboarding friction.** A capable engineer will get it running, but plan for **half a day of trial-and-error**, not the "clone and go" the README implies.

1. **Docs promise vs. setup reality** — README implies a simple start. Reality: `docker-compose.yml` brings up **6 interdependent services** (api, worker, ws, dashboard, mongodb, redis). Skip the compose step and the app silently fails to connect.
2. **Doc-drift vs. product-bug** — This is **doc drift, not a product bug**. The software works; the docs never caught up to the config. Predictable, not a landmine. Evidence: GitHub issue #11657, acknowledged by Novu's co-founder, triaged internally to Linear.
3. **Time-to-first-success** — Experienced eng: **2–4 hrs.** Unfamiliar with the stack: **most of a day.** Main time-sink is env config.
4. **Real failure point: env config** — `.env.example` defines **88 variables**; docs meaningfully explain **~5**. The rest are unclassified — an adopter can't tell required-for-local vs deployment-only vs optional. This is where the half-day goes.
5. **Recommended safe path** — (a) `docker compose up -d` first, don't skip. (b) Treat only the local-required subset as needed for eval; ignore S3/integration vars. (c) Budget a half-day; don't schedule the eval review same-day.

---

## Dependency Onboarding Risk Memo — Uptrace (self-hosted)
*For a platform team evaluating Uptrace (OpenTelemetry APM / observability) before adoption*

**TL;DR risk rating: HIGH onboarding friction.** The most service-heavy of the three. Expect a **full day** to a confident first run unless someone already knows the OTel stack.

1. **Docs promise vs. setup reality** — README has **zero mention** of the local service topology. Reality: the compose stack runs **9 services** (alertmanager, clickhouse, grafana, keycloak, mailpit, otelcol, postgres, prometheus, vector). Several depend on each other and on correct config wiring (ClickHouse + otelcol especially).
2. **Doc-drift vs. product-bug** — **Doc drift.** The components are standard and work; the gap is that the README never documents which services must come up, in what order, or how they connect. Evidence: GitHub issue #601.
3. **Time-to-first-success** — Eng familiar with OTel/ClickHouse: **3–5 hrs.** Everyone else: **a full day or more**, mostly spent reverse-engineering service dependencies.
4. **Real failure point: service topology** — Unlike a typical app, the value is in the pipeline (vector → otelcol → clickhouse → grafana). Bring up the wrong subset and you get no data with no obvious error. The README gives you no map.
5. **Recommended safe path** — (a) Bring up the full compose stack, not a subset. (b) Verify ClickHouse is healthy before expecting any telemetry. (c) Budget a full day for a first confident run; treat it as a spike, not a quick eval.

---

## Dependency Onboarding Risk Memo — Docmost (self-hosted)
*For an engineering manager evaluating Docmost (Confluence-style wiki) before adoption*

**TL;DR risk rating: LOW-MEDIUM onboarding friction.** The lightest of the three, and notably the one with the best external docs — included here precisely to show the classification isn't crying wolf.

1. **Docs promise vs. setup reality** — The repo README itself documents **0** of the setup, but Docmost maintains a **detailed external install guide** (docmost.com/docs/installation) that covers it well. The drift is **repo-local only**: someone self-hosting straight from the cloned repo (not the website) still hits gaps. `docker-compose.yml` runs **3 services** (db, docmost, redis).
2. **Doc-drift vs. product-bug** — **Doc drift, and partially mitigated.** Because good external docs exist, the practical risk is lower than the repo alone suggests. Evidence: GitHub issue #2310; maintainer confirmed they prefer users follow the external docs.
3. **Time-to-first-success** — Following the external guide: **under 1 hr.** From the repo alone: **2–3 hrs**, mostly env config.
4. **Real failure point: env config (if repo-only)** — `.env.example` defines **35 vars**; **3 are required for local** (DATABASE_URL, PORT, REDIS_URL), 21 unclassified, the rest secrets/optional. Trivial *if* you read the external docs; a time-sink if you don't.
5. **Recommended safe path** — (a) Use the external install guide, not the bare repo. (b) Set the 3 required vars; ignore S3/optional integrations for eval. (c) Lowest-risk adoption of the three — fine for a same-day eval.

---

## Cross-repo comparison (the part an evaluator actually wants)

| Dependency | Risk | Services | Time-to-first-success | Pain type |
|-----------|------|----------|----------------------|-----------|
| Docmost | LOW-MED | 3 | <1 hr (w/ docs) | Doc drift, mitigated |
| Novu | MED-HIGH | 6 | 2–4 hrs → ½ day | Doc drift (env config) |
| Uptrace | HIGH | 9 | 3–5 hrs → full day | Doc drift (service topology) |

**How to read this:** all three are doc-drift, not product-bug — meaning the friction is predictable and front-loaded, not a sign of an unstable tool. If you must adopt one this week with the least eval risk, Docmost. If you're standing up observability and have OTel experience, Uptrace's friction is one-time. Novu sits in between.
