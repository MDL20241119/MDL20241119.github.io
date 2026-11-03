# 2026-11-03 result observations

The four regional records in `data/research-outcomes-20261103.json` are source-result observations, not four additional canonical projects or adoptions. Explicit related-record IDs connect the Sanda adoption and Osaka history without merging unrelated projects. Canonical projects, prior source shards, original local records and the adoption ledger are preserved.

Each metric carries its period, original unit, planned/actual phase and primary-source references. Unresolved source discrepancies remain visible, including Toyooka's 807 runs versus 885 services. Policy events distinguish budget evaluation, requirements, grant decisions and operational outcomes.

Regenerate the observation shard, discovery index, observation timeline, counts and static policy supplement:

```sh
python municipal-mobility-history/maintenance/build-research-outcomes.py
node municipal-mobility-history/verification/research-outcomes.cjs
node municipal-mobility-history/verification/research-updates.cjs
node mobility-policy-history/verification/status-map.cjs
node mobility-policy-history/verification/acceptance.cjs
```

The builder removes only its own observation IDs before regeneration and refuses an unexpected baseline count. Reconcile a later baseline explicitly before reuse. It also synchronizes release query values through `sync_release.py`. The preservation tests compare original records with the checked-out Git HEAD, so they work both before and after publication.

The existing municipal acceptance suite has three independently reproduced baseline failures in its latest-batch expectation, legacy-title expectation and stale-count exception expectation. These are not reported as a full pass. Its other 14 checks and the dedicated research suites pass. Keep baseline test evidence distinct from the focused checks.
