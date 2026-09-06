# Current Workbench Status

## Repository role

`linwuyen/Digital-Power-Engineering-Workbench` is the **View / Analysis Plane** for ASR5K.

It is not the owner of:

- product / architecture intent;
- current firmware implementation truth;
- production build / flash / physical HIL execution;
- qualification transaction authority;
- durable current project status.

Those owners are:

```text
ASR5K_AGENT
= Control / Knowledge Plane

ASR5K_v2_28384
= Execution Plane
```

The Workbench federation contract is indexed at:

```text
engineering_data/federation/source_manifest.json
```

## Checked-in ASR5K dataset

The Workbench still contains a reproducible pinned dataset at:

```text
repository: linwuyen/ASR5K_v2_28384
branch:     feat/voltage-slew-runtime-complete
commit:     2b72f50648d86c11547645882248eed69f12892f
```

This dataset is now explicitly classified as:

```text
DERIVED_SNAPSHOT
historical_snapshot
view / analysis only
```

It is not the live firmware baseline. Current live firmware identity and current qualification state must be re-queried from the owning repositories.

## Three-repository convergence

The Workbench has been converged away from acting as a third Engineering Truth owner.

Completed boundary changes:

- added federated source ownership manifest;
- added execution-plane deprecation registry;
- changed `engineering_data/index.json` from authoritative truth wording to derived snapshot wording;
- changed browser UI from `Engineering Truth` to `Engineering Snapshot`;
- added fail-closed checks that Workbench cannot claim current authority;
- CI now verifies federation ownership and historical snapshot consistency;
- active Workbench CI no longer runs duplicate production-build/HIL/qualification orchestration gates;
- new production execution automation is prohibited in Workbench by policy.

## Legacy compatibility infrastructure

Older Workbench automation remains in the repository temporarily for compatibility/history, including build/HIL/evidence helpers introduced before convergence.

Their status is canonical at:

```text
engineering_data/federation/deprecation_registry.json
```

They must not gain new production authority. New execution capability belongs in `linwuyen/ASR5K_v2_28384`.

## Workbench-owned capabilities

Workbench continues to own and develop:

- signal-chain / ADC calculators;
- control / Bode / SFRA analysis;
- state / protocol visualization;
- mock/reference validation tools;
- read-only evidence/status views;
- derived Release Readiness / Qualification / Change Impact views when their source identities are explicit;
- browser presentation and analysis UX.

## Safety boundary

Browser / Workbench remains operator-intent and analysis only. OVP, OCP, OTP, PWM Trip, interlock, emergency safe-off, actuator authority, and deterministic protection remain local to firmware/hardware.

## Evidence boundary

```text
Workbench view PASS
!= firmware build PASS
!= flash PASS
!= board PASS
!= HIL PASS
!= Production qualification
```

A derived Workbench view can only be as strong as the exact source/evidence identities it consumes.

## Next useful Workbench work

The preferred direction is a federated reader, not more mirrored ledgers:

```text
ASR5K_AGENT contracts / decisions
        +
ASR5K_v2_28384 exact source / evidence
        ↓
normalized derived model
        ↓
Workbench UI
```

High-value views may include Release Readiness, Qualification Matrix, Evidence Browser, Change Impact, and Open Verification Gaps, but they must be generated from named owner sources rather than manually maintained as competing truth.
