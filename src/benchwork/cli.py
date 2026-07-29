"""Command-line interface for the first Athanor milestone."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from .athanor import Athanor, AthanorError
from .circle import CapsuleStore, CapabilityRegistry, Ward
from .hosts import ClaudeCodeHostAdapter, CodexHostAdapter, HOSTS
from .rites import RiteRegistry


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="bwork", description="Benchwork Athanor foundation")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("init", help="initialize a local Benchwork project")
    subparsers.add_parser("status", help="show rebuilt canonical state")
    subparsers.add_parser("doctor", help="verify Chronicle receipts and chain")

    program = subparsers.add_parser("program", help="manage Research Programs")
    program_commands = program.add_subparsers(dest="program_command", required=True)
    create = program_commands.add_parser("create", help="create a Research Program")
    create.add_argument("slug")
    create.add_argument("--title", required=True)
    create.add_argument("--problem", default="")

    protocol = subparsers.add_parser("protocol", help="manage Protocols")
    protocol_commands = protocol.add_subparsers(dest="protocol_command", required=True)
    draft = protocol_commands.add_parser("draft", help="create a Protocol draft")
    draft.add_argument("protocol_id")
    draft.add_argument("--program", required=True)
    draft.add_argument("--title", required=True)
    draft.add_argument("--analysis-plan", required=True)
    seal = protocol_commands.add_parser("seal", help="seal a drafted Protocol")
    seal.add_argument("protocol_id")

    capability = subparsers.add_parser("capability", help="inspect Capability contracts")
    capability_commands = capability.add_subparsers(dest="capability_command", required=True)
    capability_commands.add_parser("list", help="list installed Capability contracts")

    task = subparsers.add_parser("task", help="create or inspect Task Capsules")
    task_commands = task.add_subparsers(dest="task_command", required=True)
    task_create = task_commands.add_parser("create", help="create a bounded Task Capsule")
    task_create.add_argument("capability")
    task_create.add_argument("--input-sigil", required=True)
    task_create.add_argument("--tool", action="append", default=[])
    task_create.add_argument("--time-budget", type=int, required=True)
    task_create.add_argument("--network", action="store_true")
    task_show = task_commands.add_parser("show", help="show a Task Capsule")
    task_show.add_argument("task_id")

    ward = subparsers.add_parser("ward", help="evaluate Circle policy")
    ward_commands = ward.add_subparsers(dest="ward_command", required=True)
    ward_check = ward_commands.add_parser("check", help="check a Task Capsule against Ward policy")
    ward_check.add_argument("task_id")

    approval = subparsers.add_parser("approval", help="record explicit human approval")
    approval_commands = approval.add_subparsers(dest="approval_command", required=True)
    approval_grant = approval_commands.add_parser("grant", help="grant a Task Capsule approval")
    approval_grant.add_argument("task_id")
    approval_grant.add_argument("--reason", required=True)

    host = subparsers.add_parser("host", help="create provider-neutral host proposals")
    host_commands = host.add_subparsers(dest="host_command", required=True)
    host_commands.add_parser("list", help="list supported host adapters")
    propose = host_commands.add_parser("propose", help="create and check a Host Task Capsule")
    propose.add_argument("host", choices=HOSTS)
    propose.add_argument("capability")
    propose.add_argument("--input-sigil", required=True)
    propose.add_argument("--tool", action="append", default=[])
    propose.add_argument("--time-budget", type=int, required=True)
    propose.add_argument("--network", action="store_true")

    rite = subparsers.add_parser("rite", help="inspect versioned workflow definitions")
    rite_commands = rite.add_subparsers(dest="rite_command", required=True)
    rite_commands.add_parser("list", help="list installed Rites")

    working = subparsers.add_parser("working", help="manage Rite executions")
    working_commands = working.add_subparsers(dest="working_command", required=True)
    working_start = working_commands.add_parser("start", help="start a Protocol-bound Working")
    working_start.add_argument("rite_id")
    working_start.add_argument("--program", required=True)
    working_start.add_argument("--protocol", required=True)
    working_show = working_commands.add_parser("show", help="show a Working projection")
    working_show.add_argument("working_id")
    working_advance = working_commands.add_parser("advance", help="advance a Working one stage")
    working_advance.add_argument("working_id")
    working_advance.add_argument("--reason", required=True)
    working_advance.add_argument(
        "--artifact",
        action="append",
        default=[],
        metavar="KIND|URI|SHA256",
        help="typed artifact reference; repeatable",
    )

    trace = subparsers.add_parser("trace", help="show Chronicle events for an object")
    trace.add_argument("object_id")
    return parser


def _print_receipt(message: str, receipt_id: str, sigil: str) -> None:
    print(f"{message}\nReceipt {receipt_id}  {sigil}")


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    root = Path.cwd()
    athanor = Athanor(root)
    registry = CapabilityRegistry(root)
    capsules = CapsuleStore(root)
    rites = RiteRegistry(root)
    try:
        if args.command == "init":
            athanor.initialize()
            registry.initialize()
            rites.initialize()
            print("BENCHWORK · ATHANOR\nChronicle initialized at .benchwork/chronicle.jsonl")
        elif args.command == "program":
            problem = {"statement": args.problem} if args.problem else {}
            program_id, receipt = athanor.create_program(args.slug, args.title, problem)
            _print_receipt(f"Research Program {program_id} created", receipt.receipt_id, receipt.sigil)
        elif args.command == "protocol" and args.protocol_command == "draft":
            receipt = athanor.draft_protocol(args.protocol_id, args.program, args.title, args.analysis_plan)
            _print_receipt(f"Protocol {args.protocol_id} drafted", receipt.receipt_id, receipt.sigil)
        elif args.command == "protocol":
            receipt = athanor.seal_protocol(args.protocol_id)
            _print_receipt(f"Protocol {args.protocol_id} sealed", receipt.receipt_id, receipt.sigil)
        elif args.command == "capability":
            print(json.dumps(registry.capabilities(), indent=2))
        elif args.command == "task" and args.task_command == "create":
            registry.get(args.capability)
            capsule = capsules.create(
                args.capability,
                args.input_sigil,
                {"tools": args.tool, "time_budget_seconds": args.time_budget, "network": args.network},
            )
            decision = Ward(registry, athanor.approvals()).evaluate(capsule)
            print(json.dumps({"task_id": capsule["task_id"], "ward": decision.as_dict()}, indent=2))
        elif args.command == "task":
            print(json.dumps(capsules.get(args.task_id), indent=2))
        elif args.command == "ward":
            capsule = capsules.get(args.task_id)
            decision = Ward(registry, athanor.approvals()).evaluate(capsule)
            print(json.dumps(decision.as_dict(), indent=2))
            return 0 if decision.status == "PASS" else 2
        elif args.command == "approval":
            if not capsules.get(args.task_id):
                raise AthanorError(f"unknown Task Capsule: {args.task_id}")
            receipt = athanor.grant_approval(capsules.get(args.task_id), args.reason)
            _print_receipt(f"Approval granted for {args.task_id}", receipt.receipt_id, receipt.sigil)
        elif args.command == "host" and args.host_command == "list":
            print(json.dumps({"hosts": HOSTS}, indent=2))
        elif args.command == "host":
            adapter_class = CodexHostAdapter if args.host == "codex" else ClaudeCodeHostAdapter
            proposal = adapter_class(athanor, registry, capsules).propose(
                args.capability, args.input_sigil, args.tool, args.time_budget, args.network
            )
            print(json.dumps(proposal.as_dict(), indent=2))
            return 0 if proposal.ward.status == "PASS" else 2
        elif args.command == "rite":
            print(json.dumps(rites.rites(), indent=2))
        elif args.command == "working" and args.working_command == "start":
            rites.get(args.rite_id)
            working_id, receipt = athanor.create_working(args.rite_id, args.program, args.protocol)
            _print_receipt(f"Working {working_id} started", receipt.receipt_id, receipt.sigil)
        elif args.command == "working" and args.working_command == "show":
            try:
                working = athanor.workings()[args.working_id]
            except KeyError as error:
                raise AthanorError(f"unknown Working: {args.working_id}") from error
            print(json.dumps(working, indent=2))
        elif args.command == "working":
            artifacts = []
            for value in args.artifact:
                try:
                    kind, uri, digest = value.split("|", 2)
                except ValueError as error:
                    raise AthanorError("artifact must use KIND|URI|SHA256") from error
                artifacts.append({"kind": kind, "uri": uri, "sigil": digest})
            receipt = athanor.advance_working(args.working_id, args.reason, artifacts)
            _print_receipt(f"Working {args.working_id} advanced", receipt.receipt_id, receipt.sigil)
        elif args.command == "status":
            print(json.dumps(athanor.replay(), indent=2))
        elif args.command == "doctor":
            event_count = len(athanor.chronicle.events())
            print(f"Chronicle healthy: {event_count} verified event(s), receipt chain intact")
        elif args.command == "trace":
            print(json.dumps(athanor.trace(args.object_id), indent=2))
    except AthanorError as error:
        print(f"Athanor rejected transition: {error}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
