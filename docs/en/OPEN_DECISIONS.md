---
language: en
canonical: true
---

# Open Decisions

1. Select the stable Python distribution and CLI names after conflict review.
   This prototype uses `benchwork-arcana` and `bwork` provisionally.
2. Decide whether Chronicle checkpoints should additionally be signed for
   protection against a malicious local writer. The current head detects
   accidental tail truncation and incomplete commits.
3. Extend Circle policy from declarative checks to executor-enforced filesystem,
   budget, and network isolation.
4. Finalize metric-level constraints in result-bundle/1.0 before Alembic ships.
