#!/usr/bin/env python3
"""Create a consolidated workspace from phase zip archives.

This utility complements `generate_ripplet_handoff.py` by producing a real file tree that a
coding agent can execute against immediately.

Behavior:
- discovers `*.zip` archives in a directory
- infers phase order from names like `phase2`, `phase10`, etc.
- extracts each archive into `.ripplet/phases/<archive-stem>`
- builds `.ripplet/merged` by overlaying phases from oldest -> newest
- records per-file provenance and conflicts in `.ripplet/merge_report.json`
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from zipfile import ZipFile

PHASE_RE = re.compile(r"phase(\d+)", re.IGNORECASE)
IGNORE_SEGMENTS = {"__MACOSX"}


@dataclass(frozen=True)
class ArchiveInfo:
    path: Path
    phase: int | None


def infer_phase(path: Path) -> int | None:
    match = PHASE_RE.search(path.name)
    return int(match.group(1)) if match else None


def list_archives(root: Path) -> list[ArchiveInfo]:
    infos = [ArchiveInfo(path=p, phase=infer_phase(p)) for p in root.glob("*.zip")]
    return sorted(infos, key=lambda a: (a.phase is None, a.phase or -1, a.path.name.lower()))


def safe_rel(path: str) -> Path | None:
    rel = Path(path)
    if rel.is_absolute() or ".." in rel.parts:
        return None
    if any(part in IGNORE_SEGMENTS for part in rel.parts):
        return None
    return rel


def hash_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def prepare_dirs(base: Path, clean: bool) -> tuple[Path, Path, Path]:
    phases_dir = base / "phases"
    merged_dir = base / "merged"
    report_path = base / "merge_report.json"
    if clean and base.exists():
        shutil.rmtree(base)
    phases_dir.mkdir(parents=True, exist_ok=True)
    merged_dir.mkdir(parents=True, exist_ok=True)
    return phases_dir, merged_dir, report_path


def extract_archive(archive: ArchiveInfo, target_dir: Path) -> list[Path]:
    extracted: list[Path] = []
    with ZipFile(archive.path) as zf:
        for name in zf.namelist():
            if name.endswith("/"):
                continue
            rel = safe_rel(name)
            if rel is None:
                continue
            out_path = target_dir / rel
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_bytes(zf.read(name))
            extracted.append(rel)
    return extracted


def overlay_phase(
    archive: ArchiveInfo,
    phase_dir: Path,
    merged_dir: Path,
    provenance: dict[str, dict[str, str]],
    conflicts: list[dict[str, str]],
) -> None:
    for file_path in phase_dir.rglob("*"):
        if not file_path.is_file():
            continue
        rel = file_path.relative_to(phase_dir)
        key = rel.as_posix()
        payload = file_path.read_bytes()
        digest = hash_bytes(payload)

        merged_target = merged_dir / rel
        merged_target.parent.mkdir(parents=True, exist_ok=True)

        if merged_target.exists():
            old_payload = merged_target.read_bytes()
            old_digest = hash_bytes(old_payload)
            if old_digest != digest:
                previous = provenance.get(key, {})
                conflicts.append(
                    {
                        "path": key,
                        "replaced_by": archive.path.name,
                        "replaced_phase": str(archive.phase),
                        "previous_archive": previous.get("archive", "unknown"),
                        "previous_phase": previous.get("phase", "unknown"),
                    }
                )

        merged_target.write_bytes(payload)
        provenance[key] = {
            "archive": archive.path.name,
            "phase": str(archive.phase),
            "sha256": digest,
        }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Root directory containing zip archives.")
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path(".ripplet"),
        help="Output directory for extracted phases, merged tree, and report.",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Delete the output directory before rebuilding.",
    )
    args = parser.parse_args()

    archives = list_archives(args.root)
    phases_dir, merged_dir, report_path = prepare_dirs(args.out_dir, clean=args.clean)

    provenance: dict[str, dict[str, str]] = {}
    conflicts: list[dict[str, str]] = []
    archive_reports: list[dict[str, object]] = []

    for archive in archives:
        phase_name = archive.path.stem.replace(" ", "_")
        phase_dir = phases_dir / phase_name
        extracted = extract_archive(archive, phase_dir)
        overlay_phase(archive, phase_dir, merged_dir, provenance, conflicts)
        archive_reports.append(
            {
                "archive": archive.path.name,
                "phase": archive.phase,
                "extracted_files": len(extracted),
                "phase_dir": str(phase_dir),
            }
        )

    report = {
        "archive_count": len(archives),
        "archives": archive_reports,
        "merged_dir": str(merged_dir),
        "provenance_count": len(provenance),
        "conflict_count": len(conflicts),
        "conflicts": conflicts[:200],
        "provenance": provenance,
    }
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    print(f"Prepared workspace at {args.out_dir}")
    print(f"Merged files: {len(provenance)}")
    print(f"Conflicts detected: {len(conflicts)}")


if __name__ == "__main__":
    main()
