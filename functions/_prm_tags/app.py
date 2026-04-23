import json
import os

import boto3
from botocore.config import Config

PRM_TAG_KEY = "aws-apn-id"
PRM_TAG_VALUE = os.environ.get("PRM_TAG_VALUE", "pc:PLACEHOLDER_PRODUCT_CODE")

boto_config = Config(
    user_agent_appid=os.environ.get("AWS_SDK_UA_APP_ID", PRM_TAG_VALUE)
)


def lambda_handler(event, context):
    """Apply PRM tag to the staging DB and enable CopyTagsToSnapshot.

    Inserted between masking completion and masked snapshot creation
    so the PRM tag propagates to the snapshot and all downstream restores.
    """
    client = boto3.client("rds", config=boto_config)
    db_identifier = event["StageDB"]
    db_type = event["DBType"]

    try:
        arn = _get_resource_arn(client, db_identifier, db_type)

        client.add_tags_to_resource(
            ResourceName=arn,
            Tags=[{"Key": PRM_TAG_KEY, "Value": PRM_TAG_VALUE}],
        )
        print(f"Applied PRM tag {PRM_TAG_KEY}={PRM_TAG_VALUE} to {arn}")

        if db_type == "RDS":
            client.modify_db_instance(
                DBInstanceIdentifier=db_identifier,
                CopyTagsToSnapshot=True,
                ApplyImmediately=True,
            )
            print(f"Enabled CopyTagsToSnapshot on {db_identifier}")

        event["PRMTagApplied"] = True
        return event

    except Exception as e:
        print(f"Error applying PRM tags: {e}")
        event["PRMTagApplied"] = False
        event["PRMTagError"] = str(e)
        return event


def _get_resource_arn(client, db_identifier, db_type):
    if db_type == "Aurora":
        resp = client.describe_db_clusters(DBClusterIdentifier=db_identifier)
        return resp["DBClusters"][0]["DBClusterArn"]
    else:
        resp = client.describe_db_instances(DBInstanceIdentifier=db_identifier)
        return resp["DBInstances"][0]["DBInstanceArn"]
