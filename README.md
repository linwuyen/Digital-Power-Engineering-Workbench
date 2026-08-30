# Digital Power Engineering Workbench

Browser-first engineering workbench for digital-power development. The project is intentionally organized around the same signal/authority path used in a real programmable power supply:

**measurement → plant/controller → firmware policy → host protocol → operator intent → validation evidence**.

The public GitHub Pages build runs without a backend. `server.py` provides an optional Python reference path for calculations, contract validation, protocol framing and deterministic mock validation.

## Engineering v1 modules

### 1. Datasheet / Signal-Chain Calculator

- physical quantity → sensor → op-amp → divider → ADC code
- inverse reconstruction to engineering units
- explicit ADC clipping and quantization error
- load/save signal-chain profiles in JSON
- built-in profiles are **reference templates**, not verified ASR5K channel coefficients

Truth requirement: replace reference coefficients with the actual schematic, datasheet, calibration and measured values before using results for hardware decisions.

### 2. Digital Control Visualizer

Two model levels are available:

- ideal CCM Buck + PI + delay reference model
- topology-agnostic identified second-order plant with optional RHP zero + pole/zero controller

The advanced model supports identified plant/controller parameters rather than inventing unverified Boost/PFC/PSFB/LLC equations. Use design equations or SFRA to identify the required resonance/Q/RHPZ/controller pole/zero parameters.

Outputs include Bode magnitude/phase, 0 dB crossover, phase margin and model-risk warnings.

### 3. SFRA Theory / Measurement Compare

- CSV import (`frequency_hz,magnitude_db,phase_deg` plus common aliases)
- log-frequency interpolation
- theory vs measured overlay
- RMS magnitude and phase error
- explicit model-mismatch assessment

Large theory/measurement error is treated as evidence that the analytic model should not have hardware tuning authority.

### 4. Firmware State Machine + Machine-Readable Contract

- existing interactive reference state viewer
- JSON state-contract import
- duplicate/unknown-state validation
- reachability analysis
- required `hardware_protection` authority boundary

The contract is designed so production firmware state definitions can become explicit reviewable data instead of being inferred only from source-code control flow.

### 5. Protocol Explorer

Reference/demo frame format:

```text
AA 55 | command_id:u16le | payload_len:u16le | payload | CRC16-CCITT:u16le
```

Features:

- encode/decode
- CRC validation
- payload size limit
- byte-level breakdown

This demo framing is **not the ASR5K production SPI protocol**. The evidence-bound production SPIB contract is now indexed separately under `engineering_data/protocol/`: 32-bit address/data request, next-master-transaction response, `0xFFFF0000` NULL frame, additive response checksum semantics, and only the scalar register addresses proven by the pinned production source.

### 6. Web Serial Gateway

The GitHub Pages application can open a browser-authorized Web Serial connection and exchange newline-delimited JSON commands with a local gateway.

Reference command example:

```json
{"action":"set_voltage","value":100}
```

The gateway and DUT must independently revalidate command, range, state and timeout. Browser/network availability is never safety authority.

### 7. Validation Runner

JSON sequence runner currently validates deterministic mock command/state/protection policy, including:

- bounded voltage/current commands
- OUTPUT ON/OFF
- state assertions
- fault injection in mock mode
- fault authority over OUTPUT_ON

Real HIL PASS/FAIL must additionally include independent scope/DAQ/instrument evidence.

### 8. Regression History / Reports

GitHub Pages stores the latest local engineering runs in browser `localStorage` and can export JSON/CSV.

A production team regression database should instead be written by CI/HIL infrastructure with immutable commit/build/test metadata.

## ASR5K Engineering Data Source

`engineering_data/` is the evidence-bound truth/index layer for Workbench, AI agents, host/HIL tools and future report generators.

Current dataset baseline:

```text
repository: linwuyen/ASR5K_v2_28384
branch:     feat/voltage-slew-runtime-complete
commit:     2b72f50648d86c11547645882248eed69f12892f
```

Start at:

```text
engineering_data/index.json
```

The dataset normalizes:

- exact baseline identity
- architecture and C28/MSPM0 ownership
- SystemState/fault vocabulary and critical paths
- verified signal names and explicit unknown scaling
- protection facts and explicit unknown thresholds/latencies
- SPIB host wire contract and verified scalar registers
- verification/test catalogs without false PASS claims
- AI safety invariants and commit-pinned evidence links
- empty hardware/regression ledgers that only accept evidence-bound future results

Trust values are explicit: `verified_source`, `governance_contract`, `derived`, or `pending_verification`. A `null` pending value is intentional and must never be silently replaced by zero, one, a legacy register or a guessed datasheet value.

This repository does not modify the production ASR5K source. The generated data is a derived navigation/normalization layer and cannot override higher-tier design or production-source authority.

## Run locally

Python 3.10+; no third-party runtime dependency is required for the reference backend.

```bash
python server.py
```

Open `http://localhost:8000`.

## GitHub Pages

The repository root redirects to `static/`. The browser app loads the engineering v1 modules from `static/eng/` and requires no server for calculations, SFRA comparison, contracts, protocol exploration, mock validation or report export.

Static engineering-data JSON is also published by GitHub Pages, with `engineering_data/index.json` as the stable discovery endpoint.

## Verification

```bash
python -m unittest discover -s tests -v
python -m py_compile server.py workbench/*.py tests/test_engineering_data.py
node --check static/app.js
node --check static/i18n.js
node --check static/eng/loader.js
node --check static/eng/common.js
node --check static/eng/profiles.js
node --check static/eng/control_sfra.js
node --check static/eng/system_tools.js
```

GitHub Actions runs the same verification and additionally parses every JSON file under `engineering_data/`.

## Safety / authority boundary

This repository is an engineering tool, not a protection layer.

For real hardware, the following must remain local and deterministic in firmware/hardware:

- OVP
- OCP
- OTP
- PWM trip
- interlock
- emergency shutdown

The browser and host are allowed to express **operator intent** only. They do not own protection authority.

## Engineering truth hierarchy

When sources disagree, use this order:

1. current explicit instruction / formal design documents
2. exact production firmware behavior and frozen interface contracts
3. active architecture contracts, with their baseline caveat
4. calibrated hardware measurements / qualification evidence bound to exact artifacts
5. derived `engineering_data/` index
6. Python/browser reference models and examples

## Repository architecture

```text
GitHub Pages / Browser
├─ Measurement + JSON profiles
├─ Buck reference control model
├─ Identified plant / pole-zero control lab
├─ SFRA CSV comparison
├─ State-contract validator
├─ Protocol explorer
├─ Web Serial reference gateway
├─ Validation runner
└─ Local history / export

Engineering truth/index layer
├─ engineering_data/architecture
├─ engineering_data/firmware
├─ engineering_data/protocol
├─ engineering_data/control
├─ engineering_data/verification
├─ engineering_data/baselines
└─ engineering_data/ai

Python reference backend
├─ workbench.measurement
├─ workbench.profiles
├─ workbench.control
├─ workbench.control_advanced
├─ workbench.sfra
├─ workbench.contracts
├─ workbench.protocol
├─ workbench.state_machine
├─ workbench.remote
└─ workbench.validation
```

## Explicit pending verification

The data-source framework is complete, but evidence that was not established is intentionally represented as `null` / `pending_verification` rather than guessed. Current important pending facts include:

- real ASR5K ADC current/voltage/temperature channel scaling and calibration coefficients
- complete AM3352 ↔ C2000 register/telemetry map beyond the extracted authoritative scalar registers
- formal numerical SPIB response-deadline acceptance limit
- measured hardware protection shutdown latency
- production PSFB/LLC/PFC plant/controller/SFRA operating-point package
- exact board/HIL/AM3352 A/B qualification records for the pinned baseline

Promote a pending value only when exact source, schematic/calibration, or measured evidence is added and bound to the relevant baseline/artifact.

## Repository policy

Develop on feature branches, verify in CI, merge through PRs, and keep hardware transport behind an explicit authority boundary.
