# Digital Power Engineering Workbench

A browser-based engineering workbench for digital-power development. The MVP intentionally connects four views of the same system: **measurement**, **control**, **firmware authority**, and **operator commands**.

The current feature branch is designed to run in two modes:

- **Static browser mode** — no backend required; suitable for GitHub Pages. Measurement/control calculations and the PSU/state simulators execute locally in the browser.
- **Python reference mode** — run `server.py`; the browser uses the Python calculation cores and deterministic mock PSU backend.

## MVP modules

1. **Datasheet / Signal-Chain Calculator**
   - physical quantity → sensor → op-amp → divider → ADC voltage/code
   - inverse reconstruction back to engineering units
   - explicit ADC clipping and quantization error

2. **Digital Control Visualizer**
   - ideal CCM buck averaged control-to-output plant
   - PI compensator
   - computation/PWM delay approximation
   - Bode magnitude + loop phase
   - 0 dB crossover, phase margin and LC resonance
   - phase unwrap before phase-margin interpolation
   - Tustin incremental PI coefficients (`b0`, `b1`)
   - warnings when crossover approaches `fs/10` or `fsw/10`, phase margin falls below 45°, or becomes non-positive

3. **Firmware State Machine Viewer**
   - BOOT / INIT / STANDBY / PRECHARGE / SOFT_START / RUN / STOP / FAULT
   - entry/exit conditions, PWM status, command/control/protection authority
   - explicit authority hierarchy from UI → host → firmware → control loop → hardware protection
   - interactive transition-policy simulator and transition history

4. **Power Supply Remote Control**
   - deterministic mock PSU only
   - bounded 0–700 V / 0–15 A setpoint model
   - output ON/OFF, telemetry and fault/interlock gating
   - browser-mode OCP injection and interlock simulation
   - command log showing accepted/rejected requests
   - intentionally demonstrates that browser/network command authority is lower than protection authority

## Run locally

Requires Python 3.10+ and no third-party runtime dependencies.

```bash
python server.py
```

Open `http://localhost:8000`.

The header should report **PYTHON REFERENCE** when the backend is detected.

## Static / GitHub Pages mode

The repository root contains `index.html`, which redirects to the self-contained static application under `static/`. No Python server is required in this mode.

After this branch is merged, GitHub Pages can serve the repository root directly. The header should report **STATIC BROWSER** and **standalone ready**.

Static mode is intentionally useful for calculations, visualization and policy simulation only. It does not create a real hardware transport.

## Verification

Regression tests:

```bash
python -m unittest discover -s tests -v
```

Syntax checks:

```bash
python -m py_compile server.py workbench/*.py
node --check static/app.js
```

`.github/workflows/ci.yml` contains the same checks for GitHub Actions. At the time the workflow was first added on the feature branch, GitHub had not yet produced a workflow run, so do not treat CI as proven until an Actions run reports PASS.

## Safety / evidence boundary

This repository is an engineering visualization and host-tool prototype. The included remote-control path uses a mock transport. It must not be treated as a protection layer or connected to production hardware without a reviewed protocol adapter and device-side validation.

For a real power supply, OVP/OCP/OTP, PWM trip, emergency shutdown and interlock authority must remain local and deterministic in hardware/firmware. Network/UI availability must never be required to reach a safe state.

The control visualizer uses an ideal averaged CCM buck model. It does **not** yet include capacitor ESR, inductor DCR, PWM modulator gain normalization, current-loop interaction, right-half-plane zeros, sampled-data effects beyond the configured pure delay, saturation/anti-windup, quantization or nonlinear operating-point changes. Validate plant parameters, controller scaling and delay against SFRA or measured loop gain before controller changes reach hardware.

## Architecture

```text
Browser UI
   │
   ├── static mode ────────> local JavaScript engineering models
   │
   └── Python mode ────────> server.py
                              │
                              ├── Measurement calculator ──> workbench.measurement
                              ├── Control visualizer ──────> workbench.control
                              ├── State viewer ────────────> workbench.state_machine
                              └── Remote console ──────────> workbench.remote (MOCK)
                                                           │
                                                           └── future reviewed protocol adapter
                                                                └── device firmware command gate
                                                                     └── local protection authority
```

## Engineering truth hierarchy

When results disagree, use this priority:

1. measured hardware / calibrated instrument evidence
2. production firmware behavior and explicit interface contracts
3. Python reference model in `workbench/`
4. browser static model
5. documentation/examples

The browser model should remain numerically aligned with the Python model, but it is a convenience execution path rather than the source of truth.

## Next engineering increments

- load/save signal-chain profiles for real ADC/DAC/current-sensor front ends
- add tolerance / worst-case stack-up and calibration coefficients
- add Boost/PFC/PSFB/LLC plant models and discrete controller variants
- import measured SFRA CSV and overlay theory vs measurement
- import firmware state definitions from a machine-readable contract
- add transport abstraction for serial/Ethernet gateways while preserving firmware-side command gating
- add test-sequence runner and report generation

## Repository policy

Development should occur on feature branches and merge through pull requests. Keep calculation cores pure/testable; keep hardware transport behind an explicit boundary.
