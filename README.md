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

Reference frame format:

```text
AA 55 | command_id:u16le | payload_len:u16le | payload | CRC16-CCITT:u16le
```

Features:

- encode/decode
- CRC validation
- payload size limit
- byte-level breakdown

This reference framing is **not a claim about the ASR5K production SPI protocol**. Before real Host integration, import/freeze the production command map, endian rules, CRC/checksum and response/deadline contract.

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

## Run locally

Python 3.10+; no third-party runtime dependency is required for the reference backend.

```bash
python server.py
```

Open `http://localhost:8000`.

## GitHub Pages

The repository root redirects to `static/`. The browser app loads the engineering v1 modules from `static/eng/` and requires no server for calculations, SFRA comparison, contracts, protocol exploration, mock validation or report export.

## Verification

```bash
python -m unittest discover -s tests -v
python -m py_compile server.py workbench/*.py
node --check static/app.js
node --check static/i18n.js
node --check static/eng/loader.js
node --check static/eng/common.js
node --check static/eng/profiles.js
node --check static/eng/control_sfra.js
node --check static/eng/system_tools.js
```

GitHub Actions runs the same verification.

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

1. calibrated hardware measurements / independent instruments
2. production firmware behavior and frozen interface contracts
3. Python reference models in `workbench/`
4. browser models under `static/`
5. documentation/examples/reference templates

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

## What still requires project-specific truth

The software framework is intentionally complete enough to accept the missing production facts, but these facts cannot be safely guessed:

- real ASR5K ADC/DAC/current/voltage channel coefficients
- production AM3352 ↔ C2000 command IDs/frame/checksum/deadlines
- real PSFB/LLC/PFC operating-point plant parameters
- real HIL instrument transport and pass/fail tolerances

Those items should be imported as reviewed profiles/contracts or measured SFRA data, not hard-coded from assumptions.

## Repository policy

Develop on feature branches, verify in CI, merge through PRs, and keep hardware transport behind an explicit authority boundary.
