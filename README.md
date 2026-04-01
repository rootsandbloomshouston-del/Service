# Service

This repository contains multiple historical app snapshots (`service-app-phase*.zip`) and utilities to generate a high-signal handoff package for a downstream implementation agent.

## 1) Generate a Ripplet handoff package

```bash
python3 tools/generate_ripplet_handoff.py --project-name Service --root .
```

Outputs:
- `RIPPLET_AGENT_PROMPT.md` — ready-to-use instruction prompt for Ripplet.
- `ripplet_context.json` — machine-readable inventory of discovered phase archives.

## 2) Build a merged workspace Ripplet can execute immediately

```bash
python3 tools/prepare_ripplet_workspace.py --root . --out-dir .ripplet --clean
```

Outputs:
- `.ripplet/phases/*` — extracted contents of each zip snapshot.
- `.ripplet/merged` — consolidated file tree overlaid oldest → newest.
- `.ripplet/merge_report.json` — provenance map + conflict report.

## Recommended next flow

1. Run both commands above.
2. Point Ripplet at `.ripplet/merged` as the implementation base.
3. Give Ripplet `RIPPLET_AGENT_PROMPT.md` + `.ripplet/merge_report.json` to preserve high-value features while resolving conflicts intentionally.
