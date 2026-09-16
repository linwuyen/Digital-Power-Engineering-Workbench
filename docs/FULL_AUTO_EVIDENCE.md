# Full-Auto Evidence Pipeline — Historical Reference

## Status

The Workbench-owned full-auto execution pipeline is **retired** as of 2026-09-16.

Production build, flash, physical HIL, evidence capture and qualification transactions belong to:

```text
linwuyen/ASR5K_v2_28384
```

Workbench is the View / Analysis Plane and no longer ships the former `auto_run`, `auto_run_ext` or `evidence_agent` executors.

## Why this was retired

The previous design duplicated execution responsibility that already belongs with the exact firmware/toolchain/hardware owner. Keeping both implementations created two risks:

1. an engineer could run the wrong executor and mistake its result for current qualification truth;
2. execution semantics could drift while both copies still passed their own tests.

Three-repository convergence therefore keeps one owner per responsibility class.

## What remains in Workbench

The checked-in material under:

```text
engineering_data/automation/
engineering_data/hil/
```

is retained as **frozen historical/reference data**. It may be used to understand prior contracts, schemas and qualification intent, but it must not be treated as an active production operator.

Workbench may still:

- read exact execution evidence;
- normalize exact-SHA status;
- compare candidate and GOLDEN identities;
- derive blockers and traceability;
- visualize historical or current evidence with explicit provenance.

Workbench may not:

- build production firmware;
- flash a DUT;
- bind a target configuration;
- drive physical HIL;
- collect production evidence as execution owner;
- promote a firmware image to GOLDEN.

## Migration

The retained `asrtest.ps1` / `asrtest.cmd` files are migration stubs only. They intentionally direct operators to the supported tools in `ASR5K_v2_28384` and exit without executing the retired Workbench pipeline.

For current operational commands, use the Execution Plane repository and its repository-owned exact-head build / HIL / qualification wrappers.

## Qualification invariant

The architectural rule remains:

```text
exact candidate SHA
+ exact artifact identity
+ exact run/test identity
+ exact required baseline/GOLDEN identity
+ physical evidence when required
= eligible qualification claim
```

Simulation, source-file presence, historical plans or a previous run never become current PASS by inference.
