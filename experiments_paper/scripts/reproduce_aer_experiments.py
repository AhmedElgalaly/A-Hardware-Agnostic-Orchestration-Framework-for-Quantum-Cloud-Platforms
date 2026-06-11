#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Reproduce the local Qiskit Aer experiments from the paper.

Runs ONLY on the local Aer simulator: no IBM/AWS/Azure credentials are required
and no network calls are made. It loads each OpenQASM 2 circuit from
``experiments_paper/circuits/`` and executes it on the Aer simulator, writing
fresh per-experiment JSON into ``experiments_paper/reproduced_results/`` and
printing a concise summary.

Counts are probabilistic; exact integers will differ from the recorded runs in
``experiments_paper/results/``, but the qualitative structure reproduces
(e.g. Grover concentrates on ``111``; QAOA on ``0110``/``1001``).

Usage:
    cd Implementation
    pip install -r requirements.txt          # qiskit + qiskit-aer suffice here
    python experiments_paper/scripts/reproduce_aer_experiments.py [--shots 1024]
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
EXP = os.path.dirname(HERE)                       # experiments_paper/
CIRCUITS = os.path.join(EXP, "circuits")
OUT = os.path.join(EXP, "reproduced_results")

# Map circuit file -> (label, expected dominant outcome(s) described in the paper)
EXPERIMENTS = [
    ("bell.qasm",                "Bell state",                 "00 and 11 (~50/50)"),
    ("ghz.qasm",                 "GHZ state",                  "000 and 111"),
    ("bernstein_vazirani.qasm",  "Bernstein-Vazirani (s=101)", "101"),
    ("deutsch_jozsa.qasm",       "Deutsch-Jozsa (balanced)",   "non-zero (balanced)"),
    ("grover.qasm",              "Grover (mark 111)",          "111 amplified (~77%)"),
    ("qaoa_maxcut.qasm",         "QAOA Max-Cut (4-node, p=1)", "0110 and 1001"),
]


def main() -> int:
    ap = argparse.ArgumentParser(description="Reproduce U-QaaS Aer experiments (offline).")
    ap.add_argument("--shots", type=int, default=1024)
    args = ap.parse_args()

    try:
        from qiskit import QuantumCircuit, transpile
        from qiskit_aer import AerSimulator
    except Exception as exc:  # pragma: no cover
        print("ERROR: qiskit / qiskit-aer not installed. Run: pip install -r requirements.txt")
        print(f"       ({exc})")
        return 1

    os.makedirs(OUT, exist_ok=True)
    sim = AerSimulator()
    summary = []

    for fname, label, expected in EXPERIMENTS:
        path = os.path.join(CIRCUITS, fname)
        if not os.path.exists(path):
            print(f"[SKIP] {label}: missing circuit {fname}")
            continue
        with open(path, encoding="utf-8") as fh:
            qasm = fh.read()

        qc = QuantumCircuit.from_qasm_str(qasm)
        depth_before = qc.depth()
        tqc = transpile(qc, sim)
        depth_after = tqc.depth()
        result = sim.run(tqc, shots=args.shots).result()
        counts = result.get_counts()

        top = sorted(counts.items(), key=lambda kv: -kv[1])[:3]
        record = {
            "experiment": label,
            "circuit": fname,
            "backend": "aer_simulator",
            "shots": args.shots,
            "depth_before_transpile": depth_before,
            "depth_after_transpile": depth_after,
            "counts": counts,
            "expected_per_paper": expected,
        }
        out_path = os.path.join(OUT, fname.replace(".qasm", "_reproduced.json"))
        with open(out_path, "w", encoding="utf-8") as fh:
            json.dump(record, fh, indent=2)

        top_str = ", ".join(f"{k}:{v}" for k, v in top)
        print(f"[OK] {label:<30} top: {top_str:<28} (expected {expected})")
        summary.append(record)

    print(f"\nWrote {len(summary)} result file(s) to {OUT}")
    print("Note: counts are probabilistic and measurement bit-ordering may differ")
    print("from the normalised platform output; the dominant outcomes are the claim.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
