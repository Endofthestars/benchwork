---
language: en
canonical: true
---

# Twin Gate

M3 establishes Codex and Claude Code as symmetric Host adapters. A Host is an
interaction environment, not a provider authority or source of truth.

```text
Codex / Claude Code
        |
        | HostProposal
        v
Task Capsule + Circle -> Ward -> PASS | WAITING_FOR_APPROVAL | REJECTED
        |
        v
Later provider executor (not part of M3)
```

Both adapters use `HostAdapter.propose`. Their output differs only in the
recorded `host` value. A Host cannot seal a Protocol, approve itself, append an
experimental result, or make a scientific Decision.
