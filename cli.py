"""NovelKit CLI surface over the Hermes tool registry (Task 11.3).

Replaces the legacy React UI + bespoke scheduler (Resolved Decision #2). Every
command runs through the Orchestrator dispatch seam (:func:`delegate.delegate_tool`),
so the CLI reaches tools exactly the way the gateway and cron do — hub-and-spoke,
no specialist-to-specialist calls.

Commands::

    novelkit tools                       # list registered tools
    novelkit schedule                    # show the declarative cron jobs
    novelkit pipeline init   --state F --target-chapters N
    novelkit pipeline plan-next   --state F [--claim]
    novelkit pipeline record-result --state F --task-key K --result R [--score S]
    novelkit pipeline resume --state F
    novelkit sync   --novel PATH --chapter N
    novelkit doctor --novel PATH

The pipeline state is a plain JSON file (a stand-in for the Hermes session
store). ``init`` mints a fresh state; the other pipeline commands read it,
delegate to ``novelkit_pipeline``, and write the updated state back.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Optional

import bootstrap  # noqa: F401 — importing brings the tool surface online
from delegate import available_tools, delegate_tool
from tools.novelkit_pipeline_tool import ARC_SIZE, PipelineEngine
from tools.novelkit_pipeline_state_store import PipelineStateStore

SCHEDULE_CONFIG_PATH: Path = Path(__file__).resolve().parent / "config" / "schedule.json"


# --------------------------------------------------------------------------- #
# State helpers
# --------------------------------------------------------------------------- #


def _load_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise SystemExit(f"pipeline state not found: {path} (run 'pipeline init' first)")
    return PipelineStateStore.from_state_path(path).load_payload()


def _save_state(
    path: Path,
    state: dict[str, Any],
    *,
    expected_version: Optional[int] = None,
) -> None:
    PipelineStateStore.from_state_path(path).save(
        state,
        expected_version=expected_version,
    )


def _emit(payload: Any) -> None:
    print(json.dumps(payload, indent=2, ensure_ascii=False))


# --------------------------------------------------------------------------- #
# Command handlers
# --------------------------------------------------------------------------- #


def cmd_tools(_: argparse.Namespace) -> int:
    _emit(available_tools())
    return 0


def cmd_schedule(_: argparse.Namespace) -> int:
    if not SCHEDULE_CONFIG_PATH.exists():
        raise SystemExit(f"schedule config not found: {SCHEDULE_CONFIG_PATH}")
    _emit(json.loads(SCHEDULE_CONFIG_PATH.read_text(encoding="utf-8")))
    return 0


def cmd_pipeline_init(args: argparse.Namespace) -> int:
    engine = PipelineEngine.create(
        target_chapters=args.target_chapters,
        arc_size=args.arc_size,
        novel=args.novel or "",
        mode=args.mode,
    )
    state = engine.state.to_dict()
    _save_state(Path(args.state), state)
    _emit({"created": args.state, "tasks": len(state.get("tasks", []))})
    return 0


def cmd_pipeline_plan_next(args: argparse.Namespace) -> int:
    state_path = Path(args.state)
    state = _load_state(state_path)
    out = delegate_tool(
        "novelkit_pipeline",
        action="plan_next",
        state=state,
        claim=args.claim,
    )
    if args.claim:
        _save_state(
            state_path,
            out["state"],
            expected_version=state.get("state_version"),
        )
    _emit(out["result"])
    return 0


def cmd_pipeline_record_result(args: argparse.Namespace) -> int:
    state_path = Path(args.state)
    state = _load_state(state_path)
    out = delegate_tool(
        "novelkit_pipeline",
        action="record_result",
        state=state,
        task_key=args.task_key,
        result=args.result,
        score=args.score,
    )
    _save_state(state_path, out["state"], expected_version=state.get("state_version"))
    _emit(out["result"])
    return 0


def cmd_pipeline_resume(args: argparse.Namespace) -> int:
    state_path = Path(args.state)
    state = _load_state(state_path)
    out = delegate_tool(
        "novelkit_pipeline",
        action="resume",
        state=state,
    )
    _save_state(state_path, out["state"], expected_version=state.get("state_version"))
    _emit(out["result"])
    return 0


def cmd_sync(args: argparse.Namespace) -> int:
    report = delegate_tool(
        "novelkit_sync",
        action="commit",
        novel_path=args.novel,
        chapter=args.chapter,
    )
    _emit(report)
    return 1 if report.get("blocked") else 0


def cmd_doctor(args: argparse.Namespace) -> int:
    report = delegate_tool("novelkit_sync", action="doctor", novel_path=args.novel)
    _emit(report)
    return 1 if report.get("blocking_issues") else 0


def cmd_steer(args: argparse.Namespace) -> int:
    state_path = Path(args.state)
    state = _load_state(state_path)
    out = delegate_tool(
        "novelkit_steer", action="apply", novel_path=args.novel,
        text=args.text, state=state,
    )
    _save_state(state_path, out["state"], expected_version=state.get("state_version"))
    _emit({
        "route": out["route"], "affected_chapters": out["affected_chapters"],
        "steer_id": out["steer_id"], "applied": out["applied"],
    })
    return 0


def cmd_diag(args: argparse.Namespace) -> int:
    findings = delegate_tool(
        "novelkit_diagnostics", action="diagnose",
        novel_path=args.novel, redact=args.redact,
    )
    _emit(findings)
    return 0


def cmd_graph(args: argparse.Namespace) -> int:
    """Build / query / detect-contradictions / export the knowledge graph.

    Reaches ``novelkit_graph`` through the same ``delegate_tool`` hub the gateway
    and cron use. The CLI verb ``contradictions`` maps to the tool's
    ``detect_contradictions`` action; the rest map 1:1.
    """
    graph_action = args.graph_action
    if graph_action == "query":
        params: dict[str, Any] = {"kind": args.kind}
        if args.node is not None:
            params["node"] = args.node
        result = delegate_tool(
            "novelkit_graph", action="query", novel_path=args.novel, **params
        )
    elif graph_action == "contradictions":
        result = delegate_tool(
            "novelkit_graph", action="detect_contradictions", novel_path=args.novel
        )
    else:  # build | export
        result = delegate_tool(
            "novelkit_graph", action=graph_action, novel_path=args.novel
        )
    _emit(result)
    return 0


def cmd_compass(args: argparse.Namespace) -> int:
    if getattr(args, "migrate", False):
        if args.target_chapters is None:
            raise SystemExit("compass --migrate requires --target-chapters")
        out = delegate_tool(
            "novelkit_compass", action="migrate_to_compass", novel_path=args.novel,
            current_chapter=args.current_chapter, target_chapters=args.target_chapters,
        )
        _emit(out)
        return 0
    data = delegate_tool("novelkit_compass", action="read_compass", novel_path=args.novel)
    _emit(data if data is not None else {"compass": None})
    return 0


def cmd_stop_guard(args: argparse.Namespace) -> int:
    from tools.novelkit_longform_config import load_config
    from tools.novelkit_pipeline_tool import PipelineState
    from tools.novelkit_reminder import stop_guard

    state_path = Path(args.state)
    payload = _load_state(state_path)
    ps = PipelineState.from_dict(payload)
    # <novel>/logs/pipeline_state.json → novel root is two levels up.
    novel_root = state_path.parent.parent
    max_blocks = int(load_config(novel_root).get("MAX_STOP_BLOCKS", 3))
    blocked, reason = stop_guard(ps, max_stop_blocks=max_blocks)
    # Count consecutive stop-attempts-while-incomplete so the escalate valve is
    # reachable (Req 8.4); reset once a stop is allowed.
    ps.creative.stop_block_count = ps.creative.stop_block_count + 1 if blocked else 0
    ps.state_version += 1
    _save_state(state_path, ps.to_dict(), expected_version=payload.get("state_version"))
    _emit({"blocked": blocked, "reason": reason})
    return 2 if blocked else 0  # exit 2 => Stop hook blocks ending the run


def cmd_reminder(args: argparse.Namespace) -> int:
    from tools.novelkit_pipeline_tool import PipelineState
    from tools.novelkit_reminder import build_reminder

    state = _load_state(Path(args.state))
    print(build_reminder(PipelineState.from_dict(state)))
    return 0


# --------------------------------------------------------------------------- #
# Parser
# --------------------------------------------------------------------------- #


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="novelkit",
        description="NovelKit surface over the Hermes tool registry (hub-and-spoke).",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("tools", help="list registered tools").set_defaults(func=cmd_tools)
    sub.add_parser("schedule", help="show declarative cron jobs").set_defaults(
        func=cmd_schedule
    )

    pipeline = sub.add_parser("pipeline", help="pipeline DAG operations")
    psub = pipeline.add_subparsers(dest="pipeline_command", required=True)

    p_init = psub.add_parser("init", help="create a fresh pipeline state")
    p_init.add_argument("--state", required=True)
    p_init.add_argument("--target-chapters", type=int, default=None)
    p_init.add_argument("--arc-size", type=int, default=ARC_SIZE)
    p_init.add_argument("--novel", default=None)
    p_init.add_argument(
        "--mode", default="compass",
        choices=["full_plan", "rolling", "compass"],
        help="compass = long-form mode (bootstrap+compass only; arcs expand on demand)",
    )
    p_init.set_defaults(func=cmd_pipeline_init)

    p_plan = psub.add_parser("plan-next", help="get the next ready task")
    p_plan.add_argument("--state", required=True)
    p_plan.add_argument("--claim", action="store_true")
    p_plan.set_defaults(func=cmd_pipeline_plan_next)

    p_rec = psub.add_parser("record-result", help="record a task result")
    p_rec.add_argument("--state", required=True)
    p_rec.add_argument("--task-key", required=True)
    p_rec.add_argument(
        "--result",
        required=True,
        choices=["done", "soft_fail", "hard_fail", "blocked", "skipped"],
    )
    p_rec.add_argument("--score", type=float, default=None)
    p_rec.set_defaults(func=cmd_pipeline_record_result)

    p_res = psub.add_parser("resume", help="resume from the next ready task")
    p_res.add_argument("--state", required=True)
    p_res.set_defaults(func=cmd_pipeline_resume)

    p_sync = sub.add_parser("sync", help="commit (sync) a chapter")
    p_sync.add_argument("--novel", required=True)
    p_sync.add_argument("--chapter", type=int, required=True)
    p_sync.set_defaults(func=cmd_sync)

    p_doc = sub.add_parser("doctor", help="run the doctor health-check")
    p_doc.add_argument("--novel", required=True)
    p_doc.set_defaults(func=cmd_doctor)

    p_steer = sub.add_parser("steer", help="inject a realtime steer (intervention)")
    p_steer.add_argument("--state", required=True)
    p_steer.add_argument("--novel", required=True)
    p_steer.add_argument("--text", required=True)
    p_steer.set_defaults(func=cmd_steer)

    p_diag = sub.add_parser("diag", help="creative-health diagnostics")
    p_diag.add_argument("--novel", required=True)
    p_diag.add_argument("--redact", action="store_true")
    p_diag.set_defaults(func=cmd_diag)

    p_graph = sub.add_parser("graph", help="narrative knowledge graph")
    p_graph.add_argument(
        "graph_action",
        choices=["build", "query", "contradictions", "export"],
        help="build/query/contradictions/export the knowledge graph",
    )
    p_graph.add_argument("--novel", required=True)
    p_graph.add_argument("--kind", default=None, help="query kind (for 'query')")
    p_graph.add_argument("--node", default=None, help="focus node id (for 'query')")
    p_graph.set_defaults(func=cmd_graph)

    p_compass = sub.add_parser("compass", help="show / migrate the story compass")
    p_compass.add_argument("--novel", required=True)
    p_compass.add_argument(
        "--migrate", action="store_true",
        help="migrate an in-progress novel to compass mode (needs --target-chapters)",
    )
    p_compass.add_argument("--current-chapter", type=int, default=0)
    p_compass.add_argument("--target-chapters", type=int, default=None)
    p_compass.set_defaults(func=cmd_compass)

    p_sg = sub.add_parser("stop-guard", help="completion guard (exit 2 when blocked)")
    p_sg.add_argument("--state", required=True)
    p_sg.set_defaults(func=cmd_stop_guard)

    p_rem = sub.add_parser("reminder", help="render the per-turn system reminder")
    p_rem.add_argument("--state", required=True)
    p_rem.set_defaults(func=cmd_reminder)

    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
