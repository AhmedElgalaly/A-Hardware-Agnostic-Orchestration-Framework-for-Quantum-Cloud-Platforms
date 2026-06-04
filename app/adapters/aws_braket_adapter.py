from __future__ import annotations

from time import perf_counter, time

from app.adapters.base import QuantumBackendAdapter
from app.config import settings
from app.models import BackendCapability, BackendType, JobCreateRequest, NormalizedBackendResult
from app.services.circuit_translator import TranslatedCircuit
from app.services.result_normalizer import normalize_failure, normalize_success

# On-demand managed simulators that are always available with a valid AWS
# account. QPUs are discovered dynamically and only added when online.
_BRAKET_SIMULATORS = {
    "sv1": "arn:aws:braket:::device/quantum-simulator/amazon/sv1",
    "dm1": "arn:aws:braket:::device/quantum-simulator/amazon/dm1",
    "tn1": "arn:aws:braket:::device/quantum-simulator/amazon/tn1",
}


class AWSBraketAdapter(QuantumBackendAdapter):
    """AWS Braket adapter.

    Enabled with ENABLE_AWS_BRAKET=true and AWS credentials (access key/secret
    or an ambient AWS profile/role) plus an S3 bucket for result storage. Without
    credentials or the amazon-braket-sdk, the adapter reports itself unavailable
    and the platform continues with the other providers.
    """

    _provider = "aws_braket"
    # Backend discovery hits the AWS network, so cache it instead of querying on
    # every capabilities()/supports_backend() call (which the orchestrator makes
    # repeatedly per request).
    _CACHE_TTL_SECONDS = 300

    def __init__(self) -> None:
        self._session = None
        self._import_error: str | None = None
        self._auth_error: str | None = None
        self._caps_cache: list[BackendCapability] | None = None
        self._caps_cached_at: float = 0.0
        self._initialize()

    def provider_name(self) -> str:
        return self._provider

    def is_available(self) -> bool:
        return self._session is not None

    def _initialize(self) -> None:
        if not settings.enable_aws_braket:
            self._auth_error = "AWS Braket adapter is disabled. Set ENABLE_AWS_BRAKET=true to enable it."
            return
        if not settings.aws_braket_s3_bucket:
            self._auth_error = "AWS_BRAKET_S3_BUCKET is required for Braket result storage."
            return
        try:
            import boto3
            from botocore.config import Config
            from braket.aws import AwsSession
        except Exception as exc:  # pragma: no cover - depends on optional SDK
            self._import_error = f"amazon-braket-sdk/boto3 not installed: {exc}"
            return
        try:
            kwargs = {"region_name": settings.aws_region}
            if settings.aws_access_key_id and settings.aws_secret_access_key:
                kwargs["aws_access_key_id"] = settings.aws_access_key_id
                kwargs["aws_secret_access_key"] = settings.aws_secret_access_key
            boto_session = boto3.Session(**kwargs)
            # Bounded timeouts so a bad network/credentials fail fast instead of
            # hanging the API/worker on long boto retries.
            config = Config(connect_timeout=5, read_timeout=15, retries={"max_attempts": 2})
            self._session = AwsSession(boto_session=boto_session, config=config)
        except Exception as exc:  # pragma: no cover
            self._auth_error = f"AWS authentication failed: {type(exc).__name__}"
            self._session = None

    def capabilities(self) -> list[BackendCapability]:
        if not self._session:
            return []
        now = time()
        if self._caps_cache is not None and (now - self._caps_cached_at) < self._CACHE_TTL_SECONDS:
            return self._caps_cache
        self._caps_cache = self._discover_capabilities()
        self._caps_cached_at = now
        return self._caps_cache

    def _discover_capabilities(self) -> list[BackendCapability]:
        caps: list[BackendCapability] = []
        # Managed simulators are always usable; expose them with generous limits.
        for name, arn in _BRAKET_SIMULATORS.items():
            caps.append(
                BackendCapability(
                    provider=self._provider,
                    backend_name=name,
                    backend_type=BackendType.simulator,
                    num_qubits=34 if name == "sv1" else 17,
                    native_gates=["h", "x", "y", "z", "rx", "ry", "rz", "cx", "cz", "measure"],
                    topology="fully_connected_simulated",
                    noise_model_available=(name == "dm1"),
                    estimated_latency_ms=3000,
                    metadata={"arn": arn, "sdk": "amazon-braket-sdk"},
                )
            )
        # Best-effort QPU discovery.
        try:
            from braket.aws import AwsDevice

            for device in AwsDevice.get_devices(statuses=["ONLINE"], aws_session=self._session):
                if "simulator" in device.arn:
                    continue
                props = getattr(device, "properties", None)
                # Skip non-gate devices (e.g. QuEra Aquila is analog/neutral-atom
                # and only runs Hamiltonian programs, not OpenQASM gate circuits).
                if not _supports_gate_model(props):
                    continue
                qubit_count = getattr(getattr(props, "paradigm", None), "qubitCount", 0) if props else 0
                caps.append(
                    BackendCapability(
                        provider=self._provider,
                        backend_name=device.name.lower().replace(" ", "_"),
                        backend_type=BackendType.hardware,
                        num_qubits=int(qubit_count or 0),
                        native_gates=[],  # provider-validated at submission
                        topology="braket_qpu",
                        noise_model_available=False,
                        estimated_latency_ms=60000,
                        metadata={"arn": device.arn, "sdk": "amazon-braket-sdk"},
                    )
                )
        except Exception:
            pass
        return caps

    def supports_backend(self, backend_name: str) -> bool:
        return any(cap.backend_name == backend_name for cap in self.capabilities())

    def run(
        self,
        job_id: str,
        circuit: TranslatedCircuit,
        job_request: JobCreateRequest,
        backend_capability: BackendCapability,
    ) -> NormalizedBackendResult:
        if not self._session:
            return normalize_failure(
                backend_capability,
                job_request.shots,
                self._auth_error or self._import_error or "AWS Braket not configured.",
                circuit.internal.metadata,
            )
        try:
            from braket.aws import AwsDevice

            arn = backend_capability.metadata.get("arn")
            if not arn:
                raise ValueError(f"No device ARN for backend '{backend_capability.backend_name}'.")

            braket_circuit = _to_braket(circuit)
            device = AwsDevice(arn, aws_session=self._session)

            depth_before = circuit.qiskit.depth() or 0
            started = perf_counter()
            s3_location = (settings.aws_braket_s3_bucket, settings.aws_braket_s3_prefix)
            task = device.run(braket_circuit, s3_destination_folder=s3_location, shots=job_request.shots)
            result = task.result()
            execution_time_ms = round((perf_counter() - started) * 1000, 3)

            counts = {str(state): int(count) for state, count in dict(result.measurement_counts).items()}
            return normalize_success(
                backend_capability,
                job_request.shots,
                counts,
                circuit.internal.metadata,
                execution_time_ms,
                depth_before,
                depth_before,
            )
        except Exception as exc:
            return normalize_failure(backend_capability, job_request.shots, str(exc), circuit.internal.metadata)


_GATE_ACTION_TYPES = {"braket.ir.openqasm.program", "braket.ir.jaqcd.program"}


def _supports_gate_model(props) -> bool:
    """True only if the device accepts gate-model (OpenQASM/JAQCD) programs.

    Analog devices like QuEra Aquila advertise only 'braket.ir.ahs.program' and
    must be excluded, otherwise a gate circuit submission fails with a Braket
    ValidationException.
    """
    action = getattr(props, "action", None)
    if not action:
        return False
    keys = action.keys() if hasattr(action, "keys") else []
    advertised = {getattr(key, "value", str(key)) for key in keys}
    return bool(advertised & _GATE_ACTION_TYPES)


def _to_braket(circuit: TranslatedCircuit):
    """Translate the provider-independent internal circuit into a Braket circuit.

    Braket measures all qubits implicitly when shots > 0, so explicit 'measure'
    operations are skipped.
    """
    from braket.circuits import Circuit

    braket = Circuit()
    for op in circuit.internal.operations:
        name = op.name.lower()
        if name == "measure":
            continue
        if name in {"h", "x", "y", "z"}:
            getattr(braket, name)(op.targets[0])
        elif name in {"rx", "ry", "rz"}:
            getattr(braket, name)(op.targets[0], op.params[0])
        elif name == "cx":
            control = op.controls[0] if op.controls else op.targets[0]
            target = op.targets[0] if op.controls else op.targets[1]
            braket.cnot(control, target)
        elif name == "cz":
            control = op.controls[0] if op.controls else op.targets[0]
            target = op.targets[0] if op.controls else op.targets[1]
            braket.cz(control, target)
        else:
            raise ValueError(f"Gate '{name}' is not supported by the Braket translator.")
    return braket
