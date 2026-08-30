# Current Engineering Status

## Authoritative production baseline

- Repository: `linwuyen/ASR5K_v2_28384`
- Branch: `feat/voltage-slew-runtime-complete`
- Exact commit: `2b72f50648d86c11547645882248eed69f12892f`
- Production repository access for this dataset: **read-only**

## Workbench release state

The Digital Power Engineering Workbench software stack is integrated and published from `main` through GitHub Pages. The browser application consumes `engineering_data/` directly and uses a fail-closed trust model: unknown production values are shown as pending instead of being substituted with demo values.

## Source-verified production facts

- CPU1 SystemState vocabulary: `BOOT`, `INIT`, `IDLE`, `RUN`, `FAULT`, `MAINTENANCE`, `OTA`.
- CPU1 SPIB NORMAL request width: 32 bit, encoded as 16-bit address + 16-bit data.
- SPIB response timing: response is generated for the next master transaction.
- SPIB NULL/fetch frame: `0xFFFF0000`.
- Host Command queue depth: 8.
- Verified scalar register contracts:
  - Frequency: `0x0910/0x0911`, `0.01 Hz/count`.
  - FREQ_COMP ON/OFF: `0x0929`, bit0.
  - DCV: `0x0939/0x093A`, `0.0001 V/count`.
  - ACV: `0x093B/0x093C`, `0.0001 V/count`.
- AC input classification source: GPIO8 / ECAP1; accepted frequency 45–65 Hz; duty 10–90%; 3 confirmation samples.
- System sequence source constants currently extracted include 500 ms AC ACK timeout, 500 ms output ACK timeout, 20 ms output relay settle, and 500 ms DDS-start liveness timeout. These are software timing constants, not measured hardware performance claims.
- SPIB parser diagnostic thresholds of 500 and 1000 CPU timer ticks exist; they are diagnostics, not formal acceptance deadlines.

## Governance / authority contracts

- Browser and network control express operator intent only.
- Protection, PWM Trip and emergency safe-off authority remain local to firmware/hardware.
- Detection authority, shutdown authority, state-policy ownership and host visibility are modeled separately.
- A source file or test file existing does not prove a PASS run.

## Explicit pending verification

The following are intentionally **not** promoted to production truth:

- VOUT / IOUT / VBUS / temperature ADC module/channel/SOC/trigger mapping.
- Analog front-end gain, offset, tolerance and calibration coefficients for those ADC measurements.
- Formal numerical SPIB response-deadline acceptance limit.
- Production control ISR period until the exact timer/PWM trigger path is extracted and cross-checked.
- Exact electrical thresholds and complete routing for local C28 / MSPM0 protection paths.
- Measured fault-detection-to-safe-output latency.
- Complete production SystemState transition/guard/action table.
- Complete AM3352 ↔ CPU1 wire register and telemetry dictionary.
- Production PFC / PSFB / LLC plant, controller and SFRA operating-point package.
- CPU1 / CPU2 / M0 exact-baseline build PASS records.
- Board HIL and real-AM3352 A/B qualification records.

## Canonical data sources

Start from `engineering_data/index.json`.

The highest-value engineering-memory sources are:

- `engineering_data/requirements/requirement_ledger.json` — requirement → implementation → verification → evidence traceability.
- `engineering_data/hardware/signal_dictionary.json` — signal identity, direction, owner, scaling and explicit unknown analog chain fields.
- `engineering_data/timing/timing_budget.json` — software timing constants, formal-deadline placeholders, measured-WCET fields and evidence requirements.
- `engineering_data/protection/protection_matrix.json` — fault bitmap, detection/shutdown authority and qualification gaps.
- `engineering_data/evidence/evidence_ledger.jsonl` — append-only evidence contract for exact run/artifact PASS records.

## Definition of Done

A production item is considered qualified only when all applicable layers are closed:

1. Requirement is explicit.
2. Implementation/source identity is exact.
3. Static/contract/regression verification exists.
4. Build artifact is bound to an exact baseline/toolchain when relevant.
5. Hardware or HIL evidence exists when the claim concerns physical behavior or latency.
6. Evidence is appended to the ledger with exact test, artifact and timestamp identity.

Until those conditions are met, the status remains `pending_verification` or `not_claimed`.
