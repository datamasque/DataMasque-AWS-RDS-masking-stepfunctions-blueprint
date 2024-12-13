import os

import boto3


def lambda_handler(event, context):

    db_snapshot_identifier = event["DBSnapshotIdentifier"]
    db_instance_identifier = event["DBInstanceIdentifier"]

    client = boto3.client("rds")

    response = client.describe_db_instances(
        DBInstanceIdentifier=db_instance_identifier,
    )

    instance = response["DBInstances"][0]

    security_groups = instance["VpcSecurityGroups"]

    VpcSecurityGroupIds = [d["VpcSecurityGroupId"] for d in security_groups]

    parameters = {
        "DBSnapshotIdentifier": db_snapshot_identifier,
        "DBInstanceIdentifier": instance["DBInstanceIdentifier"] + "-datamasque",
        "DBInstanceClass": instance["DBInstanceClass"],
        "AvailabilityZone": event["PreferredAZ"],
        "DBSubnetGroupName": instance["DBSubnetGroup"]["DBSubnetGroupName"],
        "OptionGroupName": instance["OptionGroupMemberships"][0]["OptionGroupName"],
        "DBParameterGroupName": instance["DBParameterGroups"][0][
            "DBParameterGroupName"
        ],
        "VpcSecurityGroupIds": VpcSecurityGroupIds,
        "DeletionProtection": False,
    }

    event["parameters"] = parameters
    return event
