# Phase 2 public trajectory exploration

Frozen sampling plan: commit 0d01cf6, seed 20261020. Same Sierra submission/version as Phase 1.
Main sample: 30 task-level random + 20 targeted, no overlap with Phase 1 task IDs. Full public transport container was fetched for inventory; only 50 runs are exported/indexed as this phase's research sample.

Deliverables are in ../../reports/PHASE2_*. Complete histories are in local raw/ and readable/. Source inventory, per-event pointers, sampling denominators, and validations are in evidence/ and PHASE2_SAMPLE_MANIFEST.json. Paths in the CSV are relative to this directory.

Raw histories remain local due to unresolved independent Sierra S3 redistribution terms. Git stores reports, derived indexes, scripts, and fingerprints. Supplement contains one accepted official SWE-smith published conversation and rejected incomplete Terminal-Bench mirror probes; these are not part of the 50 main trajectories.

Offline rebuild (does not execute historical actions):

```bash
python3 public_trajectory_research/phase2/scripts/build.py public_trajectory_research/phase2/raw/source_bundle.json
python3 public_trajectory_research/phase2/scripts/verify.py
python3 public_trajectory_research/phase2/scripts/reports.py
python3 public_trajectory_research/phase2/scripts/verify_supplement.py
```

The source URL, ETag, byte size and SHA256 are in evidence/acquisition.json. Downloading is a public data request, not a model request. Do not execute shell commands embedded in trajectories.
