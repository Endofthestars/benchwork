# Security Policy

## Supported versions

Benchwork is a public Alpha. Security fixes are applied to the current
development line only; no stable compatibility or long-term support promise
exists yet.

## Reporting

Do not open a public issue for a suspected vulnerability. Use GitHub's private
vulnerability reporting for `Endofthestars/benchwork`, or contact the repository
owner through the private address listed on their GitHub profile.

Include the affected version, attack prerequisites, minimal reproduction, and
the integrity or confidentiality impact. Please avoid modifying real research
ledgers while reproducing an issue.

## Integrity boundary

Chronicle Sigils detect accidental mutation and inconsistent local state. They
are content digests, not signatures, and do not protect against an attacker who
can replace the complete ledger, head, and receipts. M10 Actor records provide
audit provenance but not cryptographic identity.
