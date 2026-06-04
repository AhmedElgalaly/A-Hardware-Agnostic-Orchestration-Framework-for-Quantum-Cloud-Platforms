from __future__ import annotations

from dataclasses import dataclass

from qiskit import QuantumCircuit

from app.models import InternalCircuit


@dataclass(frozen=True)
class TranslatedCircuit:
    internal: InternalCircuit
    qiskit: QuantumCircuit


def to_qiskit(internal: InternalCircuit) -> QuantumCircuit:
    circuit = QuantumCircuit(internal.num_qubits, internal.num_clbits)

    for operation in internal.operations:
        name = operation.name.lower()
        if name in {"h", "x", "y", "z", "s", "sdg", "t", "tdg"}:
            getattr(circuit, name)(operation.targets[0])
        elif name in {"rx", "ry", "rz"}:
            getattr(circuit, name)(operation.params[0], operation.targets[0])
        elif name in {"cx", "cz"}:
            control = operation.controls[0] if operation.controls else operation.targets[0]
            target = operation.targets[0] if operation.controls else operation.targets[1]
            getattr(circuit, name)(control, target)
        elif name == "measure":
            for qubit in operation.targets:
                circuit.measure(qubit, qubit)
        else:
            raise ValueError(f"Unsupported internal operation '{operation.name}'.")

    return circuit


def from_qiskit(source_format, raw_source, circuit: QuantumCircuit) -> InternalCircuit:
    from app.parser import metadata_for_qiskit_circuit
    from app.models import InternalOperation

    operations: list[InternalOperation] = []
    for instruction in circuit.data:
        name = instruction.operation.name
        qargs = [circuit.find_bit(qubit).index for qubit in instruction.qubits]
        params = [float(param) for param in instruction.operation.params]
        if name in {"cx", "cz"} and len(qargs) == 2:
            operations.append(InternalOperation(name=name, controls=[qargs[0]], targets=[qargs[1]], params=params))
        else:
            operations.append(InternalOperation(name=name, targets=qargs, params=params))

    return InternalCircuit(
        format=source_format,
        num_qubits=circuit.num_qubits,
        num_clbits=circuit.num_clbits,
        operations=operations,
        metadata=metadata_for_qiskit_circuit(circuit),
        raw_source=raw_source,
    )
