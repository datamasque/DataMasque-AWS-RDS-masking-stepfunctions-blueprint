import os

import boto3


def lambda_handler(event, context):

    db_snapshot_identifier = event["DBSnapshotIdentifier"]
    db_instance_identifier = event["DBInstanceIdentifier"]
    db_type = event["DBType"]  # 'RDS' or 'Aurora'

    client = boto3.client("rds")

    parameters = {}

    if db_type == "RDS":
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
            "AvailabilityZone": event.get("PreferredAZ", instance["AvailabilityZone"]),
            "DBSubnetGroupName": instance["DBSubnetGroup"]["DBSubnetGroupName"],
            "OptionGroupName": (
                instance["OptionGroupMemberships"][0]["OptionGroupName"]
                if instance["OptionGroupMemberships"]
                else None
            ),
            "DBParameterGroupName": (
                instance["DBParameterGroups"][0]["DBParameterGroupName"]
                if instance["DBParameterGroups"]
                else None
            ),
            "VpcSecurityGroupIds": VpcSecurityGroupIds,
            "DeletionProtection": False,
        }

    elif db_type == "Aurora":
        # Generate parameters for Aurora cluster restoration
        response = client.describe_db_clusters(
            DBClusterIdentifier=db_instance_identifier
        )
        cluster = response["DBClusters"][0]

        # Extract VPC Security Group IDs
        VpcSecurityGroupIds = [
            d["VpcSecurityGroupId"] for d in cluster["VpcSecurityGroups"]
        ]

        # Build parameters dictionary for Aurora cluster
        parameters = {
            "DBSnapshotIdentifier": db_snapshot_identifier,
            "DBInstanceIdentifier": db_instance_identifier + "-datamasque",
            "AvailabilityZone": event.get("PreferredAZ"),
            "DBSubnetGroupName": cluster["DBSubnetGroup"],
            "DBClusterParameterGroupName": cluster["DBClusterParameterGroup"],
            "VpcSecurityGroupIds": VpcSecurityGroupIds,
            "Engine": cluster["Engine"],
            "EngineMode": cluster.get("EngineMode", "provisioned"),
            "DeletionProtection": False,
        }
        instance_response = client.describe_db_instances(
            DBInstanceIdentifier=cluster["DBClusterMembers"][0]["DBInstanceIdentifier"],
        )
        parameters["DBInstanceClass"] = instance_response["DBInstances"][0][
            "DBInstanceClass"
        ]
        parameters["DBParameterGroupName"] = instance_response["DBInstances"][0][
            "DBParameterGroups"
        ][0]["DBParameterGroupName"]

    else:
        raise ValueError(f"Invalid DBType '{db_type}'. Expected 'RDS' or 'Aurora'.")

    # Update the event with generated parameters
    event["parameters"] = parameters
    return event
