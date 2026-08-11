import os

import boto3

PRM_TAG_KEY = "aws-apn-id"
PRM_TAG_VALUE = os.environ["PRM_TAG_VALUE"]


def lambda_handler(event, context):
    """Apply the PRM attribution tag to the staging database.

    Runs after masking completes and before the masked snapshot is created, so
    `CopyTagsToSnapshot` carries the tag onto the snapshot and onto every
    database later restored from it.

    Raises on failure. The state machine retries, then continues to
    `CreateDBSnapshot` on a persistent failure: a missing attribution tag is
    not worth discarding a completed masking run over.
    """
    DBId = event["StageDB"]
    DBType = event["DBType"]  # Either "RDS" or "Aurora"
    client = boto3.client("rds")

    arn = get_resource_arn(client, DBId, DBType)
    client.add_tags_to_resource(
        ResourceName=arn,
        Tags=[{"Key": PRM_TAG_KEY, "Value": PRM_TAG_VALUE}],
    )
    print(f"Applied PRM tag {PRM_TAG_KEY}={PRM_TAG_VALUE} to {arn}")

    # Tags are only inherited by a snapshot when the source has
    # CopyTagsToSnapshot enabled, which is off by default on a restored clone.
    #
    # No `ApplyImmediately`: CopyTagsToSnapshot takes effect on its own, while
    # the flag would also force any other pending modification to apply now.
    # That can put the instance into `modifying`, which fails the
    # `CreateDBSnapshot` that follows and tears down a completed masking run.
    if DBType == "RDS":
        client.modify_db_instance(
            DBInstanceIdentifier=DBId,
            CopyTagsToSnapshot=True,
        )
    else:
        client.modify_db_cluster(
            DBClusterIdentifier=DBId,
            CopyTagsToSnapshot=True,
        )
    print(f"Enabled CopyTagsToSnapshot on {DBId}")

    event["PRMTagApplied"] = True
    return event


def get_resource_arn(client, DBId, DBType):
    if DBType == "Aurora":
        response = client.describe_db_clusters(DBClusterIdentifier=DBId)
        return response["DBClusters"][0]["DBClusterArn"]
    elif DBType == "RDS":
        response = client.describe_db_instances(DBInstanceIdentifier=DBId)
        return response["DBInstances"][0]["DBInstanceArn"]
    else:
        raise ValueError(f"Invalid DBType: {DBType}. Expected 'RDS' or 'Aurora'.")
