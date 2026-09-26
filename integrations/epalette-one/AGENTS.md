# e-Palette ONE integration rules

- Authenticated UI, direct API, MCP, A2A and transport-standard adapters must use the same business services and D1 workspace state. Never duplicate operational booking, capacity, energy or stock ledgers.
- The user explicitly requested no initial login (2026-09-26). Public `/`, `/connections`, `/try/approvals/*` are a visibly synthetic, tab-local sandbox using the same domain rules. Never upload its state/approvals to D1 or external services. Keep authenticated workspaces and approvals separate; no anonymous shared-owner or development auth bypass.
- A passenger reservation is a ticket against a trip; it is not the operator's vehicle-use reservation. Unassigned on-demand requests are not confirmed trips or COMmmmONS tentative reservations.
- Pin standards and record the original source, retrieval time, hash and licence. Test e-Palette itself; do not reuse another project's pass result as evidence.
- External changes require a stored proposal, exact content, expiry, current version and authenticated human approval. An agent-supplied approved flag is never authorization.
- Enforce tenant, subject, role and delegation scope on the server. Reject unknown fields, stale approvals, repeated use with different content and unsupported operations.
- Never expose VCI, steering, braking, door, key, movement or charger-start controls to any API or AI tool.
- Keep synthetic data visibly separate. Fail closed when production inputs, authentication, contracts or partner configuration are unavailable.
- Report implementation, local verification, external test connection and production connection separately. A green local test is not full standard conformance.
- After domain changes run domain/SQLite/integration/guest-UI tests. The user authorized public access to the isolated no-login demo; deploy the safe guest-capable code before changing access. Preserve server-side identity requirements and update the existing GitHub draft PR.

- Keep service/stop discovery tied to the same vehicle schedule; publish only configured dates, stops and reservation conditions. Never infer weekly service or production GPS from synthetic labels.
- Passenger payment reads must not report received without payment-provider evidence. Synthetic zero fare is excluded. Cancellation remains an explicit human-approved action.
