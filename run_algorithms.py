# -*- coding: utf-8 -*-
"""Execute four canonical quantum algorithms THROUGH the platform (eager mode),
persist them to the SQLite job store (so they appear in the web UI), and print
the real measurement counts + metrics for the dissertation's results chapter.

Algorithms: Bernstein-Vazirani, Deutsch-Jozsa, Grover, QAOA Max-Cut (variational).
All run on the local Qiskit Aer simulator (no credentials needed).
"""
import os, math, itertools, json

# Configure the platform for a local, offline, eager run BEFORE importing app.*
os.environ["CELERY_TASK_ALWAYS_EAGER"] = "true"
os.environ["ENABLE_IBM"] = "false"
os.environ["ENABLE_AWS_BRAKET"] = "false"
os.environ["ENABLE_AZURE_QUANTUM"] = "false"
os.environ["DATABASE_URL"] = "sqlite:///./quantum_jobs.db"

from qiskit import QuantumCircuit, transpile
from qiskit.qasm2 import dumps as qasm2_dumps
from qiskit.quantum_info import Statevector
from qiskit_aer import AerSimulator

from app.models import JobCreateRequest
from app.orchestrator import Orchestrator

EX_DIR = os.path.join(os.path.dirname(__file__), "examples")
os.makedirs(EX_DIR, exist_ok=True)
SHOTS = 1024
orch = Orchestrator()


def submit(name, qc: QuantumCircuit):
    src = qasm2_dumps(qc)
    body = {
        "name": name,
        "circuit": {"format": "openqasm2", "source": src},
        "shots": SHOTS,
        "execution": {"strategy": "fastest", "backend_type": "any",
                       "provider": "auto", "objective": "min_latency"},
    }
    # save a ready-to-submit request file for the frontend
    with open(os.path.join(EX_DIR, name + ".json"), "w") as fh:
        json.dump(body, fh, indent=2)
    req = JobCreateRequest.model_validate(body)
    res = orch.submit_job(req)
    r = res.results[0]
    counts = dict(sorted(r.counts.items(), key=lambda kv: kv[1], reverse=True))
    print("\n=== %s ===" % name)
    print("job_id:", res.job_id, "| status:", res.status.value,
          "| backend:", r.backend)
    print("depth before/after transpile:",
          r.metrics.depth_before_transpile, "/", r.metrics.depth_after_transpile,
          "| exec_ms:", r.metrics.execution_time_ms)
    print("counts:", counts)
    return counts


# ---------------------------------------------------------------------------
# 1) Bernstein-Vazirani, secret string s = 101 (3 query qubits + 1 ancilla)
# ---------------------------------------------------------------------------
def bernstein_vazirani(secret="101"):
    n = len(secret)
    qc = QuantumCircuit(n + 1, n)
    qc.x(n); qc.h(range(n + 1))
    # oracle: CX from query qubit i to ancilla where secret bit (LSB=q0) is 1
    for i, bit in enumerate(reversed(secret)):   # reversed: q0 = LSB
        if bit == "1":
            qc.cx(i, n)
    qc.h(range(n))
    qc.measure(range(n), range(n))
    return qc


# ---------------------------------------------------------------------------
# 2) Deutsch-Jozsa, balanced function f(x)=x0 xor x1 xor x2 (3 inputs + ancilla)
# ---------------------------------------------------------------------------
def deutsch_jozsa(n=3):
    qc = QuantumCircuit(n + 1, n)
    qc.x(n); qc.h(range(n + 1))
    for i in range(n):           # balanced (parity) oracle
        qc.cx(i, n)
    qc.h(range(n))
    qc.measure(range(n), range(n))
    return qc


# ---------------------------------------------------------------------------
# 3) Grover, 3 qubits, marked state |111>, 1 iteration
# ---------------------------------------------------------------------------
def grover():
    qc = QuantumCircuit(3, 3)
    def ccz():
        qc.h(2); qc.ccx(0, 1, 2); qc.h(2)
    qc.h(range(3))
    ccz()                                   # oracle marks |111>
    qc.h(range(3)); qc.x(range(3))          # diffuser
    ccz()
    qc.x(range(3)); qc.h(range(3))
    qc.measure(range(3), range(3))
    return qc


# ---------------------------------------------------------------------------
# 4) QAOA Max-Cut (variational), 4-node graph, p=1, grid-searched parameters
# ---------------------------------------------------------------------------
N = 4
EDGES = [(0, 1), (0, 2), (1, 2), (1, 3), (2, 3)]

def cut_value(bs, edges):
    return sum(1 for u, v in edges if bs[u] != bs[v])

def build_qaoa(n, edges, gamma, beta, measure=True):
    qc = QuantumCircuit(n, n if measure else 0)
    for i in range(n):
        qc.h(i)
    for u, v in edges:
        qc.cx(u, v); qc.rz(2 * gamma, v); qc.cx(u, v)
    for i in range(n):
        qc.rx(2 * beta, i)
    if measure:
        qc.measure(range(n), range(n))
    return qc

def best_qaoa_params(n, edges):
    best = (-1.0, None, None)
    gammas = [i * math.pi / 20 for i in range(21)]
    betas = [i * math.pi / 20 for i in range(11)]
    for g in gammas:
        for b in betas:
            sv = Statevector.from_instruction(build_qaoa(n, edges, g, b, measure=False))
            exp = sum(p * cut_value(bs[::-1], edges) for bs, p in sv.probabilities_dict().items())
            if exp > best[0]:
                best = (exp, g, b)
    return best


def classical_maxcut(n, edges):
    best = -1; sols = []
    for bits in itertools.product("01", repeat=n):
        bs = "".join(bits); s = cut_value(bs, edges)
        if s > best: best, sols = s, [bs]
        elif s == best: sols.append(bs)
    return best, sols


if __name__ == "__main__":
    submit("bernstein_vazirani_s101", bernstein_vazirani("101"))
    submit("deutsch_jozsa_balanced", deutsch_jozsa(3))
    submit("grover_3q_marked_111", grover())

    exp, g, b = best_qaoa_params(N, EDGES)
    cbest, csols = classical_maxcut(N, EDGES)
    print("\n[QAOA] graph N=%d edges=%s" % (N, EDGES))
    print("[QAOA] classical optimal cut=%d solutions=%s" % (cbest, csols))
    print("[QAOA] best gamma=%.4f beta=%.4f expected_cut=%.4f" % (g, b, exp))
    counts = submit("qaoa_maxcut_4node", build_qaoa(N, EDGES, g, b, measure=True))
    # interpret QAOA counts by cut value (reverse bitstring for node order 0..N-1)
    ranked = sorted(counts.items(), key=lambda kv: kv[1], reverse=True)
    print("[QAOA] top measured (node-order, cut):")
    for bs, fr in ranked[:6]:
        print("   %s  freq=%4d  cut=%d" % (bs[::-1], fr, cut_value(bs[::-1], EDGES)))
    print("\nALL DONE. Jobs persisted to quantum_jobs.db (visible in the web UI).")
