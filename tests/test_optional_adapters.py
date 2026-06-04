import app.adapters.aws_braket_adapter as aws_module
import app.adapters.azure_quantum_adapter as azure_module
import app.adapters.ibm_quantum_adapter as ibm_module
from app.adapters.aws_braket_adapter import AWSBraketAdapter
from app.adapters.azure_quantum_adapter import AzureQuantumAdapter
from app.adapters.ibm_quantum_adapter import IBMQuantumAdapter


def test_ibm_adapter_is_optional_without_credentials(monkeypatch):
    monkeypatch.setattr(ibm_module.settings, "enable_ibm", False)
    monkeypatch.setattr(ibm_module.settings, "ibm_quantum_token", "")

    adapter = IBMQuantumAdapter()

    assert adapter.provider_name() == "ibm"
    assert adapter.is_available() is False
    assert adapter.capabilities() == []


def test_aws_and_azure_skeletons_are_unavailable_by_default(monkeypatch):
    monkeypatch.setattr(aws_module.settings, "enable_aws_braket", False)
    monkeypatch.setattr(azure_module.settings, "enable_azure_quantum", False)

    aws = AWSBraketAdapter()
    azure = AzureQuantumAdapter()

    assert aws.is_available() is False
    assert aws.capabilities() == []
    assert azure.is_available() is False
    assert azure.capabilities() == []


def test_enabled_but_unconfigured_providers_report_no_backends(monkeypatch):
    # Enabling the flag without the required cloud configuration must not create
    # backends or attempt any network calls; the adapter stays unavailable.
    monkeypatch.setattr(aws_module.settings, "enable_aws_braket", True)
    monkeypatch.setattr(aws_module.settings, "aws_braket_s3_bucket", "")
    monkeypatch.setattr(aws_module.settings, "aws_access_key_id", "")
    monkeypatch.setattr(aws_module.settings, "aws_secret_access_key", "")

    monkeypatch.setattr(azure_module.settings, "enable_azure_quantum", True)
    monkeypatch.setattr(azure_module.settings, "azure_subscription_id", "")
    monkeypatch.setattr(azure_module.settings, "azure_resource_group", "")
    monkeypatch.setattr(azure_module.settings, "azure_workspace_name", "")
    monkeypatch.setattr(azure_module.settings, "azure_location", "")

    aws = AWSBraketAdapter()
    azure = AzureQuantumAdapter()

    assert aws.is_available() is False
    assert aws.capabilities() == []
    assert azure.is_available() is False
    assert azure.capabilities() == []
