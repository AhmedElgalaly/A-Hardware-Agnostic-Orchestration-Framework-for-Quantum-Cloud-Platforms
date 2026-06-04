import pytest

from app.models import CircuitFormat, CircuitSpec
from app.parser import CircuitParseError, parse_circuit


BELL_QASM = (
    'OPENQASM 2.0; include "qelib1.inc"; '
    "qreg q[2]; creg c[2]; h q[0]; cx q[0], q[1]; measure q -> c;"
)


def test_openqasm_bell_state_parsing():
    parsed = parse_circuit(CircuitSpec(format=CircuitFormat.openqasm2, source=BELL_QASM))

    assert parsed.internal.num_qubits == 2
    assert parsed.internal.num_clbits == 2
    assert parsed.metadata.gate_names == ["h", "cx", "measure", "measure"]
    assert parsed.metadata.operation_count == 4
    assert parsed.metadata.has_measurements is True
    assert parsed.qiskit.num_qubits == 2


def test_json_bell_state_parsing():
    parsed = parse_circuit(
        CircuitSpec(
            format=CircuitFormat.json,
            qubits=2,
            classical_bits=2,
            gates=[
                {"name": "h", "targets": [0]},
                {"name": "cx", "controls": [0], "targets": [1]},
                {"name": "measure", "targets": [0, 1]},
            ],
        )
    )

    assert parsed.internal.num_qubits == 2
    assert parsed.internal.num_clbits == 2
    assert parsed.metadata.gate_names == ["h", "cx", "measure"]
    assert parsed.metadata.operation_count == 3
    assert parsed.metadata.has_measurements is True
    assert parsed.qiskit.num_clbits == 2


def test_json_parser_infers_classical_bits_for_measurement():
    parsed = parse_circuit(
        CircuitSpec(
            format=CircuitFormat.json,
            qubits=1,
            gates=[
                {"name": "x", "targets": [0]},
                {"name": "measure", "targets": [0]},
            ],
        )
    )

    assert parsed.internal.num_clbits == 1


def test_json_parser_supports_parameterized_rotation():
    parsed = parse_circuit(
        CircuitSpec(
            format=CircuitFormat.json,
            qubits=1,
            gates=[
                {"name": "rx", "targets": [0], "params": [1.5708]},
                {"name": "measure", "targets": [0]},
            ],
        )
    )

    assert parsed.metadata.gate_names == ["rx", "measure"]


def test_invalid_json_circuit_raises_clear_error():
    with pytest.raises(CircuitParseError, match="Unsupported gate"):
        parse_circuit(
            CircuitSpec(
                format=CircuitFormat.json,
                qubits=1,
                gates=[{"name": "unsupported", "targets": [0]}],
            )
        )
