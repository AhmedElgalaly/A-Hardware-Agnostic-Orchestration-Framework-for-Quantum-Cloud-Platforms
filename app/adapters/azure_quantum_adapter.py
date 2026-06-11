from __future__ import annotations

from time import perf_counter

from qiskit import transpile

from app.adapters.base import QuantumBackendAdapter
from app.config import settings
from app.models import BackendCapability, BackendType, JobCreateRequest, NormalizedBackendResult
from app.services.circuit_translator import TranslatedCircuit
from app.services.result_normalizer import normalize_failure, normalize_success


class AzureQuantumAdapter(QuantumBackendAdapter):
    """Azure Quantum adapter via the azure-quantum Qiskit provider.

    Enabled with ENABLE_AZURE_QUANTUM=true and an Azure Quantum workspace
    (subscription id, resource group, workspace name, location). Authentication
    uses a service principal when AZURE_TENANT_ID/AZURE_CLIENT_ID/
    AZURE_CLIENT_SECRET are set, otherwise the default Azure credential chain.
    Without the SDK or credentials the adapter reports itself unavailable.
    """

    _provider = "azure_quantum"
    _CACHE_TTL_SECONDS = 300

    def __init__(self) -> None:
        self._provider_client = None
        self._import_error: str | None = None
        self._auth_error: str | None = None
        self._caps_cache: list[BackendCapability] | None = None
        self._caps_cached_at: float = 0.0
        self._initialize()

    def provider_name(self) -> str:
        return self._provider

    def is_available(self) -> bool:
        return self._provider_client is not None

    def _initialize(self) -> None:
        if not settings.enable_azure_quantum:
            self._auth_error = "Azure Quantum adapter is disabled. Set ENABLE_AZURE_QUANTUM=true to enable it."
            return
        required = [
            settings.azure_subscription_id,
            settings.azure_resource_group,
            settings.azure_workspace_name,
            settings.azure_location,
        ]
        if not all(required):
            self._auth_error = (
                "Azure workspace config incomplete. Set AZURE_SUBSCRIPTION_ID, "
                "AZURE_RESOURCE_GROUP, AZURE_WORKSPACE_NAME, AZURE_LOCATION."
            )
            return
        try:
            from azure.quantum.qiskit import AzureQuantumProvider
        except Exception as exc:  # pragma: no cover - optional SDK
            self._import_error = f"azure-quantum not installed: {exc}"
            return
        try:
            credential = self._build_credential()
            self._provider_client = AzureQuantumProvider(
                resource_id=(
                    f"/subscriptions/{settings.azure_subscription_id}"
                    f"/resourceGroups/{settings.azure_resource_group}"
                    f"/providers/Microsoft.Quantum/Workspaces/{settings.azure_workspace_name}"
                ),
                location=settings.azure_location,
                credential=credential,
            )
        except Exception as exc:  # pragma: no cover
            self._auth_error = f"Azure authentication failed: {type(exc).__name__}"
            self._provider_client = None

    def _build_credential(self):
        if settings.azure_tenant_id and settings.azure_client_id and settings.azure_client_secret:
            from azure.identity import ClientSecretCredential

            return ClientSecretCredential(
                tenant_id=settings.azure_tenant_id,
                client_id=settings.azure_client_id,
                client_secret=settings.azure_client_secret,
            )
        return None  # AzureQuantumProvider falls back to the default credential chain

    def capabilities(self) -> list[BackendCapability]:
        if not self._provider_client:
            return []
        from time import time

        now = time()
        if self._caps_cache is not None and (now - self._caps_cached_at) < self._CACHE_TTL_SECONDS:
            return self._caps_cache
        self._caps_cache = self._discover_capabilities()
        self._caps_cached_at = now
        return self._caps_cache

    def _discover_capabilities(self) -> list[BackendCapability]:
        import logging

        logger = logging.getLogger("quantum_orchestrator")
        caps: list[BackendCapability] = []
        try:
            backends = self._provider_client.backends()
        except Exception as exc:
            logger.warning("Azure backend discovery failed: %s: %s", type(exc).__name__, exc)
            return []

        for backend in backends:
            try:
                name = _backend_name(backend)
                config = getattr(backend, "configuration", None)
                config = config() if callable(config) else None
                is_sim = "simulator" in name.lower() or bool(getattr(config, "simulator", False))
                num_qubits = getattr(config, "n_qubits", None) or getattr(backend, "num_qubits", 0) or 0
                basis = list(getattr(config, "basis_gates", None) or getattr(backend, "operation_names", []) or [])
                caps.append(
                    BackendCapability(
                        provider=self._provider,
                        backend_name=name,
                        backend_type=BackendType.simulator if is_sim else BackendType.hardware,
                        num_qubits=int(num_qubits),
                        native_gates=basis,
                        topology="azure_target",
                        noise_model_available=False,
                        estimated_latency_ms=4000 if is_sim else 60000,
                        metadata={"sdk": "azure-quantum"},
                    )
                )
            except Exception as exc:  # one malformed target must not hide the rest
                logger.warning("Azure target skipped during discovery: %s: %s", type(exc).__name__, exc)
        if not caps:
            logger.warning(
                "Azure is authenticated but no targets were discovered. Check that your "
                "workspace has quantum providers added (e.g. IonQ) and that AZURE_LOCATION matches."
            )
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
        if not self._provider_client:
            return normalize_failure(
                backend_capability,
                job_request.shots,
                self._auth_error or self._import_error or "Azure Quantum not configured.",
                circuit.internal.metadata,
            )
        try:
            backend = self._provider_client.get_backend(backend_capability.backend_name)
            depth_before = circuit.qiskit.depth() or 0
            started = perf_counter()
            transpiled = transpile(circuit.qiskit, backend)
            job = backend.run(transpiled, shots=job_request.shots)
            result = job.result()
            execution_time_ms = round((perf_counter() - started) * 1000, 3)
            return normalize_success(
                backend_capability,
                job_request.shots,
                result.get_counts(),
                circuit.internal.metadata,
                execution_time_ms,
                depth_before,
                transpiled.depth() or 0,
            )
        except Exception as exc:
            return normalize_failure(backend_capability, job_request.shots, str(exc), circuit.internal.metadata)


def _backend_name(backend) -> str:
    """Return a backend's name across Qiskit versions, where `name` may be a
    string property (BackendV2) or a callable method (BackendV1)."""
    name = getattr(backend, "name", None)
    return str(name() if callable(name) else name)
