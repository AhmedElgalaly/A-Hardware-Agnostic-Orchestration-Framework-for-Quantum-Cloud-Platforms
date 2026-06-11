# Logs

Evidence for the paper's automated-testing claim.

* `pytest_output.txt` — output of `python -m pytest -q` run on a **clean database**
  (the fresh-clone / CI condition). Result: **38 passed**.
* `test_summary.md` — short summary and the important caveat about test isolation.

No runtime application logs are included here because they may contain backend
hostnames and timing detail that are not needed for reproducibility; the
per-backend `metrics` (execution time, transpiled depth) are preserved inside each
file under `../results/`.
