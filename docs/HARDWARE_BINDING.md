# ASR5K Local Hardware Binding — Historical Reference

## Status

The Workbench-owned hardware binder is **retired** as of 2026-09-16.

Target discovery, CCS/toolchain binding, flash configuration, physical HIL gateway binding and operator authorization belong to the Execution Plane:

```text
linwuyen/ASR5K_v2_28384
```

`Digital-Power-Engineering-Workbench` is the View / Analysis Plane and no longer ships `tools/hardware_bind.py` or `tools/ccs_build.py`.

## Historical contract retained for analysis

`engineering_data/automation/asr5k_build_contract.json` remains checked in as a frozen historical snapshot bound to:

```text
repository: linwuyen/ASR5K_v2_28384
branch:     feat/voltage-slew-runtime-complete
commit:     2b72f50648d86c11547645882248eed69f12892f
```

The snapshot records the historical project/configuration/toolchain identities:

| ID | CCS project | Configuration | Compiler | Historical artifact name |
|---|---|---|---|---|
| cpu1 | ASR5K_F28384D_CPU1 | FLASH | 22.6.1.LTS | ASR5K_F28384D_CPU1.out |
| cpu2 | ASR5K_F28384D_CPU2 | FLASH | 22.6.1.LTS | ASR5K_F28384D_CPU2.out |
| m0 | ASR5K_M0G3519 | Debug | TICLANG_3.2.2.LTS | ASR5K_M0G3519.out |

These values are historical/reference data. Current build or target identity must be re-queried from the Execution Plane and its exact source/toolchain evidence.

## View-plane boundary

Workbench may display or compare:

- exact firmware SHA;
- artifact identities/hashes emitted by the Execution Plane;
- flash / board / HIL / protection evidence;
- target and toolchain provenance;
- missing, stale or conflicting bindings.

Workbench must not discover a local target and then treat that discovery as permission to flash or drive hardware.

In particular:

```text
tool found        != tool approved
target found      != target authoritative
artifact exists   != artifact flashed
flash success     != board PASS
board response    != protection qualification
```

## Safety and deterministic timing

Hardware binding is outside the deterministic control/protection path. Moving binding ownership out of Workbench does not change C2000/MSPM0 ISR execution, PWM timing, control-loop timing or fault latency.

OVP/OCP/OTP, PWM Trip, interlock and emergency safe-off remain local firmware/hardware authority and must never depend on browser, Workbench or network availability.

## Migration

The root `asrtest.ps1` / `asrtest.cmd` files are retained only as migration stubs. They point operators toward repository-owned exact-head build / qualification tools in `ASR5K_v2_28384` and intentionally do not invoke a Workbench hardware binder.
