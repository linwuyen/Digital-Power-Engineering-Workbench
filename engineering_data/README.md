# Engineering Data Source

This directory is the machine-readable / human-readable engineering truth layer for Digital Power Engineering Workbench.

## Baseline

- Production repository: `linwuyen/ASR5K_v2_28384`
- Formal branch: `feat/voltage-slew-runtime-complete`
- Exact production commit: `2b72f50648d86c11547645882248eed69f12892f`
- Dataset schema: `1.0`

The production repository is read-only from this project. This dataset is a derived index; it never overrides production source or higher-tier design documents.

## Trust model

Every engineering fact is classified as one of:

- `verified_source` — directly supported by the exact production baseline.
- `governance_contract` — supported by the active ASR5K architecture/governance contract, but may describe a different milestone SHA; production source wins on conflict.
- `derived` — calculated or summarized from verified facts; the derivation must be stated.
- `pending_verification` — value intentionally unknown. Consumers MUST NOT infer or substitute a value.

## Consumer rule

Workbench, AI agents, host simulators, HIL tests and report generators may consume this directory. They MUST:

1. bind data to the declared baseline;
2. reject unknown required fields rather than invent values;
3. treat safety/protection authority as firmware/hardware authority, never browser authority;
4. preserve one physical/timing owner per resource;
5. report source conflicts instead of silently choosing a lower-tier source.

## Primary data sets

- `baselines/manifest-2b72f506.json` — baseline identity and evidence scope.
- `architecture/ownership_matrix.json` — decision / physical actuator ownership.
- `architecture/dataflow.json` — command, state and safety data paths.
- `firmware/state_machine.json` — SystemState, fault state and power-sequence vocabulary.
- `firmware/protection_matrix.json` — verified protection sources plus explicit unknowns.
- `firmware/signals.json` — named production signals/diagnostics.
- `firmware/scaling.json` — engineering-unit scaling; unknown calibration stays null.
- `firmware/timing_budget.json` — verified software ceilings and unverified timing budgets.
- `protocol/host_protocol.json` — SPIB request/response wire contract.
- `protocol/command_dictionary.json` — transport-neutral host intents and verified wire registers.
- `verification/verification_matrix.json` — what this dataset proves and does not prove.
- `ai/safety_invariants.json` — non-negotiable safety invariants for AI/code review.
- `ai/evidence_index.json` — evidence locator for every source family.

## Evidence hierarchy

1. Current explicit instruction / formal design documents.
2. Exact production source at the declared baseline.
3. Active architecture contracts in `ASR5K_AGENT`.
4. Verification evidence.
5. This derived Workbench dataset.

A generated document is navigation and normalization, not a new architecture authority.
