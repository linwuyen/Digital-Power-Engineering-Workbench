# Current Engineering Status

## Authoritative production baseline

- Repository: `linwuyen/ASR5K_v2_28384`
- Branch: `feat/voltage-slew-runtime-complete`
- Exact commit: `2b72f50648d86c11547645882248eed69f12892f`
- Production repository access for this dataset: **read-only**

## Workbench release state

The Digital Power Engineering Workbench software stack is integrated and published from `main` through GitHub Pages. The browser application consumes `engineering_data/` directly and uses a fail-closed trust model: unknown production values are shown as pending instead of being substituted with demo values.

## Engineering OS automation state

The automation framework is implemented for source-truth extraction, source-truth drift detection, evidence validation/import, requirement-to-evidence traceability, host-intent-only HIL execution, full-auto run capture, and local hardware/build binding.

CI always verifies the commit-pinned source snapshot `engineering_data/source_truth/snapshot-2b72f506.json` against canonical engineering data. A live private-repository re-extraction runs only when `ASR5K_READ_TOKEN` is configured; without it the live check is explicitly SKIPPED and is not claimed as a live-source PASS.

## Local binding and exact builds

The remaining build setup is now automated by `asrtest bind`. It discovers an exact-baseline ASR5K checkout, CCS CLI, source project metadata, optional DSLite/ccxml, collector folders and optional HIL gateway. It never enables physical hardware automatically.

Source-verified build contracts are now canonical for:

- CPU1: `ASR5K_F28384D_CPU1`, configuration `FLASH`, C2000 compiler `22.6.1.LTS`, artifact `ASR5K_F28384D_CPU1.out`.
- CPU2: `ASR5K_F28384D_CPU2`, configuration `FLASH`, C2000 compiler `22.6.1.LTS`, artifact `ASR5K_F28384D_CPU2.out`.
- M0: `ASR5K_M0G3519`, configuration `Debug`, TIClang `3.2.2.LTS`, artifact `ASR5K_M0G3519.out`.

Canonical build plans exist for each target and for the three-target sequence. These plans are `NOT_CLAIMED` until they are actually run on the user's bound local CCS installation and exact `.out` SHA-256 evidence is appended.

Build mode is non-physical: it cannot run HIL, execute hardware-marked steps, wait on physical collectors, or satisfy physical-evidence requirements.

## Source-verified production facts

- CPU1 SystemState vocabulary: `BOOT`, `INIT`, `IDLE`, `RUN`, `FAULT`, `MAINTENANCE`, `OTA`.
- CPU1 SPIB NORMAL request width: 32 bit, encoded as 16-bit address + 16-bit data.
- SPIB response timing: response is generated for the next master transaction.
- SPIB NULL/fetch frame: `0xFFFF0000`.
- Host Command queue depth: 8.
- Verified scalar register contracts: Frequency `0x0910/0x0911` at `0.01 Hz/count`; FREQ_COMP `0x0929` bit0; DCV `0x0939/0x093A` at `0.0001 V/count`; ACV `0x093B/0x093C` at `0.0001 V/count`.
- AC input classification source: GPIO8 / ECAP1; accepted frequency 45–65 Hz; duty 10–90%; 3 confirmation samples.
- System sequence constants include 500 ms AC ACK timeout, 500 ms output ACK timeout, 20 ms output relay settle and 500 ms DDS-start liveness timeout. These are software constants, not measured hardware performance claims.
- SPIB parser diagnostic thresholds of 500 and 1000 CPU timer ticks exist; they are diagnostics, not formal acceptance deadlines.

## Governance / authority contracts

- Browser and network control express operator intent only.
- Protection, PWM Trip and emergency safe-off authority remain local to firmware/hardware.
- Detection authority, shutdown authority, state-policy ownership and host visibility are modeled separately.
- A source file or test file existing does not prove a PASS run.
- Source-verified fact drift is a CI blocker.
- Exact-baseline PASS evidence is required before traceability can promote a requirement to `QUALIFIED_BY_EVIDENCE`.

## Explicit pending verification

The following are intentionally **not** promoted to production truth:

- CPU1 / CPU2 / M0 exact-baseline build PASS records until the new build plans actually execute locally.
- Production flash target configuration/command: no canonical `.ccxml` is established by the exact source baseline; local detection must be unambiguous.
- Production process-JSONL HIL gateway: no exact gateway command is established by the source baseline.
- VOUT / IOUT / VBUS / temperature ADC module/channel/SOC/trigger mapping and analog calibration.
- Formal numerical SPIB response deadline.
- Exact electrical thresholds and complete routing for local C28 / MSPM0 protection paths.
- Measured fault-detection-to-safe-output latency.
- Complete production SystemState transition/guard/action table.
- Complete AM3352 ↔ CPU1 wire register and telemetry dictionary.
- Production PFC / PSFB / LLC plant, controller and SFRA operating-point package.
- Board HIL and real-AM3352 A/B qualification records.
- Live private-repository source recheck until a CI run actually executes it with `ASR5K_READ_TOKEN`.

## Canonical data sources

Start from `engineering_data/index.json`. Key sources include the requirement ledger, signal dictionary, timing budget, protection matrix, evidence ledger, pinned source snapshot, HIL catalog, exact CCS build contract and canonical build plans.

## Definition of Done

A production item is qualified only when the requirement is explicit, source identity is exact, verification exists, the build artifact is exact when relevant, hardware/HIL evidence exists for physical claims, and evidence is appended with exact test/artifact/timestamp identity. Until then it remains pending or not claimed.
