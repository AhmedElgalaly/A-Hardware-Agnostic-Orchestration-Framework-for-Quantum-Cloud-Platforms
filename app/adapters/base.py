from __future__ import annotations

from abc import ABC, abstractmethod

from app.models import BackendCapability, JobCreateRequest, NormalizedBackendResult
from app.services.circuit_translator import TranslatedCircuit


class QuantumBackendAdapter(ABC):
    @abstractmethod
    def provider_name(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def capabilities(self) -> list[BackendCapability]:
        raise NotImplementedError

    @abstractmethod
    def is_available(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def supports_backend(self, backend_name: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    def run(
        self,
        job_id: str,
        circuit: TranslatedCircuit,
        job_request: JobCreateRequest,
        backend_capability: BackendCapability,
    ) -> NormalizedBackendResult:
        raise NotImplementedError
