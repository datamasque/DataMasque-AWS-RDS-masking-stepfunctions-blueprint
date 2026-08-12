"""
Unit tests for the masked snapshot Lambda.

Run from this directory:
    pytest test_app.py -v
"""
import os

import pytest

# app.py reads this at import time; stub it before importing.
os.environ.setdefault("PRM_TAG_VALUE", "pc:testproductcode")
os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")

import app
from app import PRM_TAGS, lambda_handler

EXPECTED_TAGS = [{"Key": "aws-apn-id", "Value": "pc:testproductcode"}]


class FakeRdsClient:
    """Records the RDS calls the handler makes so they can be asserted on."""

    def __init__(self):
        self.calls = {}

    def create_db_snapshot(self, **kwargs):
        self.calls["create_db_snapshot"] = kwargs
        return {
            "DBSnapshot": {
                "DBSnapshotIdentifier": kwargs["DBSnapshotIdentifier"],
                "Status": "creating",
            }
        }

    def create_db_cluster_snapshot(self, **kwargs):
        self.calls["create_db_cluster_snapshot"] = kwargs
        return {
            "DBClusterSnapshot": {
                "DBClusterSnapshotIdentifier": kwargs["DBClusterSnapshotIdentifier"],
                "Status": "creating",
            }
        }


@pytest.fixture
def fake_client(monkeypatch):
    client = FakeRdsClient()
    monkeypatch.setattr(app.boto3, "client", lambda service, **kwargs: client)
    return client


def test_prm_tag_value_comes_from_the_environment():
    assert PRM_TAGS == EXPECTED_TAGS


def test_rds_snapshot_is_tagged_at_creation(fake_client):
    event = lambda_handler({"StageDB": "source-rds-datamasque", "DBType": "RDS"}, None)

    assert fake_client.calls["create_db_snapshot"]["Tags"] == EXPECTED_TAGS
    assert event["MaskedSnapshotStatus"] == "creating"


def test_aurora_snapshot_is_tagged_at_creation(fake_client):
    event = lambda_handler(
        {"StageDB": "source-aurora-datamasque", "DBType": "Aurora"}, None
    )

    assert fake_client.calls["create_db_cluster_snapshot"]["Tags"] == EXPECTED_TAGS
    assert event["MaskedSnapshotStatus"] == "creating"


def test_snapshot_identifier_matches_the_iam_scoped_pattern(fake_client):
    """The `rds:AddTagsToResource` grant is scoped to `*-masked-*`, so a change
    to this identifier format would silently lose the tagging permission."""
    lambda_handler({"StageDB": "source-rds-datamasque", "DBType": "RDS"}, None)

    identifier = fake_client.calls["create_db_snapshot"]["DBSnapshotIdentifier"]
    assert identifier.startswith("source-rds-datamasque-masked-")


@pytest.mark.parametrize("DBType", ["RDS", "Aurora"])
def test_tagging_failure_fails_the_snapshot_rather_than_shipping_untagged(
    fake_client, monkeypatch, DBType
):
    """An unattributed snapshot must never ship silently: tagging is part of the
    create call, so a rejected tag routes the workflow to `CleanupOnFailure`."""

    def boom(**kwargs):
        raise RuntimeError("AccessDenied on rds:AddTagsToResource")

    monkeypatch.setattr(fake_client, "create_db_snapshot", boom)
    monkeypatch.setattr(fake_client, "create_db_cluster_snapshot", boom)

    event = lambda_handler({"StageDB": "source-datamasque", "DBType": DBType}, None)

    assert event["MaskedSnapshotStatus"] == "failed"
    assert "AccessDenied" in event["Error"]


def test_unknown_db_type_is_rejected(fake_client):
    event = lambda_handler(
        {"StageDB": "source-rds-datamasque", "DBType": "Redshift"}, None
    )

    assert event["MaskedSnapshotStatus"] == "failed"
    assert fake_client.calls == {}
