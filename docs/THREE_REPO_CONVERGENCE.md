# ASR5K Three-Repository Convergence

## Result

The ASR5K ecosystem uses one owner per responsibility class:

```text
ASR5K_AGENT
= Control / Knowledge Plane

ASR5K_v2_28384
= Execution Plane

Digital-Power-Engineering-Workbench
= View / Analysis Plane
```

Workbench is intentionally not a third source of current product, implementation, or qualification truth.

## Authority map

| Question | Authoritative owner | Workbench role |
|---|---|---|
| What should the product / architecture do? | `ASR5K_AGENT` ACTIVE contract / decision | render / link / explain |
| What does this exact firmware state do? | exact `ASR5K_v2_28384` source | normalize / visualize |
| Was this exact state built / flashed / measured / qualified? | execution-plane exact evidence + hardware evidence | browse / derive status |
| How do values, state, protocol, control or evidence relate? | source identities above | calculate / compare / visualize |

## Workbench data classification

`engineering_data/` remains useful, but its ASR5K content is a derived snapshot/cache for rendering and analysis. It cannot override the owner repositories.

The existing pinned ASR5K dataset at `2b72f50648d86c11547645882248eed69f12892f` is explicitly historical. Current firmware identity must be re-queried from `linwuyen/ASR5K_v2_28384` before making current-state claims.

Start with:

```text
engineering_data/federation/source_manifest.json
engineering_data/index.json
```

## Deprecated duplicated execution ownership

Workbench previously accumulated build/HIL/evidence orchestration. Those paths are retained temporarily for compatibility/history but are not the future owner. See:

```text
engineering_data/federation/deprecation_registry.json
```

New production build, flash, HIL, artifact, or qualification behavior must be implemented in `ASR5K_v2_28384`.

## Desired Workbench direction

Workbench should evolve toward a federated reader:

```text
Agent contract / decision
        +
firmware exact source / evidence
        ↓
normalized derived model
        ↓
Workbench UI / report
```

High-value future views include:

- Release Readiness;
- Qualification Matrix;
- Evidence Browser;
- Change Impact;
- Open Verification Gaps;
- signal / protocol / state / timing / calibration views.

These are views, not manually maintained competing ledgers.

## Fail-closed rule

If current source identity is unavailable, the Workbench must show `SNAPSHOT`, `STALE`, `PENDING`, `UNKNOWN`, or `NOT CLAIMED`. It must not silently present a historical pinned snapshot as current Engineering Truth.
