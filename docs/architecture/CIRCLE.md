# Circle and Ward

## Capability first

A Capability is a stable operation contract, not an Agent or model identity.
The local `.benchwork/capabilities.json` registry declares its allowed tools,
network access, time ceiling, and whether a human approval is required.

## A task is bounded before it is delegated

`bwork task create` writes a non-canonical Task Capsule containing exactly one
Capability, an immutable input Sigil, and one Circle. The Circle declares tools,
network use, and time budget. Ward rejects requests that exceed the Capability
contract before any provider is invoked.

## Approval is canonical, execution is not

For a gated task, Ward returns `WAITING_FOR_APPROVAL`. A researcher records an
`approval.granted` Chronicle event with a reason; Athanor produces its Receipt.
Ward then permits the same Capsule. This is deliberately not an execution API:
an Agent Result remains a Proposal until a later Athanor transition accepts a
well-defined scientific object.

## Current limits

Circle presently validates declarative boundaries. M3 Host adapters and M4
executors must enforce the issued Circle at the OS, container, and provider
layers rather than treating this policy check as a sandbox.
