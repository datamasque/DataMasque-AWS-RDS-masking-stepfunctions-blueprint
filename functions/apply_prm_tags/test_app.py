"""
Unit tests for the PRM tagging Lambda.

Run from this directory:
    pytest test_app.py -v
"""
import os

import pytest

# app.py reads this at import time; stub it before importing.
os.environ.setdefault("PRM_TAG_VALUE", "pc:testproductcode")
os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")

import app
from app import PRM_TAG_KEY, get_resource_arn, lambda_handler

INSTANCE_ARN = "arn:aws:rds:us-east-1:111111111111:db:source-rds-datamasque"
CLUSTER_ARN = "arn:aws:rds:us-east-1:111111111111:cluster:source-aurora-datamasque"


class FakeRdsClient:
    """Records the RDS calls the handler makes so they can be asserted on."""

    def __init__(self):
        self.calls = {}

    def describe_db_instances(self, **kwargs):
        self.calls["describe_db_instances"] = kwargs
        return {"DBInstances": [{"DBInstanceArn": INSTANCE_ARN}]}

    def describe_db_clusters(self, **kwargs):
        self.calls["describe_db_clusters"] = kwargs
        return {"DBClusters": [{"DBClusterArn": CLUSTER_ARN}]}

    def add_tags_to_resource(self, **kwargs):
        self.calls["add_tags_to_resource"] = kwargs
        return {}

    def modify_db_instance(self, **kwargs):
        self.calls["modify_db_instance"] = kwargs
        return {}

    def modify_db_cluster(self, **kwargs):
        self.calls["modify_db_cluster"] = kwargs
        return {}


@pytest.fixture
def fake_client(monkeypatch):
    client = FakeRdsClient()
    monkeypatch.setattr(app.boto3, "client", lambda service, **kwargs: client)
    return client


def test_rds_instance_is_tagged_and_copies_tags_to_snapshot(fake_client):
    event = lambda_handler({"StageDB": "source-rds-datamasque", "DBType": "RDS"}, None)

    assert fake_client.calls["add_tags_to_resource"] == {
        "ResourceName": INSTANCE_ARN,
        "Tags": [{"Key": PRM_TAG_KEY, "Value": "pc:testproductcode"}],
    }
    assert fake_client.calls["modify_db_instance"]["CopyTagsToSnapshot"] is True
    assert "modify_db_cluster" not in fake_client.calls
    assert event["PRMTagApplied"] is True


@pytest.mark.parametrize(
    "DBType,call", [("RDS", "modify_db_instance"), ("Aurora", "modify_db_cluster")]
)
def test_modify_never_applies_immediately(fake_client, DBType, call):
    """`ApplyImmediately` would force unrelated pending modifications to apply
    now, and an instance in `modifying` fails the `CreateDBSnapshot` that
    follows, which routes the workflow to `CleanupOnFailure`."""
    lambda_handler({"StageDB": "source-datamasque", "DBType": DBType}, None)

    assert "ApplyImmediately" not in fake_client.calls[call]


def test_aurora_cluster_is_tagged_and_copies_tags_to_snapshot(fake_client):
    event = lambda_handler(
        {"StageDB": "source-aurora-datamasque", "DBType": "Aurora"}, None
    )

    assert fake_client.calls["add_tags_to_resource"]["ResourceName"] == CLUSTER_ARN
    assert fake_client.calls["modify_db_cluster"]["CopyTagsToSnapshot"] is True
    assert "modify_db_instance" not in fake_client.calls
    assert event["PRMTagApplied"] is True


def test_event_fields_are_preserved_for_downstream_states(fake_client):
    event = lambda_handler(
        {
            "StageDB": "source-rds-datamasque",
            "DBType": "RDS",
            "MaskedDBSnapshotIdentifier": "keep-me",
        },
        None,
    )

    assert event["MaskedDBSnapshotIdentifier"] == "keep-me"


def test_unknown_db_type_is_rejected(fake_client):
    with pytest.raises(ValueError, match="Invalid DBType"):
        lambda_handler({"StageDB": "source-rds-datamasque", "DBType": "Redshift"}, None)

    assert fake_client.calls == {}


def test_tagging_failure_propagates_to_the_state_machine(fake_client, monkeypatch):
    def boom(**kwargs):
        raise RuntimeError("AccessDenied")

    monkeypatch.setattr(fake_client, "add_tags_to_resource", boom)

    with pytest.raises(RuntimeError, match="AccessDenied"):
        lambda_handler({"StageDB": "source-rds-datamasque", "DBType": "RDS"}, None)


@pytest.mark.parametrize(
    "DBType,expected_arn", [("RDS", INSTANCE_ARN), ("Aurora", CLUSTER_ARN)]
)
def test_get_resource_arn_resolves_both_engines(fake_client, DBType, expected_arn):
    assert get_resource_arn(fake_client, "source-datamasque", DBType) == expected_arn
