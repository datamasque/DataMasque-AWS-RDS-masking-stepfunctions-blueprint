import os

import boto3


def lambda_handler(event, context):

    client = boto3.client("rds")
    vpc_sg = os.environ["DATANASQUE_SG"]

    try:
        if event["DBType"] == "RDS":
            # Restore an RDS instance from a snapshot
            restore_response = client.restore_db_instance_from_db_snapshot(
                DBSnapshotIdentifier=event["parameters"]["DBSnapshotIdentifier"],
                DBInstanceIdentifier=event["parameters"]["DBInstanceIdentifier"],
                DBInstanceClass=event["parameters"]["DBInstanceClass"],
                AvailabilityZone=event["PreferredAZ"],
                DBSubnetGroupName=event["parameters"]["DBSubnetGroupName"],
                OptionGroupName=event["parameters"]["OptionGroupName"],
                DBParameterGroupName=event["parameters"]["DBParameterGroupName"],
                VpcSecurityGroupIds=[vpc_sg],
                DeletionProtection=event["parameters"]["DeletionProtection"],
            )
            event["status"] = "success"
            event["StageDB"] = event["parameters"]["DBInstanceIdentifier"]
            print(f"RDS instance restore initiated: {restore_response}")

        elif event["DBType"] == "Aurora":
            # Restore an Aurora cluster from a snapshot
            restore_response = client.restore_db_cluster_from_snapshot(
                SnapshotIdentifier=event["parameters"]["DBSnapshotIdentifier"],
                DBClusterIdentifier=event["parameters"]["DBInstanceIdentifier"],
                Engine=event["parameters"]["Engine"],
                EngineMode=event["parameters"]["EngineMode"],
                DBSubnetGroupName=event["parameters"]["DBSubnetGroupName"],
                VpcSecurityGroupIds=[vpc_sg],
                DeletionProtection=False,
            )
            event["status"] = "success"
            event["StageDB"] = event["parameters"]["DBInstanceIdentifier"]
            print(f"Aurora cluster restore initiated: {restore_response}")

        else:
            raise ValueError(
                f"Invalid DBType '{event['DBType']}'. Expected 'RDS' or 'Aurora'."
            )

        return event

    except Exception as e:
        print(f"Error restoring snapshot: {e}")
        return {
            "status": "failure",
            "Error": f"Error restoring snapshot: {e}",
            "StageDB": event.get("parameters", {}).get(
                "DBInstanceIdentifier", "unknown"
            ),
        }
