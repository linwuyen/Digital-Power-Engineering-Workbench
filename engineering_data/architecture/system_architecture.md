# ASR5K System Architecture — Evidence-Bound Map

Baseline: `linwuyen/ASR5K_v2_28384@2b72f50648d86c11547645882248eed69f12892f`

## Proven production path

```text
AM3352 host intent
    |
    v
CPU1 SPIB NORMAL transport
    | 32-bit request / next-transaction 32-bit response
    v
SpiBCommandRouter / HostCommandAdmission
    |
    v
HostCommandQueue (bounded, depth 8)
    |
    v
HostCommandController (background cooperative dispatcher)
    |                    |
    |                    +--> DDS / waveform / scalar owners
    v
CPU1 SystemState
    |
    +--> local DDS / DCAC safe actions
    |
    +--> C28 request/policy to MSPM0 physical-output contract
                              |
                              v
                     applied state / telemetry
```

## Safety data path

```text
local C28 protection / M0 protection telemetry / AC input monitor
                     |
                     v
              CPU1 SystemState
                     |
           active + latched faults
                     |
              blocking mask
                     |
       +-------------+-------------+
       |                           |
       v                           v
safe-off / DDS stop       child power-sequence force fault
```

Production source states that CPU1 owns the formal System State and that ISR/DMA code may report a fault source but must not perform state transitions directly.

## Ownership boundary

The active architecture contract describes one-owner semantics:

- CPU1 owns SystemState, top-level state transitions, DDS/waveform/scalar derivation, local DCAC control and C28-local CMPSS/TZ/ISR protection.
- MSPM0 owns PFC/DCDC/AC_OCPA physical GPIO, OUT_ON physical relay GPIO, fan physical service, DAC physical transaction, M0 protection GPIO acquisition/decode and critical physical shutdown timing.
- CPU1 owns requested command image; MSPM0 owns applied output image / physical ACK.

The active governance document is tied to an older milestone SHA, therefore these ownership statements are recorded as `governance_contract` unless independently confirmed in the exact 2b72 production source. If source conflicts, exact production/design authority must be reviewed before modification.

## Host transport boundary

The exact SPIB parser defines a 32-bit request as `address[15:0] + data[15:0]`. A complete request is decoded once and generates one 32-bit response that is clocked out on the next master transaction. Accepted commands return `address + checksum(data)` in the response-address word; rejected/unknown commands return `0xFFFF0000`.

The transport's admission decision is deliberately O(1) and excludes DDS derivation, tracing, M0 transaction, physical output write, queue scan and blocking state-machine work from the SPIB response-deadline path.

## Explicit evidence boundaries

This document does **not** claim the following unless present in a machine-readable data file with `verified_source`:

- ADC analog scaling or calibration coefficients;
- protection voltage/current thresholds not present in the extracted exact source;
- hardware shutdown latency;
- an unmeasured ISR WCET;
- full AM3352 register handbook coverage;
- physical hardware safety from browser/Web Serial behavior.

Unknowns remain null/pending so downstream tools cannot silently turn assumptions into production facts.
