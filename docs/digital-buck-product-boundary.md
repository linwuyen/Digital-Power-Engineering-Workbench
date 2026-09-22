# Digital Buck product boundary

## Public Community Edition

Path:

`training/digital-buck/`

Public content is intentionally limited to:

1. Buck physics preview.
2. ADC/divider scaling preview.
3. PWM → ADC → ISR/CLA → shadow-load timing preview.
4. One unknown-fault diagnosis challenge.
5. Product description and fail-closed checkout hook.

The public route must not link to the historical full `Circuit-Simulation/19_c2000_buck_firmware_lab/` page.

## Paid-only content

The following belongs to the paid source/delivery boundary:

- complete eight-layer guided path;
- full feedback, dynamics, safety, production and evidence labs;
- answer key;
- complete fault bank;
- production authority exercises;
- control-validation / board-evidence workflow;
- full interactive offline bundle;
- paid workbook and debug checklist.

## Cutover rule

The public route must be available before the full `linwuyen/Circuit-Simulation` repository is made private.

After cutover:

```text
Public acquisition surface
Digital-Power-Engineering-Workbench/training/digital-buck/
        ↓
Lemon Squeezy checkout
        ↓
Paid downloadable lab bundle

Private source of truth
linwuyen/Circuit-Simulation
```

Do not rely on "hidden links" as a paid boundary. If the source repository is public, the paid boundary is not effective.
