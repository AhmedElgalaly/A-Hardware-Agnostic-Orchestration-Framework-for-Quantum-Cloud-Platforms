# U-QaaS — Reproducibility Artifacts for the Paper

This folder contains the experiment artifacts behind the paper
**"U-QaaS: A Hardware-Agnostic Orchestration Framework for Quantum Cloud Platforms."**
Every result here is an exact copy of a record that the running platform persisted
in its SQLite job store — **nothing was hand-edited or fabricated**.

## Contents

```
experiments_paper/
├── README.md                     ← this file
├── metadata.json                 ← versions, shots, hardware-run provenance, security note
├── MISSING_ARTIFACTS.md          ← artifacts that do not exist in the repo (with reasons)
├── REPRODUCIBILITY_AUDIT.md      ← audit of paper claims vs. actual data
├── circuits/                     ← the OpenQASM 2 circuits submitted to the platform
├── results/                      ← the normalised job records returned by the platform
├── tables/                       ← CSV versions of the paper tables, built from results/
├── logs/                         ← test-suite evidence
├── scripts/                      ← offline reproduction script (simulator only)
└── reproduced_results/           ← output folder for scripts/reproduce_aer_experiments.py
```

## How circuits/results map to the paper

| Paper item | Circuit | Result file | Table |
|---|---|---|---|
| Fig. (Bell, simulator) | `circuits/bell.qasm` | `results/bell_aer_result.json` | `tables/table_bell_sim_vs_hardware.csv` |
| Table (Bell sim vs hardware) | `circuits/bell.qasm` | `results/bell_ibm_fez_result.json` | `tables/table_bell_sim_vs_hardware.csv` |
| Fig./Table (cross-provider `benchmark_all`) | `circuits/bell.qasm` | `results/bell_benchmark_all_result.json` | `tables/table_benchmark_all.csv` |
| GHZ validation | `circuits/ghz.qasm` | `results/ghz_aer_result.json` | — |
| Fig. (Bernstein–Vazirani) | `circuits/bernstein_vazirani.qasm` | `results/bernstein_vazirani_aer_result.json` | `tables/table_algorithm_results.csv` |
| Deutsch–Jozsa | `circuits/deutsch_jozsa.qasm` | `results/deutsch_jozsa_aer_result.json` | `tables/table_algorithm_results.csv` |
| Fig. (Grover) | `circuits/grover.qasm` | `results/grover_aer_result.json` | `tables/table_algorithm_results.csv` |
| Fig. (QAOA Max-Cut) | `circuits/qaoa_maxcut.qasm` | `results/qaoa_maxcut_aer_result.json` | `tables/table_algorithm_results.csv` |
| Objective traceability table | — | — | `tables/table_objective_traceability.csv` |

## Reproducing the simulator experiments (no credentials needed)

The local Qiskit Aer experiments are fully reproducible offline:

```bash
cd Implementation
pip install -r requirements.txt
python experiments_paper/scripts/reproduce_aer_experiments.py
```

Fresh outputs are written to `experiments_paper/reproduced_results/`. Counts are
probabilistic but the **qualitative structure is stable** (e.g. Grover concentrates
on `111`, QAOA on `0110`/`1001`). The exact integer counts in `results/` come from
the original recorded runs and will differ slightly between executions.

## Reproducing the hardware experiments (historical; paid accounts / queue time)

The IBM Quantum and AWS Braket QPU runs in `results/bell_ibm_fez_result.json` and
`results/bell_benchmark_all_result.json` are **historical records**. Re-running them
requires:

* enabling the relevant provider(s) and supplying credentials in a local `.env`
  (see the main `Implementation/README.md`), and
* provider quota / paid access and queue time (some QPU runs took tens of minutes).

Because real quantum hardware is recalibrated frequently and is a shared resource,
the **exact counts will differ between runs**; the entangled-pair-plus-noise-floor
structure is what reproduces, not the precise integers.

## Credentials are excluded

No `.env`, API token, AWS key, Azure secret or raw database is included here. The
normalised result records never contain credentials by construction. See
`metadata.json` → `security_note` and `REPRODUCIBILITY_AUDIT.md` → security section.

## Citing / using the artifact

Cite the paper above and reference this `experiments_paper/` folder. Each result file
carries its original `job_id`, `created_at` and per-backend `metrics` so individual
runs can be traced.
