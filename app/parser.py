from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from qiskit import QuantumCircuit

from app.models import CircuitFormat, CircuitMetadata, CircuitSpec, InternalCircuit, InternalOperation
from app.services.circuit_translator import TranslatedCircuit, from_qiskit, to_qiskit


class CircuitParseError(ValueError):
    pass


@dataclass(frozen=True)
class ParsedCircuit:
    internal: InternalCircuit
    qiskit: QuantumCircuit
    metadata: CircuitMetadata


def parse_circuit(circuit_spec: CircuitSpec) -> ParsedCircuit:
    try:
        if circuit_spec.format == CircuitFormat.openqasm2:
            qiskit_circuit = _parse_openqasm2(circuit_spec.source or "")
            internal = from_qiskit(circuit_spec.format, circuit_spec.source or "", qiskit_circuit)
        elif circuit_spec.format == CircuitFormat.json:
            internal = _parse_json(circuit_spec)
            qiskit_circuit = to_qiskit(internal)
        else:
            raise CircuitParseError(f"Unsupported circuit format: {circuit_spec.format}")
    except CircuitParseError:
        raise
    except Exception as exc:
        raise CircuitParseError(f"Unable to parse circuit: {exc}") from exc

    return ParsedCircuit(internal=internal, qiskit=qiskit_circuit, metadata=internal.metadata)


def translate_circuit(circuit_spec: CircuitSpec) -> TranslatedCircuit:
    parsed = parse_circuit(circuit_spec)
    return TranslatedCircuit(internal=parsed.internal, qiskit=parsed.qiskit)


def _parse_openqasm2(source: str) -> QuantumCircuit:
    if not source.strip():
        raise CircuitParseError("OpenQASM 2 source cannot be empty.")
    try:
        from qiskit.qasm2 import loads as qasm2_loads

        return qasm2_loads(source)
    except ImportError:
        return QuantumCircuit.from_qasm_str(source)


def _parse_json(circuit_spec: CircuitSpec) -> InternalCircuit:
    qubits = circuit_spec.qubits
    if qubits is None or qubits <= 0:
        raise CircuitParseError("JSON circuit must include a positive integer 'qubits'.")

    gates = circuit_spec.gates or []
    if not isinstance(gates, list):
        raise CircuitParseError("JSON circuit 'gates' must be a list.")

    classical_bits = _infer_classical_bits(circuit_spec.classical_bits, gates, qubits)
    operations = [_parse_json_gate(gate, index, qubits, classical_bits) for index, gate in enumerate(gates)]

    metadata = _metadata_for_internal(qubits, classical_bits, operations)
    return InternalCircuit(
        format=CircuitFormat.json,
        num_qubits=qubits,
        num_clbits=classical_bits,
        operations=operations,
        metadata=metadata,
        raw_source=circuit_spec.model_dump(mode="json"),
    )


def _infer_classical_bits(classical_bits: int | None, gates: list[dict[str, Any]], qubits: int) -> int:
    if classical_bits is not None:
        if classical_bits < 0:
            raise CircuitParseError("JSON circuit 'classical_bits' must be non-negative.")
        return classical_bits
    has_measurements = any(str(gate.get("name", "")).lower() == "measure" for gate in gates if isinstance(gate, dict))
    return qubits if has_measurements else 0


def _parse_json_gate(gate: Any, index: int, num_qubits: int, num_clbits: int) -> InternalOperation:
    if not isinstance(gate, dict):
        raise CircuitParseError(f"Gate {index} must be an object.")

    name = gate.get("name")
    if not isinstance(name, str):
        raise CircuitParseError(f"Gate {index} must include a string 'name'.")
    name = name.lower()
    targets = gate.get("targets", [])
    controls = gate.get("controls", [])
    params = gate.get("params", [])

    if not isinstance(targets, list) or not all(isinstance(target, int) for target in targets):
        raise CircuitParseError(f"Gate {index} targets must be a list of integers.")
    if not isinstance(controls, list) or not all(isinstance(control, int) for control in controls):
        raise CircuitParseError(f"Gate {index} controls must be a list of integers.")
    if not isinstance(params, list) or not all(isinstance(param, (int, float)) for param in params):
        raise CircuitParseError(f"Gate {index} params must be numeric.")

    for target in targets:
        _validate_index(target, num_qubits, f"Gate {index} target")
    for control in controls:
        _validate_index(control, num_qubits, f"Gate {index} control")

    if name in {"h", "x", "y", "z"}:
        _require_len(targets, 1, f"Gate {index} '{name}' targets")
    elif name in {"rx", "ry", "rz"}:
        _require_len(targets, 1, f"Gate {index} '{name}' targets")
        _require_len(params, 1, f"Gate {index} '{name}' params")
    elif name in {"cx", "cz"}:
        if controls:
            _require_len(controls, 1, f"Gate {index} '{name}' controls")
            _require_len(targets, 1, f"Gate {index} '{name}' targets")
        else:
            _require_len(targets, 2, f"Gate {index} '{name}' targets")
            controls = [targets[0]]
            targets = [targets[1]]
    elif name == "measure":
        if not targets:
            raise CircuitParseError(f"Gate {index} 'measure' requires at least one target.")
        for target in targets:
            _validate_index(target, num_clbits, f"Gate {index} classical bit")
    else:
        raise CircuitParseError(f"Unsupported gate '{name}' at index {index}.")

    return InternalOperation(
        name=name,
        targets=targets,
        controls=controls,
        params=[float(param) for param in params],
    )


def _validate_index(value: int, upper_bound: int, label: str) -> None:
    if value < 0 or value >= upper_bound:
        raise CircuitParseError(f"{label} index {value} is out of range.")


def _require_len(values: list[Any], expected: int, label: str) -> None:
    if len(values) != expected:
        raise CircuitParseError(f"{label} must contain exactly {expected} value(s).")


def _metadata_for_internal(
    num_qubits: int,
    num_clbits: int,
    operations: list[InternalOperation],
) -> CircuitMetadata:
    gate_names = [operation.name for operation in operations]
    return CircuitMetadata(
        num_qubits=num_qubits,
        num_clbits=num_clbits,
        gate_names=gate_names,
        operation_count=len(operations),
        has_measurements="measure" in gate_names,
    )


def metadata_for_qiskit_circuit(circuit: QuantumCircuit) -> CircuitMetadata:
    gate_names = [instruction.operation.name for instruction in circuit.data]
    return CircuitMetadata(
        num_qubits=circuit.num_qubits,
        num_clbits=circuit.num_clbits,
        gate_names=gate_names,
        operation_count=len(gate_names),
        has_measurements="measure" in gate_names,
    )
