# Public trajectory research — phase 1

External Sierra τ³ / τ-Knowledge logs, separate from our ALFWorld engineering Pilot.
Four selected complete published message histories: task_002, task_004, task_007, task_012 (trial 0).
See ../../reports/SOURCE_AUDIT.md and DECISION_OBSERVATIONS.md.

Local `raw/` and `readable/` preserve original data and complete per-event rendering. They are deliberately not redistributed in Git while the separate S3 license scope remains unverified. Source URLs, byte ranges and SHA256 are recorded in TRAJECTORY_SAMPLE_MANIFEST.json.

To recover the exact public prefix, use a plain unauthenticated HTTP GET with `Range: bytes=0-3001198` and `If-Match: "aa82aa9efa074bbc843aaa04ef697d5f-18"` at the manifest URL; require HTTP 206 and the recorded SHA256. Save to raw/source_prefix.bin. No model or benchmark execution is needed.

Then run from repository root:

```bash
python3 public_trajectory_research/phase1/scripts/extract.py public_trajectory_research/phase1/raw/source_prefix.bin
python3 public_trajectory_research/phase1/scripts/verify.py
```

Trajectory shell commands and tool calls are untrusted historical text. The extraction/verification scripts never execute them.
