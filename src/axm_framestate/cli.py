from __future__ import annotations

import argparse
import json
from pathlib import Path

from .canonical import canonical_json, load_project
from .capabilities import analyze_requirements, capability_summary
from .forge import adopt_effect, spawn_effect
from .receipts import render_with_receipt, verify_repeat
from .snapshot import create_daily_snapshot
from .review import review_project


def _root() -> Path:
    return Path.cwd().resolve()


def _print(value: object) -> None:
    print(json.dumps(value, indent=2, sort_keys=True))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="framestate")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("inspect")
    p.add_argument("project")

    p = sub.add_parser("render")
    p.add_argument("project")
    p.add_argument("output")
    p.add_argument("--no-assemble", action="store_true")

    p = sub.add_parser("verify-repeat")
    p.add_argument("project")
    p.add_argument("output")

    p = sub.add_parser("snapshot")
    p.add_argument("--output-dir")

    p = sub.add_parser("review")
    p.add_argument("project")

    sub.add_parser("capabilities")

    p = sub.add_parser("gaps")
    p.add_argument("requirements", help="JSON file with {\"required\": [capability ids]}")

    p = sub.add_parser("spawn-effect")
    p.add_argument("candidate")
    p.add_argument("output")

    p = sub.add_parser("adopt-effect")
    p.add_argument("candidate_dir")
    p.add_argument("--reason", required=True)
    p.add_argument("--root-fit", required=True, help="JSON file containing the four-root adoption decision")

    args = parser.parse_args(argv)
    root = _root()
    if args.command == "inspect":
        project = load_project(Path(args.project))
        _print(project)
    elif args.command == "render":
        project = load_project(Path(args.project))
        _print(render_with_receipt(project, Path(args.output), root, assemble=not args.no_assemble))
    elif args.command == "verify-repeat":
        project = load_project(Path(args.project))
        result = verify_repeat(project, Path(args.output), root)
        _print(result)
        return 0 if result["passed"] else 2
    elif args.command == "snapshot":
        out = Path(args.output_dir) if args.output_dir else None
        _print(create_daily_snapshot(root, output_dir=out))
    elif args.command == "review":
        project = load_project(Path(args.project))
        _print(review_project(project, root))
    elif args.command == "capabilities":
        _print(capability_summary())
    elif args.command == "gaps":
        required = json.loads(Path(args.requirements).read_text(encoding="utf-8"))["required"]
        result = analyze_requirements(required)
        _print(result)
        return 0 if result["ready"] else 4
    elif args.command == "spawn-effect":
        _print(spawn_effect(Path(args.candidate), Path(args.output)))
    elif args.command == "adopt-effect":
        root_fit = json.loads(Path(args.root_fit).read_text(encoding="utf-8"))
        result = adopt_effect(root, Path(args.candidate_dir), args.reason, root_fit)
        _print(result)
        return 0 if result.get("adopted") else 3
    return 0
