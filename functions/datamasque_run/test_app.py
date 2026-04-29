"""
Unit tests for resolve_run_secret in app.py.

Run from this directory:
    pytest test_app.py -v
"""
import os
from unittest.mock import MagicMock

import pytest
from botocore.exceptions import ClientError

# app.py reads these at import time; stub them before importing.
os.environ.setdefault("DATAMASQUE_BASE_URL", "http://localhost:8080/")
os.environ.setdefault("DATAMASQUE_SECRET_ARN", "arn:aws:secretsmanager:us-east-1:111111111111:secret:fake-AbCdEf")
os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")

from app import RunSecretError, resolve_run_secret


@pytest.fixture
def secrets_client():
    return MagicMock()


def _base_event():
    return {
        "DBInstanceIdentifier": "test-db",
        "DataMasqueRulesetId": "00000000-0000-0000-0000-000000000000",
        "DBSecretIdentifier": "datamasque/test-connections-AbCdEf",
        "StageDB": "test-db-stage",
    }


def test_random_mode_generates_high_entropy_secret(secrets_client):
    rs1 = resolve_run_secret(_base_event(), secrets_client)
    rs2 = resolve_run_secret(_base_event(), secrets_client)

    assert isinstance(rs1, str)
    assert len(rs1) >= 40
    assert rs1 != rs2
    secrets_client.get_secret_value.assert_not_called()


def test_manual_mode_uses_runsecret_verbatim(secrets_client):
    event = {**_base_event(), "RunSecret": "user-typed-secret"}

    assert resolve_run_secret(event, secrets_client) == "user-typed-secret"
    secrets_client.get_secret_value.assert_not_called()


def test_manual_mode_rejects_empty_string(secrets_client):
    event = {**_base_event(), "RunSecret": ""}

    with pytest.raises(RunSecretError, match="non-empty"):
        resolve_run_secret(event, secrets_client)


def test_manual_mode_rejects_non_string(secrets_client):
    event = {**_base_event(), "RunSecret": 12345}

    with pytest.raises(RunSecretError, match="non-empty"):
        resolve_run_secret(event, secrets_client)


def test_aws_secret_arn_uses_secretstring(secrets_client):
    arn = "arn:aws:secretsmanager:us-east-1:111111111111:secret:datamasque/foo-run-secret-AbCdEf"
    secrets_client.get_secret_value.return_value = {"SecretString": "from-secrets-manager"}
    event = {**_base_event(), "AwsSecretArn": arn}

    assert resolve_run_secret(event, secrets_client) == "from-secrets-manager"
    secrets_client.get_secret_value.assert_called_once_with(SecretId=arn)


def test_aws_secret_arn_rejects_secretbinary(secrets_client):
    secrets_client.get_secret_value.return_value = {"SecretBinary": b"binary-data"}
    event = {**_base_event(), "AwsSecretArn": "arn:aws:secretsmanager:us-east-1:1:secret:x"}

    with pytest.raises(RunSecretError, match="SecretBinary not supported"):
        resolve_run_secret(event, secrets_client)


def test_aws_secret_arn_propagates_client_error(secrets_client):
    secrets_client.get_secret_value.side_effect = ClientError(
        {"Error": {"Code": "AccessDeniedException", "Message": "denied"}},
        "GetSecretValue",
    )
    event = {**_base_event(), "AwsSecretArn": "arn:aws:secretsmanager:us-east-1:1:secret:x"}

    with pytest.raises(ClientError):
        resolve_run_secret(event, secrets_client)


def test_runsecret_wins_over_awssecretarn(secrets_client):
    event = {
        **_base_event(),
        "RunSecret": "literal-wins",
        "AwsSecretArn": "arn:aws:secretsmanager:us-east-1:1:secret:x",
    }

    assert resolve_run_secret(event, secrets_client) == "literal-wins"
    secrets_client.get_secret_value.assert_not_called()
