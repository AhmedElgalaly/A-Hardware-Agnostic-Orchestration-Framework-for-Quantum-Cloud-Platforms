# Scripts

## `reproduce_aer_experiments.py`

Offline reproduction of the paper's **local Qiskit Aer** experiments. It loads each
circuit from `../circuits/`, runs it on the Aer simulator (1024 shots by default),
writes fresh JSON to `../reproduced_results/`, and prints a summary.

```bash
cd Implementation
pip install -r requirements.txt
python experiments_paper/scripts/reproduce_aer_experiments.py            # 1024 shots
python experiments_paper/scripts/reproduce_aer_experiments.py --shots 4096
```

* **No credentials and no network** — simulator only. IBM/AWS/Azure hardware runs
  are intentionally **not** automated here; they are historical records in
  `../results/` (re-running them needs provider accounts, quota and queue time —
  see the top-level `experiments_paper/README.md`).
* Counts are probabilistic; exact integers differ between runs. The **dominant
  outcomes** are the reproducible claim. Measurement bit-ordering may differ from
  the normalised platform output (raw Qiskit vs. the platform's `result_normalizer`).

### Example (observed) output

```
[OK] Bell state                     top: 11:524, 00:500
[OK] GHZ state                      top: 111:528, 000:496
[OK] Bernstein-Vazirani (s=101)     top: 101:1024
[OK] Deutsch-Jozsa (balanced)       top: 111:1024
[OK] Grover (mark 111)              top: 111:818, ...
[OK] QAOA Max-Cut (4-node, p=1)     top: 1001:179, 0110:163, ...
```

To run the *same* circuits through the full platform (orchestrator, selection,
normalisation, persistence) instead of bare Aer, see `Implementation/run_algorithms.py`.
