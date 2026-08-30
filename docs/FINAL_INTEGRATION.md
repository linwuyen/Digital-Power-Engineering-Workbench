# Final Workbench Integration

The browser workbench now consumes the evidence-bound `engineering_data/` layer directly.

- Engineering Truth panel shows exact production baseline, trust/status counts, source-verified SPIB contract and scalar scaling facts.
- Reference measurement/control tools display explicit production-evidence boundaries.
- Firmware State Machine view is replaced at runtime by the source-verified production SystemState vocabulary; the transition simulator is disabled because the production transition table is intentionally partial.
- Remote-control view shows source-verified protocol truth while retaining MOCK/operator-intent-only transport authority.
- Python local server exposes `/engineering_data/*` with path-traversal protection so local and Pages modes consume the same data files.
- CI gates browser integration, JSON integrity, Python regression/syntax and fail-closed pending evidence.

Hardware-only evidence remains pending until measured/qualification artifacts are bound to the pinned production baseline; it is not a software-completion claim.
