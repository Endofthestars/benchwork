"""Command-line interface for Benchwork's canonical research transitions."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from .athanor import Athanor, AthanorError, content_sigil
from .circle import CapsuleStore, CapabilityRegistry, Ward
from .grimoire import rite_definition_sigil
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
    draft.add_argument("--hypothesis", action="append", default=[])
    seal = protocol_commands.add_parser("seal", help="seal a drafted Protocol")
    seal.add_argument("protocol_id")

    evidence = subparsers.add_parser("evidence", help="record and verify Evidence")
    evidence_commands = evidence.add_subparsers(dest="evidence_command", required=True)
    evidence_record = evidence_commands.add_parser("record", help="record a sourced observation")
    evidence_record.add_argument("evidence_id")
    evidence_record.add_argument("--program", required=True)
    evidence_record.add_argument("--source", required=True, metavar="URI|SHA256")
    evidence_record.add_argument("--observation", required=True)
    evidence_record.add_argument("--source-resolved", action="store_true")
    evidence_record.add_argument("--content-inspected", action="store_true")
    evidence_record.add_argument("--locally-reproduced", action="store_true")
    evidence_verify = evidence_commands.add_parser("verify", help="mark Evidence checks complete")
    evidence_verify.add_argument("evidence_id")
    evidence_verify.add_argument(
        "--check",
        action="append",
        required=True,
        choices=(
            "source_resolved",
            "content_inspected",
            "claim_relation_verified",
            "locally_reproduced",
        ),
    )
    evidence_show = evidence_commands.add_parser("show", help="show an Evidence projection")
    evidence_show.add_argument("evidence_id")

    claim = subparsers.add_parser("claim", help="manage evidence-backed Claims")
    claim_commands = claim.add_subparsers(dest="claim_command", required=True)
    claim_create = claim_commands.add_parser("create", help="create a Claim from verified Evidence")
    claim_create.add_argument("claim_id")
    claim_create.add_argument("--program", required=True)
    claim_create.add_argument(
        "--type",
        required=True,
        choices=("empirical", "theoretical", "methodological", "operational"),
    )
    claim_create.add_argument("--statement", required=True)
    claim_create.add_argument(
        "--evidence",
        action="append",
        required=True,
        metavar="EV-ID|RELATION",
    )
    claim_show = claim_commands.add_parser("show", help="show a Claim projection")
    claim_show.add_argument("claim_id")

    hypothesis = subparsers.add_parser("hypothesis", help="manage Claim-backed Hypotheses")
    hypothesis_commands = hypothesis.add_subparsers(dest="hypothesis_command", required=True)
    hypothesis_create = hypothesis_commands.add_parser("create", help="create a falsifiable Hypothesis")
    hypothesis_create.add_argument("hypothesis_id")
    hypothesis_create.add_argument("--program", required=True)
    hypothesis_create.add_argument("--claim", action="append", required=True)
    hypothesis_create.add_argument("--statement", required=True)
    hypothesis_create.add_argument("--prediction", required=True)
    hypothesis_show = hypothesis_commands.add_parser("show", help="show a Hypothesis projection")
    hypothesis_show.add_argument("hypothesis_id")

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

    grimoire = subparsers.add_parser("grimoire", help="manage pinned data-only extensions")
    grimoire_commands = grimoire.add_subparsers(dest="grimoire_command", required=True)
    grimoire_commands.add_parser("list", help="list installed Grimoires")
    grimoire_install = grimoire_commands.add_parser("install", help="install a local Grimoire directory")
    grimoire_install.add_argument("source", type=Path)
    grimoire_show = grimoire_commands.add_parser("show", help="show an installed Grimoire")
    grimoire_show.add_argument("grimoire_ref")
    grimoire_sigil = grimoire_commands.add_parser("sigil", help="compute a canonical Rite definition Sigil")
    grimoire_sigil.add_argument("rite_file", type=Path)

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

    experiment = subparsers.add_parser("experiment", help="manage Protocol-bound Experiments")
    experiment_commands = experiment.add_subparsers(dest="experiment_command", required=True)
    experiment_create = experiment_commands.add_parser("create", help="create an Experiment")
    experiment_create.add_argument("experiment_id")
    experiment_create.add_argument("--program", required=True)
    experiment_create.add_argument("--protocol", required=True)
    experiment_create.add_argument("--question", required=True)
    experiment_create.add_argument("--hypothesis")

    run = subparsers.add_parser("run", help="record immutable experimental Runs")
    run_commands = run.add_subparsers(dest="run_command", required=True)
    run_record = run_commands.add_parser("record", help="record a Run and its observed metrics")
    run_record.add_argument("run_id")
    run_record.add_argument("--experiment", required=True)
    run_record.add_argument(
        "--status",
        required=True,
        choices=("QUEUED", "RUNNING", "COMPLETED", "FAILED", "CANCELLED", "LOST"),
    )
    run_record.add_argument("--include", action="store_true", help="include this Run in primary analysis")
    run_record.add_argument("--seed", type=int)
    run_record.add_argument("--metric", action="append", default=[], metavar="NAME=VALUE")
    run_record.add_argument("--artifact", action="append", default=[], metavar="URI|SHA256")

    analyze = subparsers.add_parser("analyze", help="compute a deterministic Alembic Result Bundle")
    analyze.add_argument("--program", required=True)
    analyze.add_argument("--protocol", required=True)

    review = subparsers.add_parser("review", help="record a scientific Assessment")
    review.add_argument("result_bundle_id")
    review.add_argument("--summary", required=True)
    review.add_argument("--limitation", action="append", default=[])
    review.add_argument(
        "--claim-finding",
        action="append",
        default=[],
        metavar="CL-ID|STATUS|RATIONALE",
    )
    review.add_argument(
        "--hypothesis-finding",
        action="append",
        required=True,
        metavar="HY-ID|STATUS|RATIONALE",
    )

    assessment = subparsers.add_parser("assessment", help="inspect scientific Assessments")
    assessment_commands = assessment.add_subparsers(dest="assessment_command", required=True)
    assessment_commands.add_parser("list", help="list completed Assessments")
    assessment_show = assessment_commands.add_parser("show", help="show an Assessment")
    assessment_show.add_argument("assessment_id")

    decide = subparsers.add_parser("decide", help="Seal a human scientific Decision")
    decide.add_argument("--program", required=True)
    decide.add_argument(
        "--outcome",
        required=True,
        choices=(
            "CONTINUE",
            "REPAIR",
            "PIVOT",
            "STOP",
            "INSUFFICIENT_EVIDENCE",
            "REVIEW_REQUIRED",
        ),
    )
    decide.add_argument("--assessment", action="append", required=True)
    decide.add_argument("--rationale", required=True)

    decision = subparsers.add_parser("decision", help="inspect sealed Decisions")
    decision_commands = decision.add_subparsers(dest="decision_command", required=True)
    decision_commands.add_parser("list", help="list sealed Decisions")
    decision_show = decision_commands.add_parser("show", help="show a Decision")
    decision_show.add_argument("decision_id")

    artifact = subparsers.add_parser("artifact", help="register and inspect canonical Artifacts")
    artifact_commands = artifact.add_subparsers(dest="artifact_command", required=True)
    artifact_register = artifact_commands.add_parser(
        "register", help="register a content-addressed Artifact"
    )
    artifact_register.add_argument("artifact_id")
    artifact_register.add_argument("--program", required=True)
    artifact_register.add_argument("--kind", required=True)
    artifact_register.add_argument("--location", required=True, metavar="URI|SHA256")
    artifact_register.add_argument("--producer", required=True)
    artifact_register.add_argument("--input", action="append", default=[])
    artifact_commands.add_parser("list", help="list canonical Artifacts")
    artifact_show = artifact_commands.add_parser("show", help="show an Artifact")
    artifact_show.add_argument("artifact_id")

    issue = subparsers.add_parser("issue", help="manage research Issues")
    issue_commands = issue.add_subparsers(dest="issue_command", required=True)
    issue_open = issue_commands.add_parser("open", help="open a traceable Issue")
    issue_open.add_argument("issue_id")
    issue_open.add_argument("--program", required=True)
    issue_open.add_argument("--subject", action="append", required=True)
    issue_open.add_argument(
        "--severity",
        required=True,
        choices=("LOW", "MEDIUM", "HIGH", "CRITICAL"),
    )
    issue_open.add_argument("--title", required=True)
    issue_open.add_argument("--description", required=True)
    issue_resolve = issue_commands.add_parser("resolve", help="resolve an open Issue")
    issue_resolve.add_argument("issue_id")
    issue_resolve.add_argument("--resolution", required=True)
    issue_commands.add_parser("list", help="list research Issues")
    issue_show = issue_commands.add_parser("show", help="show an Issue")
    issue_show.add_argument("issue_id")

    deviation = subparsers.add_parser("deviation", help="record Protocol Deviations")
    deviation_commands = deviation.add_subparsers(dest="deviation_command", required=True)
    deviation_record = deviation_commands.add_parser(
        "record", help="record a change after Protocol Seal"
    )
    deviation_record.add_argument("deviation_id")
    deviation_record.add_argument("--protocol", required=True)
    deviation_record.add_argument(
        "--kind",
        required=True,
        choices=("PLANNED", "UNPLANNED"),
    )
    deviation_record.add_argument("--summary", required=True)
    deviation_record.add_argument("--rationale", required=True)
    deviation_record.add_argument(
        "--impact",
        required=True,
        choices=("NONE", "MINOR", "MAJOR", "INVALIDATING"),
    )
    deviation_record.add_argument("--affected", action="append", default=[])
    deviation_commands.add_parser("list", help="list Protocol Deviations")
    deviation_show = deviation_commands.add_parser("show", help="show a Deviation")
    deviation_show.add_argument("deviation_id")

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
            receipt = athanor.draft_protocol(
                args.protocol_id,
                args.program,
                args.title,
                args.analysis_plan,
                args.hypothesis,
            )
            _print_receipt(f"Protocol {args.protocol_id} drafted", receipt.receipt_id, receipt.sigil)
        elif args.command == "protocol":
            receipt = athanor.seal_protocol(args.protocol_id)
            _print_receipt(f"Protocol {args.protocol_id} sealed", receipt.receipt_id, receipt.sigil)
        elif args.command == "evidence" and args.evidence_command == "record":
            try:
                uri, digest = args.source.split("|", 1)
            except ValueError as error:
                raise AthanorError("Evidence source must use URI|SHA256") from error
            verification = {
                "source_resolved": args.source_resolved,
                "content_inspected": args.content_inspected,
                "claim_relation_verified": False,
                "locally_reproduced": args.locally_reproduced,
            }
            receipt = athanor.record_evidence(
                args.evidence_id,
                args.program,
                {"uri": uri, "sigil": digest},
                args.observation,
                verification,
            )
            _print_receipt(f"Evidence {args.evidence_id} recorded", receipt.receipt_id, receipt.sigil)
        elif args.command == "evidence" and args.evidence_command == "verify":
            receipt = athanor.verify_evidence(args.evidence_id, args.check)
            _print_receipt(f"Evidence {args.evidence_id} verified", receipt.receipt_id, receipt.sigil)
        elif args.command == "evidence":
            try:
                record = athanor.evidence()[args.evidence_id]
            except KeyError as error:
                raise AthanorError(f"unknown Evidence: {args.evidence_id}") from error
            print(json.dumps(record, indent=2))
        elif args.command == "claim" and args.claim_command == "create":
            relations = []
            for value in args.evidence:
                try:
                    evidence_id, relation = value.split("|", 1)
                except ValueError as error:
                    raise AthanorError("Claim Evidence must use EV-ID|RELATION") from error
                relations.append({"evidence_id": evidence_id, "relation": relation})
            receipt = athanor.create_claim(
                args.claim_id,
                args.program,
                args.type,
                args.statement,
                relations,
            )
            _print_receipt(f"Claim {args.claim_id} created", receipt.receipt_id, receipt.sigil)
        elif args.command == "claim":
            try:
                claim = athanor.claims()[args.claim_id]
            except KeyError as error:
                raise AthanorError(f"unknown Claim: {args.claim_id}") from error
            print(json.dumps(claim, indent=2))
        elif args.command == "hypothesis" and args.hypothesis_command == "create":
            receipt = athanor.create_hypothesis(
                args.hypothesis_id,
                args.program,
                args.claim,
                args.statement,
                args.prediction,
            )
            _print_receipt(
                f"Hypothesis {args.hypothesis_id} created",
                receipt.receipt_id,
                receipt.sigil,
            )
        elif args.command == "hypothesis":
            try:
                hypothesis = athanor.hypotheses()[args.hypothesis_id]
            except KeyError as error:
                raise AthanorError(f"unknown Hypothesis: {args.hypothesis_id}") from error
            print(json.dumps(hypothesis, indent=2))
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
        elif args.command == "grimoire" and args.grimoire_command == "install":
            grimoire_ref, manifest_sigil, installed = rites.install_grimoire(args.source)
            disposition = "installed" if installed else "already installed"
            print(f"Grimoire {grimoire_ref} {disposition}\nManifest {manifest_sigil}")
        elif args.command == "grimoire" and args.grimoire_command == "show":
            try:
                grimoire = rites.grimoires()[args.grimoire_ref]
            except KeyError as error:
                raise AthanorError(f"unknown Grimoire: {args.grimoire_ref}") from error
            print(json.dumps(grimoire, indent=2))
        elif args.command == "grimoire" and args.grimoire_command == "sigil":
            print(rite_definition_sigil(args.rite_file))
        elif args.command == "grimoire":
            print(json.dumps(rites.grimoires(), indent=2))
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
        elif args.command == "experiment":
            receipt = athanor.create_experiment(
                args.experiment_id,
                args.program,
                args.protocol,
                args.question,
                args.hypothesis,
            )
            _print_receipt(f"Experiment {args.experiment_id} created", receipt.receipt_id, receipt.sigil)
        elif args.command == "run":
            metrics: dict[str, float] = {}
            for value in args.metric:
                try:
                    name, raw_number = value.split("=", 1)
                    if name in metrics:
                        raise AthanorError(f"duplicate metric: {name}")
                    metrics[name] = float(raw_number)
                except ValueError as error:
                    raise AthanorError("metric must use NAME=NUMBER") from error
            artifacts = []
            for value in args.artifact:
                try:
                    uri, digest = value.split("|", 1)
                except ValueError as error:
                    raise AthanorError("Run artifact must use URI|SHA256") from error
                artifacts.append({"uri": uri, "sigil": digest})
            receipt = athanor.record_run(
                args.run_id,
                args.experiment,
                args.status,
                args.include,
                metrics,
                args.seed,
                artifacts,
            )
            run_sigil = content_sigil(athanor.runs()[args.run_id])
            _print_receipt(
                f"Run {args.run_id} recorded\nRun {run_sigil}",
                receipt.receipt_id,
                receipt.sigil,
            )
        elif args.command == "analyze":
            bundle, bundle_sigil, receipt, path = athanor.compute_analysis(args.program, args.protocol)
            relative_path = path.relative_to(root)
            _print_receipt(
                f"Result Bundle {bundle['bundle_id']} written to {relative_path}\nBundle {bundle_sigil}",
                receipt.receipt_id,
                receipt.sigil,
            )
        elif args.command == "review":
            claim_findings = []
            for value in args.claim_finding:
                try:
                    claim_id, status, rationale = value.split("|", 2)
                except ValueError as error:
                    raise AthanorError(
                        "Claim finding must use CL-ID|STATUS|RATIONALE"
                    ) from error
                claim_findings.append(
                    {"claim_id": claim_id, "status": status, "rationale": rationale}
                )
            hypothesis_findings = []
            for value in args.hypothesis_finding:
                try:
                    hypothesis_id, status, rationale = value.split("|", 2)
                except ValueError as error:
                    raise AthanorError(
                        "Hypothesis finding must use HY-ID|STATUS|RATIONALE"
                    ) from error
                hypothesis_findings.append(
                    {
                        "hypothesis_id": hypothesis_id,
                        "status": status,
                        "rationale": rationale,
                    }
                )
            assessment_id, receipt = athanor.review_result(
                args.result_bundle_id,
                args.summary,
                args.limitation,
                claim_findings,
                hypothesis_findings,
            )
            _print_receipt(
                f"Assessment {assessment_id} completed",
                receipt.receipt_id,
                receipt.sigil,
            )
        elif args.command == "assessment" and args.assessment_command == "show":
            try:
                assessment = athanor.assessments()[args.assessment_id]
            except KeyError as error:
                raise AthanorError(f"unknown Assessment: {args.assessment_id}") from error
            print(json.dumps(assessment, indent=2))
        elif args.command == "assessment":
            print(json.dumps(athanor.assessments(), indent=2))
        elif args.command == "decide":
            decision_id, receipt = athanor.seal_decision(
                args.program,
                args.outcome,
                args.assessment,
                args.rationale,
            )
            _print_receipt(
                f"Decision {decision_id} sealed",
                receipt.receipt_id,
                receipt.sigil,
            )
        elif args.command == "decision" and args.decision_command == "show":
            try:
                decision = athanor.decisions()[args.decision_id]
            except KeyError as error:
                raise AthanorError(f"unknown Decision: {args.decision_id}") from error
            print(json.dumps(decision, indent=2))
        elif args.command == "decision":
            print(json.dumps(athanor.decisions(), indent=2))
        elif args.command == "artifact" and args.artifact_command == "register":
            try:
                uri, digest = args.location.split("|", 1)
            except ValueError as error:
                raise AthanorError("Artifact location must use URI|SHA256") from error
            receipt = athanor.register_artifact(
                args.artifact_id,
                args.program,
                args.kind,
                {"uri": uri, "sigil": digest},
                args.producer,
                args.input,
            )
            _print_receipt(
                f"Artifact {args.artifact_id} registered",
                receipt.receipt_id,
                receipt.sigil,
            )
        elif args.command == "artifact" and args.artifact_command == "show":
            try:
                artifact = athanor.artifacts()[args.artifact_id]
            except KeyError as error:
                raise AthanorError(f"unknown Artifact: {args.artifact_id}") from error
            print(json.dumps(artifact, indent=2))
        elif args.command == "artifact":
            print(json.dumps(athanor.artifacts(), indent=2))
        elif args.command == "issue" and args.issue_command == "open":
            receipt = athanor.open_issue(
                args.issue_id,
                args.program,
                args.subject,
                args.severity,
                args.title,
                args.description,
            )
            _print_receipt(
                f"Issue {args.issue_id} opened",
                receipt.receipt_id,
                receipt.sigil,
            )
        elif args.command == "issue" and args.issue_command == "resolve":
            receipt = athanor.resolve_issue(args.issue_id, args.resolution)
            _print_receipt(
                f"Issue {args.issue_id} resolved",
                receipt.receipt_id,
                receipt.sigil,
            )
        elif args.command == "issue" and args.issue_command == "show":
            try:
                issue = athanor.issues()[args.issue_id]
            except KeyError as error:
                raise AthanorError(f"unknown Issue: {args.issue_id}") from error
            print(json.dumps(issue, indent=2))
        elif args.command == "issue":
            print(json.dumps(athanor.issues(), indent=2))
        elif args.command == "deviation" and args.deviation_command == "record":
            receipt = athanor.record_deviation(
                args.deviation_id,
                args.protocol,
                args.kind,
                args.summary,
                args.rationale,
                args.impact,
                args.affected,
            )
            _print_receipt(
                f"Deviation {args.deviation_id} recorded",
                receipt.receipt_id,
                receipt.sigil,
            )
        elif args.command == "deviation" and args.deviation_command == "show":
            try:
                deviation = athanor.deviations()[args.deviation_id]
            except KeyError as error:
                raise AthanorError(f"unknown Deviation: {args.deviation_id}") from error
            print(json.dumps(deviation, indent=2))
        elif args.command == "deviation":
            print(json.dumps(athanor.deviations(), indent=2))
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
