https://linwuyen.github.io/Digital-Power-Engineering-Workbench/

# Digital Power Engineering Workbench

Browser-first engineering workbench for digital-power development. The project is intentionally organized around the same signal/authority path used in a real programmable power supply:

**measurement → plant/controller → firmware policy → host protocol → operator intent → validation evidence**.

The public GitHub Pages build runs without a backend. `server.py` provides an optional Python reference path for calculations, contract validation, protocol framing and deterministic mock validation.

## Repository role

Workbench is the **View / Analysis Plane** for ASR5K. It is not the Control Plane and not the Execution Plane.

```text
linwuyen/ASR5K_AGENT
= Control / Knowledge Plane
= product intent, architecture, decisions, durable status, evidence rules

linwuyen/ASR5K_v2_28384
= Execution Plane
= exact firmware, build/test/flash/HIL/qualification execution, artifact/evidence identity

linwuyen/Digital-Power-Engineering-Workbench
= View / Analysis Plane
= visualization, calculators, derived snapshots, evidence/status views
```

The canonical Workbench federation manifest is:

```text
engineering_data/federation/source_manifest.json
```

Workbench must fail closed when current owner-repository identity cannot be established. A historical snapshot is never presented as current production truth.

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

- interactive state viewer
- JSON state-contract import
- duplicate/unknown-state validation
- reachability analysis
- required `hardware_protection` authority boundary

Any ASR5K production state view is limited by the identity and completeness of the imported source snapshot. The full production transition graph must not be invented from a partial snapshot.

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

This demo framing is **not the ASR5K production SPI protocol**. Historical evidence-bound SPIB facts may be displayed from the pinned Workbench snapshot, but current protocol truth must be resolved from the owning ASR5K contract and exact firmware state.

### 6. Web Serial Gateway

The GitHub Pages application can open a browser-authorized Web Serial connection and exchange newline-delimited JSON commands with a local gateway.

Reference command example:

```json
{"action":"set_voltage","value":100}
```

The gateway and DUT must independently revalidate command, range, state and timeout. Browser/network availability is never safety authority.

### 7. Validation Runner

JSON sequence runner validates deterministic mock command/state/protection policy. Simulation results are reference-tool results only; they are not firmware build, flash, board, HIL, or Production qualification evidence.

Production execution and qualification ownership is in `linwuyen/ASR5K_v2_28384`.

### 8. Regression History / Reports

GitHub Pages can store local engineering runs in browser `localStorage` and export JSON/CSV. These are convenience records, not the authoritative ASR5K qualification archive.

## ASR5K Federated Data / Derived Snapshot

`engineering_data/` is the Workbench's **derived snapshot / normalization cache**. It exists to make engineering data easy to render and query; it does not override `ASR5K_AGENT` or `ASR5K_v2_28384`.

Start at:

```text
engineering_data/federation/source_manifest.json
engineering_data/index.json
```

Current checked-in Workbench snapshot:

```text
repository: linwuyen/ASR5K_v2_28384
branch:     feat/voltage-slew-runtime-complete
commit:     2b72f50648d86c11547645882248eed69f12892f
freshness:  historical_snapshot
```

That identity is intentionally retained for reproducible historical rendering. It is **not** the live firmware head. Current firmware state must be re-queried from the Execution Plane.

The snapshot normalizes items such as architecture/ownership, state/fault vocabulary, selected protocol/register facts, explicit unknowns, and historical verification boundaries. Unknown values remain `null` / pending rather than guessed.

Legacy Workbench execution helpers created before three-repository convergence are listed in:

```text
engineering_data/federation/deprecation_registry.json
```

They are compatibility/history only. New production build, flash, physical HIL, artifact-capture, or qualification execution belongs in `ASR5K_v2_28384`.

## Run locally

Python 3.10+; no third-party runtime dependency is required for the reference backend.

```bash
python server.py
```

Open `http://localhost:8000`.

## GitHub Pages

The repository root redirects to `static/`. The browser app loads the engineering modules from `static/eng/` and requires no server for calculations, SFRA comparison, contracts, protocol exploration, mock validation or report export.

Static derived-snapshot JSON is also published by GitHub Pages.

## Verification

```bash
python -m unittest discover -s tests -v
python -m py_compile server.py workbench/*.py tools/*.py tests/*.py
node --check static/app.js
node --check static/i18n.js
node --check static/eng/loader.js
node --check static/eng/common.js
node --check static/eng/data_source.js
node --check static/eng/profiles.js
node --check static/eng/control_sfra.js
node --check static/eng/system_tools.js
```

## Safety / authority boundary

This repository is an engineering tool, not a protection layer.

For real hardware, the following remain local and deterministic in firmware/hardware:

- OVP
- OCP
- OTP
- PWM trip
- interlock
- emergency shutdown

The browser and host are allowed to express **operator intent** only. They do not own protection authority.

## Engineering authority hierarchy

When sources disagree, route by ownership instead of treating Workbench as an authority:

1. current explicit owner instruction;
2. `ASR5K_AGENT` approved ACTIVE contract / ADR / decision for product intent;
3. exact `ASR5K_v2_28384` source for current implementation truth;
4. exact execution / artifact / flash / board / HIL evidence for the claim being made;
5. Workbench `engineering_data/` derived snapshot for navigation / visualization only;
6. Python/browser reference models and examples.

Exact-SHA evidence never transfers to a different SHA by inference.

## Repository architecture

```text
Federated owners
├─ ASR5K_AGENT          Control / Knowledge Plane
├─ ASR5K_v2_28384       Execution Plane
└─ Workbench            View / Analysis Plane

Workbench GitHub Pages / Browser
├─ Measurement + JSON profiles
├─ Control / Bode / SFRA analysis
├─ State / protocol views
├─ Evidence / status views
├─ Web Serial reference gateway
└─ Local history / export

Derived snapshot / cache
├─ engineering_data/federation
├─ engineering_data/architecture
├─ engineering_data/firmware
├─ engineering_data/protocol
├─ engineering_data/control
├─ engineering_data/verification
└─ engineering_data/source_truth

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

Historical Workbench pending items remain useful as a view of the pinned snapshot, but they are not the authoritative current backlog. Current blockers and current qualification state belong to `ASR5K_AGENT` and exact Execution Plane evidence.

## Repository policy

Develop on feature branches, verify in CI, merge through PRs, and keep Workbench read/analysis-focused. Do not add new production execution authority here when an owning Control or Execution Plane already exists.
