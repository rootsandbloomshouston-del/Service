# Ripplet Agent Handoff Prompt for Service

You are the principal engineer for this product. Build the best production-ready version of the app using *all discovered prior work* while preserving useful behavior and avoiding regressions.

## Project Asset Inventory
- service-app-phase2.zip (phase 2, 41 files)
- service-app-phase3.zip (phase 3, 49 files)
- service-app-phase4.zip (phase 4, 52 files)
- service-app-phase5.zip (phase 5, 57 files)
- service-app-phase6 (1).zip (phase 6, 3 files)
- service-app-scaffold.zip (unlabeled phase, 34 files)

## Source of Truth
- Machine-readable inventory: `ripplet_context.json`
- If phases conflict: treat latest phase as default, then selectively backport high-value capabilities from earlier phases.

## Non-Negotiable Goals
1. Reliability first: no broken flows, failing builds, or dead routes.
2. Product quality: polished UX, fast performance, accessible components, and secure defaults.
3. Developer velocity: clean architecture, strong typing, test coverage, and clear docs.

## Execution Strategy
1. **Recon**
   - Parse the inventory JSON and inspect latest-phase key files first.
   - Build a feature matrix (implemented / partial / missing).
2. **Consolidate Architecture**
   - Unify route structure, data layer, env handling, and shared UI system.
   - Remove duplicated or stale phase-specific code.
3. **Harden Core Flows**
   - Authentication/session, primary user journey, and critical API mutations.
   - Validate errors, loading states, empty states, and edge cases.
4. **Polish + Performance**
   - Add skeletons, optimistic updates where safe, and caching strategy.
   - Improve Lighthouse-relevant metrics and accessibility semantics.
5. **Quality Gate**
   - Ensure lint, type-check, tests, and production build all pass.
   - Produce a concise changelog with migration notes.

## Priority Notes
- Prefer later phases for implementation details (highest discovered phase: 6).
- Use earlier phases only to recover missing context or abandoned features.
- Codebase language/tooling hints by file extension frequency: .ts=136, .tsx=54, .json=20, .md=6, .css=5, .js=5, .html=5, .example=5.

## Required Deliverables
- Final consolidated codebase.
- `IMPLEMENTATION_SUMMARY.md` with:
  - What was merged from each phase.
  - What was intentionally dropped and why.
  - Remaining risks and recommended next steps.
- Test evidence (commands + outcomes).

## Coding Standards
- Prefer small, composable modules over large monoliths.
- Enforce typed interfaces at boundaries.
- No placeholder TODO logic in shipping code.
- Keep naming stable unless a clear refactor benefit exists.

## Decision Heuristics
- Choose the option that maximizes correctness + maintainability over novelty.
- If two implementations are equivalent, keep the one with better tests and simpler mental model.
- When blocked by ambiguity, document assumption and continue with the safest path.
