# Digital Power Engineering Workbench

A browser-based engineering workbench for digital-power development. The MVP intentionally connects four views of the same system: **measurement**, **control**, **firmware authority**, and **operator commands**.

## MVP modules

1. **Datasheet / Signal-Chain Calculator**
   - physical quantity → sensor → op-amp → divider → ADC voltage/code
   - inverse reconstruction back to engineering units
   - explicit ADC clipping and quantization error

2. **Digital Control Visualizer**
   - ideal CCM buck averaged control-to-output plant
   - PI compensator
   - digital delay approximation
   - Bode magnitude, 0 dB crossover, phase margin, LC resonance
   - Tustin incremental PI coefficients (`b0`, `b1`)
   - warnings when crossover approaches `fs/10` or `fsw/10`

3. **Firmware State Machine Viewer**
   - BOOT / INIT / STANDBY / PRECHARGE / SOFT_START / RUN / STOP / FAULT
   - entry/exit conditions, PWM status, command/control/protection authority
   - explicit authority hierarchy from UI → host → firmware → control loop → hardware protection

4. **Power Supply Remote Control**
   - deterministic mock PSU only
   - bounded set-voltage / current-limit commands
   - output ON/OFF, telemetry and fault/interlock gating
   - intentionally demonstrates that the browser and network are **not** safety authority

## Run

Requires Python 3.10+ and no third-party runtime dependencies.

```bash
python server.py
```

Open `http://localhost:8000`.

Run regression tests:

```bash
python -m unittest discover -s tests -v
```

## Safety / evidence boundary

This repository is an engineering visualization and host-tool prototype. The included remote-control path uses a mock transport. It must not be treated as a protection layer or connected to production hardware without a reviewed protocol adapter and device-side validation.

For a real power supply, OVP/OCP/OTP, PWM trip, emergency shutdown and interlock authority must remain local and deterministic in hardware/firmware. Network/UI availability must never be required to reach a safe state.

The control visualizer uses an ideal averaged CCM buck model. Plant parameters, sampling/PWM delay, computational delay, power-stage parasitics and loop interactions must be validated against SFRA or measured loop gain before controller changes reach hardware.

## Architecture

```text
Browser UI
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
