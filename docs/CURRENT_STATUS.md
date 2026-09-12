# Current Workbench Status

## Repository role

`linwuyen/Digital-Power-Engineering-Workbench` remains the **View / Analysis Plane** for ASR5K.

It does not own product intent, current firmware implementation truth, production build/flash/HIL execution, qualification transactions, or durable project status. Those remain owned by:

```text
ASR5K_AGENT
= Control / Knowledge Plane

ASR5K_v2_28384
= Execution Plane
```

The federation contract is indexed at:

```text
engineering_data/federation/source_manifest.json
```

## ASR5K Engineering Console

The Workbench landing page is now designed as an ASR5K engineering status console rather than a calculator-first toolbox.

It normalizes read-only information into one status model with:

- Control Plane identity;
- Execution Plane exact SHA and branch;
- explicit product GOLDEN identity;
- relation to GOLDEN;
- separate Source / Build / Regression / Artifact / Flash / Board / HIL / Protection / Production gates;
- blockers and unknown evidence;
- source provenance and freshness.

`PASS`, `FAIL`, `GOLDEN`, `MISMATCH`, `PENDING`, `UNKNOWN`, and `STALE` remain semantically distinct. In particular, `UNKNOWN` means the required evidence or source identity could not be established; it must not be converted into PASS or FAIL by guesswork.

## Operating modes

### LIVE

The local Python server reads configured sibling Git repositories using read-only Git queries and exposes:

```text
GET /api/status/summary
GET /api/status/evidence
```

LIVE indicates that the backend queried the configured sources during the request. It does not mean every qualification gate passed.

### SNAPSHOT

GitHub Pages cannot inspect private sibling repositories directly. It consumes the sanitized derived file:

```text
engineering_data/status/status_snapshot.json
```

A public snapshot may show `DEGRADED`, `UNKNOWN`, or later `STALE`. That is expected fail-closed behavior when current owner sources or exact evidence were unavailable. Public browser code never receives a private GitHub token.

The snapshot can be regenerated explicitly from local owner repositories with:

```bash
python tools/generate_status_snapshot.py \
  --agent-root ../ASR5K_AGENT \
  --firmware-root ../ASR5K_v2_28384
```

Snapshot generation creates a derived read-only view only; it does not create or promote qualification evidence.

## Historical checked-in engineering dataset

The Workbench still contains the reproducible historical dataset:

```text
repository: linwuyen/ASR5K_v2_28384
branch:     feat/voltage-slew-runtime-complete
commit:     2b72f50648d86c11547645882248eed69f12892f
classification: historical_snapshot
```

This remains useful for historical source-derived views, but it is not the live firmware baseline and cannot override owner repositories.

## Evidence boundary

```text
Workbench view PASS
!= firmware build PASS
!= flash PASS
!= board PASS
!= HIL PASS
!= Production qualification
```

Exact-SHA evidence does not transfer to another SHA by inference. Test-file presence proves coverage exists, not that an exact run passed. A mismatch is displayed as `MISMATCH`; missing evidence remains `UNKNOWN` / `PENDING`.

## Engineering tools

Existing tools remain available as secondary views:

- signal-chain / ADC calculators;
- control / Bode / SFRA analysis;
- state / protocol visualization;
- mock/reference validation tools;
- read-only evidence and historical engineering views.

The mock remote-control page is a demo/reference surface and is not a production control surface.

## Safety boundary

Browser / Workbench remains operator-intent and analysis only. OVP, OCP, OTP, PWM Trip, interlock, emergency safe-off, actuator authority, and deterministic protection remain local to firmware/hardware.

## Current implementation boundary

The new Console adds visibility, not execution authority. It does not flash firmware, run physical HIL, arm qualification, mutate Agent/Firmware repositories, or promote firmware to GOLDEN.
