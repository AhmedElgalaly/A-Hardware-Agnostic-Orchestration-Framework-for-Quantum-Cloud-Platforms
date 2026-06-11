# Automated Test Summary

* **Total tests:** 38 (counted across `Implementation/tests/`).
* **Result on a clean database:** `38 passed` (see `pytest_output.txt`).
* **Command:** `python -m pytest -q` from the `Implementation/` directory.
* **Environment:** Python 3.12.13; the suite forces synchronous (eager) execution
  and disables all cloud providers (`conftest.py`), so it is offline and requires
  no credentials.

## Test-isolation caveat

The suite uses the configured `DATABASE_URL`. When run repeatedly against a
**persistent** dev database, the single test `test_fail_stale_recovers_orphaned_jobs`
can fail with `UNIQUE constraint failed: jobs.job_id`, because it inserts a fixed
job id (`orphan-test-1`) that a previous run already wrote. This is a **test-data
leftover, not a product defect**. On a clean database (a fresh clone, or by pointing
`DATABASE_URL` at a fresh file) all 38 tests pass. To reproduce cleanly:

```bash
# bash
DATABASE_URL="sqlite:///$(mktemp).db" python -m pytest -q
```

```powershell
# PowerShell
$env:DATABASE_URL = "sqlite:///$($env:TEMP -replace '\\','/')/uqaas_test_clean.db"
python -m pytest -q
```

## Note on the count

An earlier thesis draft referred to **36** tests; the current suite has **38** and
all pass. The paper has been updated to **38** to match the reproducible reality.
