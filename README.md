https://linwuyen.github.io/Digital-Power-Engineering-Workbench/

# ASR5K Engineering Console

`Digital-Power-Engineering-Workbench` is the **View / Analysis Plane** for ASR5K. Its default browser experience is now an ASR5K engineering status console: one place to see which firmware identity is being inspected, how it relates to GOLDEN, what exact-SHA evidence exists, what is still `UNKNOWN` / `PENDING`, and whether the displayed data is LIVE, SNAPSHOT, or STALE.

It does **not** become a third source of engineering truth.

```text
linwuyen/ASR5K_AGENT
= Control / Knowledge Plane
= product intent, architecture, decisions, durable status, evidence rules

linwuyen/ASR5K_v2_28384
= Execution Plane
= exact firmware, build/test/flash/HIL/qualification execution and evidence

linwuyen/Digital-Power-Engineering-Workbench
= View / Analysis Plane
= read-only status normalization, visualization, calculators and derived snapshots
```

The authority split is canonical in:

```text
engineering_data/federation/source_manifest.json
```

## What the landing page answers

The Status view is intentionally evidence-first:

- current firmware repository / branch / exact SHA;
- explicit GOLDEN SHA and release ref from the Execution Plane owner source;
- current SHA relation to GOLDEN: `MATCH`, `AHEAD`, `DIVERGED`, or `UNKNOWN`;
- Control Plane identity when available;
- separate Source / Build / Regression / Artifact / Flash / Board / HIL / Protection / Production gates;
- blockers, unknown evidence, identity mismatches, and stale inputs;
- source identity and data freshness.

The core rule is:

```text
build PASS != flash PASS != board PASS != HIL PASS != Production qualification
```

A gate is never promoted to `PASS` because a test file exists, because another SHA passed, or because a historical note says it once worked. Exact-SHA evidence does not transfer by inference.

## LIVE mode — local Python server

Use LIVE mode when the Workbench, `ASR5K_AGENT`, and `ASR5K_v2_28384` are available as local Git checkouts.

Default sibling layout:

```text
parent/
├─ ASR5K_AGENT/
├─ ASR5K_v2_28384/
└─ Digital-Power-Engineering-Workbench/
```

Start the Workbench:

```bash
python server.py
```

Then open:

```text
http://localhost:8000
```

The read-only status endpoint is:

```text
GET /api/status/summary
GET /api/status/evidence
```

The backend only performs non-mutating repository inspection. It does not checkout, reset, merge, commit, push, flash hardware, run HIL, arm qualification, or promote GOLDEN.

If the repositories are elsewhere, configure backend-only environment variables before starting the server:

```text
ASR5K_AGENT_ROOT
ASR5K_FIRMWARE_ROOT
```

Browser query parameters cannot override these filesystem roots.

## SNAPSHOT mode — GitHub Pages

GitHub Pages has no private-repository credential and must not receive one. If `/api/status/summary` is unavailable, the browser falls back to:

```text
engineering_data/status/status_snapshot.json
```

The page then identifies itself as `SNAPSHOT`; an old snapshot is shown as `STALE`. Public snapshot data is sanitized: local absolute paths, local dirty-state details, secrets, and tokens are not published.

A checked-in snapshot may legitimately show `DEGRADED` and `UNKNOWN` when the source repositories or exact evidence were unavailable at generation time. That is preferred to inventing a green status.

To explicitly regenerate the public snapshot from local owner repositories:

```bash
python tools/generate_status_snapshot.py \
  --agent-root ../ASR5K_AGENT \
  --firmware-root ../ASR5K_v2_28384
```

The generator reads owner repositories and existing evidence read-only, then writes the sanitized derived view. It does not create qualification evidence.

## Historical engineering dataset

The older `engineering_data/` snapshot remains intentionally available for reproducible engineering views. Its pinned firmware identity is:

```text
repository: linwuyen/ASR5K_v2_28384
branch:     feat/voltage-slew-runtime-complete
commit:     2b72f50648d86c11547645882248eed69f12892f
freshness:  historical_snapshot
```

That dataset is historical and cannot be presented as current firmware truth. Current implementation truth belongs to the exact Execution Plane checkout; product intent and architecture authority belong to `ASR5K_AGENT`.

## Engineering Tools

The original analysis capabilities remain available below the Status views rather than being the landing page:

- Signal Chain / ADC calculator;
- Control / Bode analysis;
- SFRA theory vs measurement comparison;
- Firmware state viewer;
- Protocol explorer;
- other derived/reference engineering views.

The mock power-control surface is retained only as a **DEMO / REFERENCE** view. Browser/network commands never own OVP, OCP, OTP, PWM Trip, interlock, emergency safe-off, or other hardware protection authority.

## Evidence boundary

Workbench output is only as strong as the named inputs behind it:

1. current explicit owner instruction;
2. `ASR5K_AGENT` approved contract / decision for product intent;
3. exact `ASR5K_v2_28384` source for implementation truth;
4. exact execution / artifact / flash / board / HIL evidence for the claim;
5. Workbench normalized status / historical snapshots for read-only presentation;
6. reference calculators and simulations.

Missing evidence is `UNKNOWN` or `PENDING`, not inferred PASS. A SHA mismatch is surfaced explicitly rather than collapsed into a generic result.

## Verification

Python 3.10+ is sufficient; the reference backend has no third-party runtime dependency.

```bash
python -m unittest discover -s tests -v
python -m py_compile server.py workbench/*.py tools/*.py tests/*.py
node --check static/app.js
node --check static/i18n.js
node --check static/eng/loader.js
node --check static/eng/common.js
node --check static/eng/status_console.js
node --check static/eng/data_source.js
node --check static/eng/profiles.js
node --check static/eng/control_sfra.js
node --check static/eng/system_tools.js
```

## Repository policy

Develop on feature branches, verify through CI, and merge through review. Keep Workbench read/analysis-focused. New production build, flash, physical HIL, artifact-capture, or qualification execution belongs in `linwuyen/ASR5K_v2_28384`, not here.
