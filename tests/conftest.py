import os

# The test suite runs without a Redis broker or a Celery worker, so force
# synchronous (eager) execution before any application module is imported.
os.environ.setdefault("CELERY_TASK_ALWAYS_EAGER", "true")

# Keep tests hermetic and offline: force all cloud providers off regardless of
# any local .env, so the suite never makes network calls to IBM/AWS/Azure.
# (Environment variables take precedence over .env in pydantic-settings.)
os.environ["ENABLE_IBM"] = "false"
os.environ["ENABLE_AWS_BRAKET"] = "false"
os.environ["ENABLE_AZURE_QUANTUM"] = "false"
