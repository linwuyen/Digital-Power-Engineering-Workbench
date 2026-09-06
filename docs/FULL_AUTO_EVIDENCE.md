# Full-Auto Evidence Pipeline

The normal operator workflow is intentionally reduced to **one setup action once** and **one command per test run**.

## One-time setup

On Windows PowerShell from the Workbench repository:

```powershell
.\asrtest.ps1 init
.\asrtest.ps1 doctor
```

`init` creates `.engineering_local/auto_run.json`, a local raw-evidence archive, and instrument inbox folders. These paths are Git-ignored. Point scope/SFRA/logic-analyzer exports at their corresponding inbox once; operators do not create run directories or evidence JSON manually.

For real hardware plans set `allow_hardware` to `true` once after reviewing the local configuration. A process HIL plan also needs a local `gateway_command`. These values are deliberately local and are never committed.

## Daily operation

```powershell
.\asrtest.ps1 list
.\asrtest.ps1 doctor <PLAN-ID>
.\asrtest.ps1 run <PLAN-ID>
```

A run automatically performs:

```text
Generate RUN ID
  -> exact-baseline / clean-tree preflight
  -> snapshot instrument export folders
  -> build / flash / HIL / command steps from the plan
  -> wait for required measurement files when specified
  -> collect every new/modified scope/SFRA/logic/log file
  -> copy explicit DUT artifacts
  -> SHA-256 every archived object
  -> write immutable run manifest
  -> derive PASS / FAIL / BLOCKED evidence claims
  -> append validated evidence ledger records
  -> recompute requirement traceability
  -> auto-commit only canonical evidence metadata
```

Raw `.out`, `.bin`, large traces, screenshots and instrument captures stay under `.engineering_local/archive/YYYY/MM/DD/RUN-*` by default. Git stores the exact hashes and evidence relationships, not the bulk raw data.

## Fail-closed qualification rules

The automation does not turn convenience into weaker qualification semantics.

- Wrong production SHA -> run is `BLOCKED_PREFLIGHT`.
- Dirty production checkout when the plan requires clean source -> blocked.
- Hardware plan without local hardware enable -> blocked.
- Missing required artifact -> evidence claim is `BLOCKED`.
- Missing required scope/SFRA/logic output -> evidence claim is `BLOCKED`.
- Failed depended-on test step -> `FAIL` evidence.
- Simulation/mock success -> never qualification PASS.
- A PASS claim still passes through the existing evidence validator and requires exact baseline, run ID, artifact identity/SHA-256, requirement link and timestamp.

## Storage

The operator does not choose a destination for every run. The default is:

```text
.engineering_local/
├─ auto_run.json
├─ inbox/
│  ├─ scope/
│  ├─ sfra/
│  ├─ logic/
│  └─ logs/
├─ runtime/
│  ├─ active_run.json
│  └─ latest_run.json
└─ archive/
   └─ YYYY/MM/DD/RUN-.../
      ├─ run_context.json
      ├─ logs/
      ├─ results/
      ├─ artifacts/
      ├─ raw/
      ├─ manifest.json
      └─ summary.json
```

If raw evidence belongs on another drive, change `archive_root` once in `.engineering_local/auto_run.json`. No test-plan changes are required.

## Plans

Canonical plans live under `engineering_data/automation/plans/`. A hardware plan declares exactly which commands/HIL steps run, which artifacts are mandatory, which physical collectors must produce data, and which requirement IDs each evidence claim is allowed to qualify.

The checked-in `AUTO-REFERENCE-MOCK-001` is an end-to-end smoke plan. It intentionally finishes unqualified because simulation is not production evidence.
