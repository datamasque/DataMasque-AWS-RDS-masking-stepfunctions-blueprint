"""
Unit tests for the TLS-verification flag parsing in app.py.

Run from this directory:
    pytest test_app.py -v
"""
import os

import pytest

# app.py reads these at import time; stub them before importing.
os.environ.setdefault("DATAMASQUE_BASE_URL", "http://localhost:8080/")
os.environ.setdefault(
    "DATAMASQUE_SECRET_ARN",
    "arn:aws:secretsmanager:us-east-1:111111111111:secret:fake-AbCdEf",
)
os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")

from app import parse_verify_tls


@pytest.mark.parametrize("value", ["false", "False", "FALSE", "0", "no", " no ", "No"])
def test_parse_verify_tls_disables_only_on_explicit_falsey(value):
    assert parse_verify_tls(value) is False


@pytest.mark.parametrize("value", ["true", "True", "1", "yes", "", "anything", None])
def test_parse_verify_tls_defaults_secure(value):
    assert parse_verify_tls(value) is True
