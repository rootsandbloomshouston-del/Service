#!/usr/bin/env python3
"""Generate a high-signal handoff prompt for a downstream coding agent (e.g., Ripplet).

The script scans local phase zip archives, builds an inventory, and produces:
1) A concise execution brief with priorities and constraints.
2) A machine-readable context file containing discovered assets.

This is designed for repositories where prior work is delivered as multiple zip snapshots.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from zipfile import ZipFile


ARCHIVE_PATTERN = re.compile(r"phase(\d+)", re.IGNORECASE)


@dataclass
class ArchiveSummary:
    archive_name: str
    phase: int | None
    total_files: int
    top_level_dirs: list[str]
    extension_counts: dict[str, int]
    key_files: list[str]


def discover_archives(root: Path) -> list[Path]:
    return sorted(root.glob("*.zip"), key=lambda p: p.name.lower())


def infer_phase(name: str) -> int | None:
    match = ARCHIVE_PATTERN.search(name)
    return int(match.group(1)) if match else None


def summarize_archive(path: Path, key_file_limit: int = 20) -> ArchiveSummary:
    ext_counter: Counter[str] = Counter()
    top_level_counter: Counter[str] = Counter()
    key_files: list[str] = []

    with ZipFile(path) as zf:
        members = [m for m in zf.namelist() if not m.endswith("/")]

        for member in members:
            parts = Path(member).parts
            if parts:
                top_level_counter[parts[0]] += 1
            ext = Path(member).suffix.lower() or "<none>"
            ext_counter[ext] += 1

        priority_fragments = (
            "readme",
            "package.json",
            "pnpm-lock",
            "yarn.lock",
            "requirements.txt",
            "pyproject.toml",
            "dockerfile",
            "next.config",
            "vite.config",
            "tsconfig",
            "eslint",
            "tailwind",
            "schema.prisma",
            "openapi",
            "api",
            "src/",
            "app/",
        )

        def score(file_path: str) -> tuple[int, int, str]:
            lowered = file_path.lower()
            hit_count = sum(fragment in lowered for fragment in priority_fragments)
            depth = lowered.count("/")
            return (-hit_count, depth, lowered)

        key_files = sorted(members, key=score)[:key_file_limit]

    return ArchiveSummary(
        archive_name=path.name,
        phase=infer_phase(path.name),
        total_files=len(members),
        top_level_dirs=[d for d, _ in top_level_counter.most_common(12)],
        extension_counts=dict(ext_counter.most_common(16)),
        key_files=key_files,
    )


def build_priority_notes(summaries: list[ArchiveSummary]) -> list[str]:
    phases = [s.phase for s in summaries if s.phase is not None]
    notes: list[str] = []
    if phases:
        notes.append(
            f"Prefer later phases for implementation details (highest discovered phase: {max(phases)})."
        )
    notes.append("Use earlier phases only to recover missing context or abandoned features.")

    merged_extensions: defaultdict[str, int] = defaultdict(int)
    for summary in summaries:
        for ext, count in summary.extension_counts.items():
            merged_extensions[ext] += count

    dominant = sorted(merged_extensions.items(), key=lambda x: x[1], reverse=True)[:8]
    if dominant:
        notes.append(
            "Codebase language/tooling hints by file extension frequency: "
            + ", ".join(f"{ext}={count}" for ext, count in dominant)
            + "."
        )
    return notes


def build_prompt(project_name: str, summaries: list[ArchiveSummary], context_file: str) -> str:
    inventory_lines = []
    for summary in summaries:
        phase_text = f"phase {summary.phase}" if summary.phase is not None else "unlabeled phase"
        inventory_lines.append(
            f"- {summary.archive_name} ({phase_text}, {summary.total_files} files)"
        )

    priority_notes = build_priority_notes(summaries)
    priority_block = "\n".join(f"- {note}" for note in priority_notes)

    return f"""# Ripplet Agent Handoff Prompt for {project_name}

You are the principal engineer for this product. Build the best production-ready version of the app using *all discovered prior work* while preserving useful behavior and avoiding regressions.

## Project Asset Inventory
{chr(10).join(inventory_lines) if inventory_lines else '- No zip archives discovered.'}

## Source of Truth
- Machine-readable inventory: `{context_file}`
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
{priority_block}

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
"""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Project root to scan.")
    parser.add_argument(
        "--project-name",
        default="Service",
        help="Display name used in generated prompt.",
    )
    parser.add_argument(
        "--out-prompt",
        type=Path,
        default=Path("RIPPLET_AGENT_PROMPT.md"),
        help="Output markdown prompt file.",
    )
    parser.add_argument(
        "--out-context",
        type=Path,
        default=Path("ripplet_context.json"),
        help="Output JSON context file.",
    )
    args = parser.parse_args()

    archives = discover_archives(args.root)
    summaries = [summarize_archive(path) for path in archives]

    context = {
        "project": args.project_name,
        "archive_count": len(summaries),
        "archives": [
            {
                "archive_name": s.archive_name,
                "phase": s.phase,
                "total_files": s.total_files,
                "top_level_dirs": s.top_level_dirs,
                "extension_counts": s.extension_counts,
                "key_files": s.key_files,
            }
            for s in summaries
        ],
    }

    args.out_context.write_text(json.dumps(context, indent=2) + "\n", encoding="utf-8")
    prompt = build_prompt(args.project_name, summaries, args.out_context.name)
    args.out_prompt.write_text(prompt, encoding="utf-8")

    print(f"Generated {args.out_prompt} and {args.out_context} from {len(summaries)} archives.")


if __name__ == "__main__":
    main()
