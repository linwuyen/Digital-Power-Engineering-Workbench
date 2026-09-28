# AGENTS.md

## Repository role

`linwuyen/Digital-Power-Engineering-Workbench` is the **View / Analysis Plane** for ASR5K.

It may present, normalize, visualize, calculate, and inspect read-only engineering information. It is **not** an execution authority and must not become a third engineering source of truth.

Canonical ownership:

```text
ASR5K_AGENT
= Control / Knowledge Plane
= product intent, architecture contracts, decisions, durable status,
  source-of-truth routing, evidence interpretation rules

ASR5K_v2_28384
= Execution Plane
= exact firmware implementation, build/link inputs, repository tests,
  flash/HIL/qualification execution, artifacts and execution evidence

Digital-Power-Engineering-Workbench
= View / Analysis Plane
= presentation, visualization, reference calculators, derived analysis,
  read-only evidence views and derived snapshots
```

The checked-in routing contract is:
`engineering_data/federation/source_manifest.json`.

## Non-negotiable invariants

1. **Fail closed.** Missing, stale, mismatched, or unresolved evidence remains `UNKNOWN`, `PENDING`, `MISMATCH`, or `STALE`. Never infer `PASS`.
2. **Exact identity first.** Qualification claims must retain repository, branch/ref when known, exact SHA, evidence source, and freshness/provenance.
3. **No evidence transfer by inference.** A PASS on one SHA does not qualify another SHA, including descendants.
4. **No execution authority here.** Do not add firmware build orchestration, checkout/reset/merge automation, flashing, physical HIL execution, qualification transactions, GOLDEN promotion, or hardware actuation.
5. **No safety authority in browser/server code.** OVP, OCP, OTP, PWM Trip, interlock, emergency safe-off, actuator ownership, and deterministic fault response remain local to firmware/hardware.
6. **Do not duplicate owner truth.** Product intent comes from `ASR5K_AGENT`; implementation/execution truth comes from `ASR5K_v2_28384`. Workbench data is derived or historical unless explicitly named otherwise.
7. **Historical snapshots stay historical.** The pinned `2b72f506...` engineering dataset is reproducible reference data, not current firmware truth.
8. **Public snapshot is not LIVE.** GitHub Pages must not receive private repository credentials. A public snapshot may legitimately be `DEGRADED` / `UNKNOWN` / `STALE`.

## Digital Buck training boundary

`training/digital-buck/` is a public acquisition/training surface, isolated from ASR5K execution authority.

Preserve `docs/digital-buck-product-boundary.md`:
- public content stays limited to the approved previews and offer surface;
- paid-only labs, answer keys, full fault bank, production-authority exercises, and board-evidence workflow must not leak into the public route;
- checkout remains fail-closed when not configured;
- course completion must never be represented as production qualification or BOARD_PASS.

## Change strategy

Prefer the smallest reversible change that preserves source ownership and observability:

```text
understand owner truth
→ make one small change
→ run focused tests
→ run full regression / syntax / data-boundary checks
→ inspect evidence
→ only then merge
```

Do not perform broad refactors unless a concrete defect or ownership violation requires them. Repeated code is not automatically removable; first verify semantic role, provenance, timing relevance, safety boundary, and test coverage.

## Required verification

Before merge, run at minimum:

```bash
python -m unittest discover -s tests -v
python -m py_compile server.py workbench/*.py tools/*.py tests/*.py

python tools/validate_federation.py
python tools/traceability.py --out /tmp/traceability.json
python tools/verify_truth_drift.py \
  --snapshot engineering_data/source_truth/snapshot-2b72f506.json \
  --data-root engineering_data \
  --report /tmp/truth-drift-pinned.json

node --check static/app.js
node --check static/i18n.js
node --check static/eng/loader.js
node --check static/eng/common.js
node --check static/eng/status_console.js
node --check static/eng/data_source.js
node --check static/eng/profiles.js
node --check static/eng/control_sfra.js
node --check static/eng/system_tools.js
node --check training/digital-buck/app.js
node --check training/digital-buck/localized-app.js
node --check training/digital-buck/product-config.js
```

CI success is necessary but does not imply flash, board, HIL, protection, or production qualification.

## Stop conditions

Stop and report instead of guessing when:
- the requested change would move execution or safety authority into this repository;
- owner repositories or exact source identity required for a claim cannot be established;
- evidence is missing or belongs to a different SHA;
- a change would require weakening fail-closed semantics;
- tests reveal an ownership or truth-source conflict.

## Rollback

All Workbench changes must remain revertible without changing firmware/hardware state. Roll back the Workbench commit/PR; never compensate for a View Plane defect by mutating firmware qualification evidence or hardware state.
