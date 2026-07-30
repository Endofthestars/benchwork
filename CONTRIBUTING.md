# Contributing to Benchwork

Benchwork is a deterministic reference kernel for auditable computational
research. Changes should preserve the boundary between Agent proposals,
canonical Athanor transitions, and human scientific authority.

## Development setup

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install --editable ".[dev]"
python3 -m unittest discover -s tests -v
```

## Change requirements

Every behavioral pull request must describe:

- the related RFC or ADR;
- invariants added, removed, or changed;
- backward-compatibility and migration impact;
- positive and adversarial tests;
- documentation changes.

New canonical objects and persisted records require a closed, versioned JSON
Schema. New Chronicle transitions require replay tests. Scientific promotion
must be an explicit Gate event and must not be inferred from conversation or
mutable files.

Keep pull requests focused. Do not combine automatic Provider execution,
network transport, or executable extensions with Phase 1 hardening work.

## Checks

```bash
ruff check .
mypy src/benchwork
python3 -m coverage run -m unittest discover -s tests
python3 -m coverage report
python3 scripts/ci/check-doc-links.py
python3 scripts/ci/check-release-policy.py
```

Use the pull request template and leave the PR in Draft while invariants,
migration notes, or negative tests are incomplete.
