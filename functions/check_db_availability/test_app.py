"""
Unit tests for the staging clone availability Lambda.

Run from this directory:
    pytest test_app.py -v
"""
import os

import pytest

# app.py reads this at import time; stub it before importing.
os.environ.setdefault("PRM_TAG_VALUE", "pc:testproductcode")
os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")

import app
from app import lambda_handler

EXPECTED_TAGS = [{"Key": "aws-apn-id", "Value": "pc:testproductcode"}]

AURORA_EVENT = {
    "DBType": "Aurora",
    "StageDB": "source-aurora-datamasque",
    "parameters": {
        "DBInstanceIdentifier": "source-aurora-datamasque",
        "DBInstanceClass": "db.r6g.large",
        "Engine": "aurora-postgresql",
        "DBSubnetGroupName": "datamasque-subnet-group",
        "AvailabilityZone": "us-east-1a",
    },
}


class FakeRdsClient:
    """Records the RDS calls the handler makes so they can be asserted on."""

    def __init__(self, cluster_status="available"):
        self.calls = {}
        self.cluster_status = cluster_status

    def describe_db_clusters(self, **kwargs):
        self.calls["describe_db_clusters"] = kwargs
        return {"DBClusters": [{"Status": self.cluster_status}]}

    def describe_db_instances(self, **kwargs):
        self.calls["describe_db_instances"] = kwargs
        return {"DBInstances": [{"DBInstanceStatus": "available"}]}

    def create_db_instance(self, **kwargs):
        self.calls["create_db_instance"] = kwargs
        return {"DBInstance": {"DBInstanceIdentifier": kwargs["DBInstanceIdentifier"]}}


@pytest.fixture
def fake_client(monkeypatch):
    client = FakeRdsClient()
    monkeypatch.setattr(app.boto3, "client", lambda service, **kwargs: client)
    return client


def test_aurora_cluster_member_is_tagged_at_creation(fake_client):
    """The cluster member is created here, not by the restore call, so it would
    otherwise be the one chargeable resource in the chain with no attribution."""
    event = lambda_handler(dict(AURORA_EVENT), None)

    assert fake_client.calls["create_db_instance"]["Tags"] == EXPECTED_TAGS
    assert event["StgDbInstanceId"] == "source-aurora-datamasque-1"


def test_rds_availability_check_creates_nothing(fake_client):
    event = lambda_handler(
        {"DBType": "RDS", "StageDB": "source-rds-datamasque"}, None
    )

    assert "create_db_instance" not in fake_client.calls
    assert event["status"] == "available"


def test_previous_step_failure_short_circuits(fake_client):
    event = lambda_handler(
        {"DBType": "RDS", "StageDB": "source-rds-datamasque", "status": "failure"}, None
    )

    assert fake_client.calls == {}
    assert event["status"] == "failure"
