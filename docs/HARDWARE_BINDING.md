# ASR5K Local Hardware Binding

This layer removes the remaining hand-edited build binding from the normal operator flow.

## One-time command

From the Workbench repository on Windows:

```powershell
.\asrtest.ps1 init
.\asrtest.ps1 bind
.\asrtest.ps1 doctor
```

`bind` does not enable physical hardware. It only discovers and verifies local prerequisites.

## What `bind` discovers automatically

The binder checks, in order:

1. Exact ASR5K production checkout, including the canonical SHA.
2. CCS command-line executable (`eclipsec` or `ccs-server-cli`).
3. Local project metadata against the exact-baseline build contract.
4. Optional DSLite / UniFlash executable.
5. An unambiguous `.ccxml` target configuration if one exists.
6. Optional process-JSONL HIL gateway only when explicitly supplied.
7. Scope / SFRA / logic / log export folders.

The resulting local report is `.engineering_local/binding.json`; the operational config is `.engineering_local/auto_run.json`. Both are Git-ignored.

## Optional explicit overrides

No environment variables are required when normal paths are discoverable. These are optional locators only; they do not upgrade trust:

`ASR5K_REPO`, `CCS_CLI`, `CCS_ROOT`, `DSLITE`, `ASR_CCXML`, `ASR_GATEWAY_COMMAND`, `ASR_SCOPE_EXPORT`, `ASR_SFRA_EXPORT`, `ASR_LOGIC_EXPORT`, `ASR_LOG_EXPORT`.

## Exact build contract

`engineering_data/automation/asr5k_build_contract.json` is bound to `linwuyen/ASR5K_v2_28384`, branch `feat/voltage-slew-runtime-complete`, exact SHA `2b72f50648d86c11547645882248eed69f12892f`.

| ID | CCS project | Configuration | Compiler | Exact artifact name |
|---|---|---|---|---|
| cpu1 | ASR5K_F28384D_CPU1 | FLASH | 22.6.1.LTS | ASR5K_F28384D_CPU1.out |
| cpu2 | ASR5K_F28384D_CPU2 | FLASH | 22.6.1.LTS | ASR5K_F28384D_CPU2.out |
| m0 | ASR5K_M0G3519 | Debug | TICLANG_3.2.2.LTS | ASR5K_M0G3519.out |

The `.out` name comes from CCS metadata (`artifactName=${ProjName}`, `artifactExtension=out`), not a guessed filename.

## Build plans

After `bind` reports `BUILD_BINDING=READY`:

```powershell
.\asrtest.ps1 doctor ASR5K-CPU1-BUILD-001
.\asrtest.ps1 run ASR5K-CPU1-BUILD-001
.\asrtest.ps1 run ASR5K-CPU2-BUILD-001
.\asrtest.ps1 run ASR5K-M0-BUILD-001
.\asrtest.ps1 run ASR5K-TRIPLE-BUILD-001
```

Each plan performs exact SHA / clean-tree preflight, CCS CLI capability probe, fresh per-run workspace, exact project import, full build of the exact configuration, exact `.out` requirement, SHA-256 archive, evidence-ledger append and traceability refresh. A CCS return code without a fresh `.out` is not PASS.

## Build mode vs hardware mode

`build` mode is separate from `hardware`: it does not require `allow_hardware=true`, cannot run HIL, cannot execute `hardware=true` commands, cannot wait for physical collectors and cannot satisfy `physical_evidence_required`. A build can qualify a build requirement only; it cannot qualify board behavior, fault latency, SFRA or HIL.

## Flash binding

Flash is intentionally not guessed. The exact source baseline does not establish one canonical `.ccxml` or production flash command. `bind` may discover DSLite and a `.ccxml`, but flash becomes `READY` only when the target configuration is unambiguous. Otherwise it reports `FLASH_BINDING=PENDING` and generates no guessed flash action.

## HIL gateway binding

The existing process JSONL adapter is a harness contract, not the production AM3352 ↔ CPU1 SPIB framing implementation. A gateway becomes ready only when a real local command is supplied, for example through `ASR_GATEWAY_COMMAND`. Until then the binder reports `HIL_GATEWAY_BINDING=PENDING`.

## Hardware enable

The binder never changes `allow_hardware` from false to true. Physical flash/HIL/fixture control requires explicit local operator enable after detected paths are reviewed. This preserves the boundary between discovery and authority to touch hardware.
