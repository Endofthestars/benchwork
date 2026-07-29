# Open Decisions

1. Select the stable Python distribution and CLI names after conflict review.
   This prototype uses `benchwork-arcana` and `bwork` provisionally.
2. Decide whether Chronicle compaction uses signed checkpoints or immutable
   segment manifests; a hash chain alone cannot prove a truncated final tail.
3. Define the M2 policy language for network, filesystem, budget, and approval
   constraints.
4. Define the result-bundle schema before implementing Alembic.
