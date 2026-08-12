"""
Unit tests for the staging clone restore Lambda.

Run from this directory:
    pytest test_app.py -v
"""
import os

import pytest

# app.py reads these at import time; stub them before importing.
os.environ.setdefault("PRM_TAG_VALUE", "pc:testproductcode")
os.environ.setdefault("DATAMASQUE_SG", "sg-0123456789abcdef0")
os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")

import app
from app import lambda_handler

EXPECTED_TAGS = [{"Key": "aws-apn-id", "Value": "pc:testproductcode"}]

RDS_PARAMETERS = {
    "DBSnapshotIdentifier": "source-rds-snapshot",
    "DBInstanceIdentifier": "source-rds-datamasque",
    "DBInstanceClass": "db.t3.medium",
    "AvailabilityZone": "us-east-1a",
    "DBSubnetGroupName": "datamasque-subnet-group",
    "DeletionProtection": False,
}

AURORA_PARAMETERS = {
    "DBSnapshotIdentifier": "source-aurora-snapshot",
    "DBInstanceIdentifier": "source-aurora-datamasque",
    "Engine": "aurora-postgresql",
    "EngineMode": "provisioned",
    "DBSubnetGroupName": "datamasque-subnet-group",
}


class FakeRdsClient:
    """Records the RDS calls the handler makes so they can be asserted on."""

    def __init__(self):
        self.calls = {}

    def restore_db_instance_from_db_snapshot(self, **kwargs):
        self.calls["restore_db_instance_from_db_snapshot"] = kwargs
        return {"DBInstance": {"DBInstanceIdentifier": kwargs["DBInstanceIdentifier"]}}

    def restore_db_cluster_from_snapshot(self, **kwargs):
        self.calls["restore_db_cluster_from_snapshot"] = kwargs
        return {"DBCluster": {"DBClusterIdentifier": kwargs["DBClusterIdentifier"]}}


@pytest.fixture
def fake_client(monkeypatch):
    client = FakeRdsClient()
    monkeypatch.setattr(app.boto3, "client", lambda service, **kwargs: client)
    return client


def test_rds_staging_clone_is_tagged_at_restore(fake_client):
    event = lambda_handler({"DBType": "RDS", "parameters": RDS_PARAMETERS}, None)

    restore = fake_client.calls["restore_db_instance_from_db_snapshot"]
    assert restore["Tags"] == EXPECTED_TAGS
    assert event["status"] == "success"


def test_aurora_staging_clone_is_tagged_at_restore(fake_client):
    event = lambda_handler({"DBType": "Aurora", "parameters": AURORA_PARAMETERS}, None)

    restore = fake_client.calls["restore_db_cluster_from_snapshot"]
    assert restore["Tags"] == EXPECTED_TAGS
    assert event["status"] == "success"


@pytest.mark.parametrize(
    "DBType,parameters,call",
    [
        ("RDS", RDS_PARAMETERS, "restore_db_instance_from_db_snapshot"),
        ("Aurora", AURORA_PARAMETERS, "restore_db_cluster_from_snapshot"),
    ],
)
def test_restore_enables_copy_tags_to_snapshot(fake_client, DBType, parameters, call):
    """`CopyTagsToSnapshot` is set here rather than by a later `ModifyDBInstance`:
    a modify can leave the clone in `modifying`, which fails the snapshot that
    follows and tears down a completed masking run."""
    lambda_handler({"DBType": DBType, "parameters": parameters}, None)

    assert fake_client.calls[call]["CopyTagsToSnapshot"] is True


def test_restore_failure_preserves_cleanup_routing_fields(fake_client, monkeypatch):
    def boom(**kwargs):
        raise RuntimeError("InvalidSnapshotState")

    monkeypatch.setattr(fake_client, "restore_db_instance_from_db_snapshot", boom)

    event = lambda_handler({"DBType": "RDS", "parameters": RDS_PARAMETERS}, None)

    assert event["status"] == "failure"
    assert event["StageDB"] == "source-rds-datamasque"


def test_unknown_db_type_is_rejected(fake_client):
    event = lambda_handler({"DBType": "Redshift", "parameters": RDS_PARAMETERS}, None)

    assert event["status"] == "failure"
    assert fake_client.calls == {}
