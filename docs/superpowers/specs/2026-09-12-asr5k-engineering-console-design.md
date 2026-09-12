# ASR5K Engineering Console Design

Date: 2026-09-12
Status: Approved design baseline
Repository: `linwuyen/Digital-Power-Engineering-Workbench`
Target branch: `design/asr5k-engineering-console`

## 1. Purpose

Refocus Digital Power Engineering Workbench from a broad digital-power toolbox into the ASR5K engineering status entry point.

The primary question the application must answer is:

> What ASR5K version is current, what evidence exists for that exact identity, what is still unknown, and can the displayed state be trusted?

The existing calculators and analysis tools remain available, but they move behind an `Engineering Tools` section. They are no longer the default landing experience.

## 2. System role and authority boundary

The three repositories retain their existing authority split:

- `linwuyen/ASR5K_AGENT` is the Control / Knowledge Plane for product intent, architecture contracts, decisions, current durable status, routing, and evidence interpretation rules.
- `linwuyen/ASR5K_v2_28384` is the Execution Plane for exact implementation truth, builds, artifacts, flash, board/HIL execution, and qualification evidence.
- `linwuyen/Digital-Power-Engineering-Workbench` is the View / Analysis Plane. It normalizes and presents status but never becomes the source of product truth.

A Workbench status result is never stronger than its named input identities and evidence.

Exact-SHA evidence never transfers to another SHA by inference.

## 3. Goals

V1 must provide a single-page engineering status view with these capabilities:

1. Show current product baseline identity.
2. Show current firmware identity and its relation to the golden baseline.
3. Show Control Plane identity when available.
4. Show exact qualification/evidence state by gate rather than one generic PASS indicator.
5. Show blockers, pending items, unknowns, stale data, and identity mismatches prominently.
6. Show freshness and provenance for every displayed status set.
7. Support two explicit operating modes:
   - local `LIVE` mode from read-only sibling repository inspection;
   - public/static `SNAPSHOT` mode from sanitized committed data.
8. Fail closed when authority, identity, evidence, or freshness cannot be established.
9. Keep all existing engineering calculators under a secondary `Engineering Tools` navigation group.

## 4. Non-goals

V1 does not:

- control physical hardware;
- replace `ASR5K_AGENT` governance or current status;
- replace `ASR5K_v2_28384` source, build, HIL, or qualification evidence;
- infer Production qualification from build success;
- expose GitHub credentials, private repository tokens, or private repository contents to GitHub Pages;
- make browser/network availability part of protection authority;
- automatically promote a firmware SHA to GOLDEN;
- mutate the Agent or firmware repositories;
- redesign the existing control-theory or signal-chain calculators beyond moving them into the tools section.

## 5. Recommended architecture

Use a hybrid architecture with one normalized status model and two adapters.

```text
                   ASR5K Engineering Console
                            |
                    Normalized Status Model
                    /                     \
                   /                       \
          LIVE adapter                 SNAPSHOT adapter
          local server                  GitHub Pages
              |                              |
      read-only local repos        sanitized engineering_data
              |
      ASR5K_AGENT + ASR5K_v2_28384
```

The browser renders the same normalized model in both modes. It must not implement separate status semantics for local and static operation.

## 6. Operating modes

### 6.1 LIVE mode

LIVE mode is available only through the local Python server.

Default sibling paths:

```text
../ASR5K_AGENT
../ASR5K_v2_28384
```

Optional environment overrides may provide alternate absolute paths.

The local backend performs read-only inspection only. Allowed operations include:

- read files;
- run non-mutating git queries such as `rev-parse`, `branch --show-current`, `status --short`, `log`, and tag/ref resolution;
- normalize evidence already present in the repositories.

The backend must not run merge, rebase, reset, checkout, clean, stash, commit, push, flash, HIL, or other state-changing commands merely to build the dashboard.

If a required repository is missing, unreadable, or not a Git checkout, LIVE mode remains available but affected fields become `UNKNOWN` and the overall health becomes degraded. It must not silently substitute a historical snapshot and label the result LIVE.

### 6.2 SNAPSHOT mode

GitHub Pages uses committed sanitized data under `engineering_data/`.

The public site must never receive a GitHub private-repository token in browser JavaScript.

Snapshot rendering must clearly identify:

- source repository names;
- source SHAs where available;
- generation timestamp;
- snapshot freshness state;
- that the data is not live;
- any fields that were omitted or could not be verified.

A snapshot may be useful for navigation and review but cannot claim current Production truth unless the snapshot itself contains exact source identity and exact evidence for that claim.

## 7. Normalized status model

Introduce a single normalized model for the UI. The exact file/module names may be refined during implementation, but the semantic contract is fixed.

Example shape:

```json
{
  "schema_version": "1.0",
  "mode": "LIVE",
  "generated_at": "2026-09-12T18:30:00+08:00",
  "health": "OK",
  "control_plane": {
    "repository": "linwuyen/ASR5K_AGENT",
    "sha": "...",
    "branch": "main",
    "status": "CURRENT"
  },
  "execution_plane": {
    "repository": "linwuyen/ASR5K_v2_28384",
    "sha": "...",
    "branch": "main",
    "dirty": false
  },
  "product_baseline": {
    "golden_sha": "...",
    "release_ref": "...",
    "source": "CURRENT_PRODUCT_BASELINE.md"
  },
  "identity": {
    "relation_to_golden": "MATCH",
    "evidence_sha_match": true,
    "control_plane_revision_known": true
  },
  "qualification": [
    {"gate": "source", "status": "PASS", "sha": "...", "evidence": "..."},
    {"gate": "build", "status": "PASS", "sha": "...", "evidence": "..."},
    {"gate": "regression", "status": "PASS", "sha": "...", "evidence": "..."},
    {"gate": "artifact", "status": "PASS", "sha": "...", "evidence": "..."},
    {"gate": "flash", "status": "PASS", "sha": "...", "evidence": "..."},
    {"gate": "board", "status": "PASS", "sha": "...", "evidence": "..."},
    {"gate": "hil", "status": "PASS", "sha": "...", "evidence": "..."},
    {"gate": "protection", "status": "PASS", "sha": "...", "evidence": "..."},
    {"gate": "production", "status": "GOLDEN", "sha": "...", "evidence": "..."}
  ],
  "blockers": [],
  "freshness": {
    "status": "LIVE",
    "age_seconds": 2,
    "sources": []
  }
}
```

This is a presentation contract, not a new source of truth.

## 8. Status vocabulary

Use explicit, evidence-typed states. Avoid ambiguous green/red labels without semantics.

Allowed gate states for V1:

- `PASS`
- `FAIL`
- `PENDING`
- `UNKNOWN`
- `NOT_RUN`
- `NOT_REQUIRED`
- `STALE`
- `MISMATCH`
- `GOLDEN` for the production gate only

Rules:

- `PASS` requires explicit evidence for the named SHA.
- `GOLDEN` requires an explicit product-baseline source and matching exact identity.
- `UNKNOWN` is preferred over guessing.
- `STALE` means the data may once have been valid but its freshness policy is exceeded.
- `MISMATCH` means identities are known and do not agree.
- absence of evidence is never converted to PASS.

## 9. Product baseline derivation

The dashboard must resolve the product baseline from the Execution Plane owner source, currently `CURRENT_PRODUCT_BASELINE.md`, rather than hard-coding a SHA into frontend JavaScript.

The current example baseline is `c31ecc57a54f9f84874af40234907be357638ebe`, but the implementation must treat that as data, not code.

The Overview displays the relationship between current firmware identity and GOLDEN:

- `MATCH` — exact current SHA equals GOLDEN;
- `AHEAD` — current history contains GOLDEN but current SHA differs;
- `DIVERGED` — current SHA is not a descendant/equivalent relation that can safely be described as ahead;
- `UNKNOWN` — relationship cannot be established.

`AHEAD` does not mean Production-qualified.

## 10. Qualification model

V1 qualification lanes are:

1. Source identity
2. CPU1/build evidence
3. Regression
4. Artifact identity
5. Flash
6. Board validation
7. HIL
8. Protection-critical validation
9. Production baseline status

If CPU2 or M0 evidence is required by the current controlling contract, those may appear as additional detailed rows, but the top-level UI remains compact.

The dashboard must preserve the existing rule:

```text
build PASS != flash PASS != board PASS != Production qualification
```

A test file existing in a repository is evidence that test coverage exists, not evidence that the test passed for the current SHA.

## 11. Evidence drill-down

Every status that is stronger than `UNKNOWN` should expose its provenance where practical.

For each row the user should be able to inspect:

- claimed gate;
- status;
- firmware SHA;
- Agent SHA or controlling contract identity when relevant;
- evidence path/reference;
- timestamp if available;
- evidence type;
- explanatory note.

The UI must make SHA mismatches visible instead of collapsing them into a generic failure.

## 12. Blocker derivation

The dashboard derives a compact blocker list from normalized status. A blocker is not simply any non-PASS row.

V1 blocker categories:

- `PRODUCTION_BLOCKER`
- `FIRMWARE_BLOCKER`
- `QUALIFICATION_PENDING`
- `IDENTITY_MISMATCH`
- `STALE_SOURCE`
- `UNKNOWN_EVIDENCE`

The source record for each blocker must be visible.

Unknown data should be surfaced separately from proven failures. Example:

```text
FAIL: CPU1 exact-head build failed
UNKNOWN: board evidence not found
PENDING: HIL has not been executed
```

## 13. Freshness and trust

Freshness is a first-class part of the status model.

### LIVE

LIVE indicates that the local server queried its configured sources during the current request/session. It does not imply that every engineering gate passed.

### SNAPSHOT

SNAPSHOT must show its generation timestamp and source identities.

### STALE

The implementation defines a configurable snapshot freshness threshold. When exceeded, the top status changes to `STALE` even if historical qualification rows contain PASS.

No historical snapshot may be visually presented as current live truth.

## 14. Fail-closed rules

The Console must fail closed in these cases:

- product baseline cannot be resolved;
- firmware SHA cannot be resolved;
- evidence references a different SHA;
- snapshot component baselines disagree;
- Control Plane identity required by evidence is unresolved;
- evidence format is malformed;
- a source path escapes its configured repository root;
- a public snapshot claims authority stronger than the source manifest allows.

Fail closed means:

- do not invent a value;
- do not preserve a stale green badge without a stale warning;
- display `UNKNOWN`, `MISMATCH`, or `STALE` as appropriate;
- retain the last readable evidence only as historical context, explicitly labeled historical.

## 15. Local API

Add a read-only status endpoint to the Python backend:

```text
GET /api/status/summary
```

It returns the normalized status model.

Optional detailed endpoint:

```text
GET /api/status/evidence
```

The summary endpoint must be sufficient to render the landing page. Detailed evidence may be loaded on demand.

No write endpoints are introduced for ASR5K status in V1.

## 16. Snapshot data

Add a normalized public snapshot under a dedicated path such as:

```text
engineering_data/status/status_snapshot.json
```

It is derived from existing `engineering_data/federation/source_manifest.json`, verification data, and intentionally published status inputs.

The existing `engineering_data` directory remains a derived cache. It does not become authoritative because the new dashboard consumes it.

## 17. User interface information architecture

Primary navigation becomes:

```text
ASR5K Status
  Overview
  Qualification
  Evidence
  Changes

Engineering Tools
  Signal Chain
  Control / Bode
  SFRA Compare
  State Viewer
  Protocol Explorer
```

The existing mock remote-control surface is removed from primary navigation. If retained for reference, it lives under a clearly labeled demo/tools area and must not look like a production control surface.

## 18. Overview page

The landing page contains five sections.

### 18.1 Product Baseline

Show:

- GOLDEN SHA;
- release ref;
- current firmware SHA;
- current branch;
- relation to GOLDEN;
- Control Plane SHA when available.

### 18.2 Qualification Matrix

Show compact gate cards/rows for source, build, regression, artifact, flash, board, HIL, protection, and Production.

### 18.3 Current Engineering State

Show:

- repository/branch;
- exact SHA;
- working-tree dirty state in LIVE mode;
- last known good baseline;
- blocker count;
- unknown evidence count.

Dirty state is informational and must not be interpreted as qualification failure by itself.

### 18.4 Source Identity

Show named source repositories and exact identities used to derive the current display.

### 18.5 Data Health

Show:

- LIVE / SNAPSHOT / STALE;
- generated/queried time;
- age;
- source availability;
- identity consistency.

## 19. Changes view

V1 Changes is intentionally small.

It shows only identity-level relationships useful for status review:

- current SHA vs GOLDEN SHA;
- branch/ref names;
- ahead/diverged/unknown relationship when available;
- link/reference information for the source commit if safe to publish.

It is not a general Git diff browser in V1.

## 20. Existing tools migration

Existing tool logic is retained where it is useful:

- signal-chain calculator;
- control/Bode analysis;
- SFRA compare;
- state viewer;
- protocol explorer.

These modules move behind `Engineering Tools` and retain their evidence-boundary banners.

Generic reference models remain clearly separated from ASR5K production truth.

No calculator result is promoted into qualification evidence merely because it was produced by the Workbench.

## 21. Security

Hard requirements:

- no private GitHub token in static/browser code;
- no arbitrary filesystem path supplied by browser requests;
- local repo paths are backend configuration only;
- normalize and validate repository roots before reading files;
- status APIs are read-only;
- do not expose unnecessary private file contents in public snapshots;
- public snapshot generation must be explicit and sanitized;
- browser commands never gain firmware or hardware protection authority.

## 22. Error handling

The UI must distinguish:

- source unavailable;
- source malformed;
- source stale;
- identity mismatch;
- evidence absent;
- evidence failure;
- internal rendering/API error.

A generic red `ERROR` is insufficient when a more precise state can be shown.

If the local status endpoint is unavailable, the browser may offer the committed snapshot, but the mode must visibly change to `SNAPSHOT`; it must never present fallback data as LIVE.

## 23. Testing strategy

### Unit tests

Test normalization and policy decisions independently from UI rendering:

- parse product baseline;
- resolve git identity;
- derive relation to GOLDEN;
- normalize gate states;
- reject SHA-mismatched evidence;
- derive blockers;
- freshness classification;
- malformed/missing source behavior;
- repository-root path validation.

### API tests

Test `/api/status/summary` for:

- complete LIVE sources;
- missing Agent checkout;
- missing firmware checkout;
- dirty firmware tree;
- baseline mismatch;
- missing evidence;
- stale snapshot fallback behavior.

### Frontend tests

At minimum verify:

- Overview renders normalized model;
- LIVE/SNAPSHOT/STALE labels cannot be confused;
- PASS/GOLDEN is not shown for UNKNOWN or mismatched evidence;
- blocker rows expose provenance;
- existing engineering tools remain reachable.

### Regression checks

Retain existing Python and JavaScript syntax/unit checks. The refactor must not silently break current calculator modules.

## 24. Migration sequence

Implementation should be staged so each step remains usable and reversible:

1. Add normalized status model and tests without changing the default UI.
2. Add local read-only status adapter and API.
3. Add sanitized snapshot adapter using the same model.
4. Add new Status UI as a separate module/page and test it.
5. Make Status the default landing page.
6. Move existing calculators under `Engineering Tools` without deleting their logic.
7. Demote the mock remote-control page from primary navigation.
8. Update README and status documentation.

At every step, existing tests should remain runnable and failures must be attributable to the staged change.

## 25. Acceptance criteria

V1 is complete only when all of the following are true:

1. Opening the local app immediately shows ASR5K status rather than a calculator.
2. The page identifies whether it is LIVE, SNAPSHOT, or STALE.
3. It shows current firmware SHA, GOLDEN SHA, and their relationship.
4. It shows Agent identity when available.
5. It shows qualification gates separately for build, regression, artifact, flash, board, HIL, protection, and Production.
6. No gate can display PASS without exact supporting evidence.
7. Evidence for a different SHA produces MISMATCH, not PASS.
8. Missing evidence produces UNKNOWN/PENDING, not an inferred result.
9. Blockers and unknowns are visible on the landing page.
10. Public GitHub Pages requires no private GitHub token.
11. Existing Signal Chain, Control/Bode, SFRA, State, and Protocol tools remain accessible under Engineering Tools.
12. Workbench remains a View / Analysis Plane and never claims authority over Agent or firmware truth.

## 26. Implementation boundary

The first implementation should remain focused on status visibility and trust. Do not add deployment control, firmware flashing, hardware actuation, automatic baseline promotion, or a general project-management system as part of this work.

The value of V1 is that one page reliably answers:

> What is running, what is verified, what is not verified, and exactly which identities support those statements?
