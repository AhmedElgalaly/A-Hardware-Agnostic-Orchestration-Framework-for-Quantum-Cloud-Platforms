# Reproducibility Audit — U-QaaS

**Date:** 2026-06-11
**Scope:** Extract the paper's experiment artifacts into `Implementation/experiments_paper/`,
verify every paper claim against the actual platform data, and fix inconsistencies
without fabricating results.

**Source of truth:** the normalised job records persisted by the running platform in
its Docker-volume SQLite store (`/data/quantum_jobs.db`, 48 jobs). All `results/`
files are exact exports of those records; all `tables/` files are computed from them.

---

## 1. Files created

```
Implementation/experiments_paper/
├── README.md, metadata.json, MISSING_ARTIFACTS.md, REPRODUCIBILITY_AUDIT.md
├── circuits/   bell.qasm, ghz.qasm, bernstein_vazirani.qasm,
│               deutsch_jozsa.qasm, grover.qasm, qaoa_maxcut.qasm
├── results/    bell_aer_result.json, bell_ibm_fez_result.json,
│               bell_benchmark_all_result.json, ghz_aer_result.json,
│               bernstein_vazirani_aer_result.json, deutsch_jozsa_aer_result.json,
│               grover_aer_result.json, qaoa_maxcut_aer_result.json
├── tables/     table_bell_sim_vs_hardware.csv, table_benchmark_all.csv,
│               table_algorithm_results.csv, table_objective_traceability.csv
├── logs/       README.md, test_summary.md, pytest_output.txt
├── scripts/    reproduce_aer_experiments.py, README.md
└── reproduced_results/   (fresh Aer outputs from the script)
```

## 2. Artifacts extracted

* 6 OpenQASM 2 circuits (from `Implementation/examples/` and the GHZ job record).
* 8 normalised result records (1 Bell-Aer, 1 Bell-`ibm_fez`, 1 cross-provider
  `benchmark_all`, 1 GHZ, 4 canonical algorithms).
* 4 CSV tables mirroring the paper.
* Test evidence (clean-DB `pytest` run) and an offline reproduction script (verified
  to run with simulator-only dependencies).

## 3. Experiments verified against the paper (all consistent — no fabrication)

| Experiment | Paper claim | Actual artifact | Verdict |
|---|---|---|---|
| Bell, Aer | near 50/50 on `00`/`11` | `{00:501, 11:523}` (1024) | ✔ matches |
| Bell, `ibm_fez` | `00:484, 11:484, 10:31, 01:25`; depth 3→8 | exactly that; `et`≈8.3 s; job `1cf75ddd…` | ✔ exact |
| `benchmark_all` Bell | Aer + AWS sims + 3 IBM QPUs + 5 AWS QPUs; `tn1` fails; status partial | exactly that (job `977d2d64…`) | ✔ exact |
| GHZ, Aer | concentrated on `000`/`111` | `{000:510, 111:514}` | ✔ matches |
| Bernstein–Vazirani | `101: 1024/1024` | `{101:1024}` | ✔ exact |
| Deutsch–Jozsa | `111: 1024/1024` (balanced) | `{111:1024}` | ✔ exact |
| Grover | `111: 792/1024` (~77%) | `{111:792, …}` | ✔ exact |
| QAOA Max-Cut | top `0110:186`, `1001:176`; γ≈2.83, β≈0.31 | `{0110:186, 1001:176, …}`; grid = k·π/20 ⇒ 18π/20≈2.827, 2π/20≈0.314 | ✔ matches |
| "eight real QPUs / two providers / one benchmark request" | — | 3 IBM + 5 AWS in one `benchmark_all` job | ✔ supported |
| No quantum advantage; QRNG/optimisation = future work | — | code confirms these endpoints are not implemented | ✔ honest |

An **independent re-run** of the simulator experiments
(`scripts/reproduce_aer_experiments.py`) reproduced every qualitative claim
(Bell ~50/50; GHZ `000`/`111`; BV `101`; DJ `111`; Grover `111` dominant; QAOA
`0110`/`1001` top two).

## 4. Inconsistencies found

1. **Test count: 36 vs 38.** The paper said *36 passing*; the current suite has
   **38** test functions.
2. **One failing test on a dirty DB.** `test_fail_stale_recovers_orphaned_jobs` fails
   with `UNIQUE constraint failed: jobs.job_id` when run against a persistent dev DB
   (leftover `orphan-test-1` row). This is a **test-isolation artifact, not a defect**;
   on a clean DB the full suite is **38 passed** (see `logs/pytest_output.txt`).
3. No numerical/result inconsistencies were found — every figure/table number in the
   paper is backed by a real record (Section 3).

## 5. Paper fixes made (`Publishing Paper/main.tex`, recompiles cleanly, 22 pp.)

* "36 passing tests" → **"38 passing tests"** in the abstract, the evaluation section
  and the conclusion; removed the stale 36-vs-38 `TODO` footnote and added
  "all of which pass on a clean database."
* **Data availability** now points to `experiments_paper/` (circuits, results, CSVs,
  test evidence).
* **Code availability** now references the repository and the offline reproduction
  script (public URL still to be added on publication).
* **Author contributions** completed for both authors; **Conflict of interest** made
  plural (two authors).
* No result numbers were changed — none were wrong.

## 6. Missing artifacts

See `MISSING_ARTIFACTS.md`. Summary: no Azure paid-QPU run (simulator-only, already
stated as future work); provider-side job IDs not persisted (platform `job_id` is);
UI screenshots live with the manuscript, not the code repo; no CI logs (tests run
locally). None affect any paper claim.

## 7. Security issues

* `Implementation/.env` contains **live credentials** (`IBM_QUANTUM_TOKEN`,
  `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AZURE_CLIENT_SECRET`, …).
  It is **already in `.gitignore`** (along with `*.db`, `*.db-wal/shm`, `.venv/`),
  so it will not be committed.
* The job-store records and all exported `results/` contain **no credentials** (the
  normalised schema excludes them by design — verified by scanning the DB export).
* **Recommendation:** before making the repo public, (a) double-check `git status`
  /`git log` so no `.env` or `*.db` was ever committed historically, and
  (b) **rotate** the IBM/AWS/Azure credentials that were stored in `.env` as routine
  hygiene, since they exist in plaintext locally.

## 8. Remaining manual actions before GitHub upload

1. Fill the manuscript placeholders (author emails, affiliation address, repository
   URL) — listed in `MISSING_ARTIFACTS.md`.
2. Confirm `.env` and `*.db` were never committed in git history; rotate credentials.
3. Optionally fix test isolation so `test_fail_stale_recovers_orphaned_jobs` uses a
   temp DB (so the suite passes even against a dirty local DB) — product-quality
   nicety, not required for the paper.
