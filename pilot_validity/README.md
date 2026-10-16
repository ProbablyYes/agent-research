# Pilot validity adapter

This is instrumentation and evaluation code owned by Agent Decision Failure Lab. It imports the locked upstream commit without editing it. Scope: ALFWorld, one frozen initial prefix per task, expert_defer, no_preview, six tasks. It is not a new agent algorithm.

- `core.py`: records reset/step state; temporarily wraps the upstream environment factory and replay function; compares every replayed state before the original branch takes its next action. All wrappers are restored on exit.
- `run.py prepare`: freezes six tasks from the existing manifest, file SHA256s, source/adapter hashes, prompt templates, package versions and parameters. Existing plan/output directories are rejected.
- `run.py run`: preserves original raw rows, persists all pre-action audits, independently reconstructs branch costs, excludes invalid pairs only in explicitly labeled valid-pair metrics, and reports attempted/valid/invalid denominators. No replacement samples.
- `original_raw` analysis uses the author's unmodified risk model and threshold search on raw rows; `valid_pairs` compares the original and expanded-boundary threshold routers on identical valid subsets. Always Continue/Intervene/Quit are explicit. Thresholds and RF models are frozen before test tasks are executed. Original explicit EU is retained without future step costs.

The corrected router enumerates all distinct validation probabilities plus -1 and 2 sentinels (probabilities must be in [0,1]). This expands the author's search class; it is a **methodological correction**, not merely logging. Order stays Continue → Intervene → Quit; it is not an arbitrary action-order oracle.

PDDL facts and counters are privileged **audit-only** data; predictors still receive the author's 26 prefix features. Equality of exported fields does not prove full native simulator/planner/RNG equivalence. Outputs never claim a reliable causal fork. Missing required fields fail closed. Invalid-pair metrics condition on passing audits; coverage loss can bias population estimates.

HTTP execution is opt-in, restricted to localhost:18080 and requires recorded service provenance. No tokenizer/weight downloads occur in the adapter. All prompts, generated text, actual HTTP payloads and responses are retained. The server's loaded tensor identity cannot be proved by its API alone.

See the four reports added in `reports/` for executed tests, failures, fingerprints, limitations and exact commands. Old evidence stays in `experiments/cinc_smoke_20261016`; new CPU evidence is separate in `experiments/pilot_validity_cpu`.
