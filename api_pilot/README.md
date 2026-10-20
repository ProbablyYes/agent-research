# API engineering round

The original `pilot_validity` local Qwen plan and upstream repository remain unchanged.
`collect.py` is a separate cloud collector: it reuses AuditSession, independent outcome
recomputation and train/validation-only baseline freezing, with strict ACTION parsing
and global stop on any exception.

The user explicitly accepted nominal billing uncertainty after the initial blocked
preflight. `authorize.py` records this as an amendment to the SAME round ledger;
`reliable_billing_bound` stays false. It never deletes prior requests or resets counts.

Controls remain USD3 estimated committed cost, 400 attempts, at most64 output Tokens,
60-second wall deadline, no retries or redirects. Before transmission reserve the
whole context's nominal input cost plus maximum output. After complete validated
Usage, settle the reservation to nominal Usage cost; unknown/timeout retains the full
reservation. This is NOT a provider-enforced invoice cap.

Implementation protocol changes are explicit: no fuzzy action matching or first-command
fallback; malformed confidence is not replaced by50. A format/protocol/environment
failure ends the round. Oracle expert_defer and original task utility stay unchanged.

Execution order (not an invitation to re-run existing phases):

1. Offline tests; commit source.
2. `python -m api_pilot.authorize` once, with frozen environment variables set.
3. `python -m api_pilot.collect smoke` once.
4. Only if Smoke completed without protocol/environment errors:
   `python -m api_pilot.collect pilot` once.
5. `python -m api_pilot.export <phase-output-directory>` once per phase.

Both phases use `/home/hly/.config/agent-research/api-agent-20261020.sqlite3`.
Existing output directories are refused; a halted/unresolved ledger cannot be resumed
automatically. The historical one-shot connectivity probe must not be re-run.
