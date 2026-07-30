# Review policy

The canonical project policy is
[`REVIEW_DISCLOSURE_POLICY.md`](../../../../../docs/en/REVIEW_DISCLOSURE_POLICY.md).
“Local” means no additional destination beyond the already authorized
interactive Host; it does not assert that the model runs on-device.

- Default to `bench.review.local`; keep source and diff in the approved project boundary
- Call `benchwork_prepare_review` with the exact target, files, checks, disclosure flags, and destination
- For local review, open `bench.review.local` with the returned `review_id`, perform the read-only review, complete the Task, and call `benchwork_record_review`
- Treat CLI, IDE, network, execution, and scientific Seal approvals as unrelated to disclosure approval
- Reject any external request that includes credentials
- For external review, call `benchwork_approve_external_review` only after explicit user authorization, then open `bench.review.external` with the same `review_id`
- Require both the disclosure approval Receipt and a Ward-passing external Task before transmission
- Record reviewer, Host, provider, scope, disclosure, approval, findings, risks, and recommendation
- Treat the completed Review Artifact as advisory until `benchwork_accept_review` records explicit acceptance
- Preserve denied or conflicting review outcomes; do not silently replace them
