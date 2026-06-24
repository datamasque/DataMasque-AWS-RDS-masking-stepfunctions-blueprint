import logging
import os

import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):

    client = boto3.client("rds")
    vpc_sg = os.environ["DATAMASQUE_SG"]

    try:
        if event["DBType"] == "RDS":
            params = event["parameters"]
            restore_kwargs = {
                "DBSnapshotIdentifier": params["DBSnapshotIdentifier"],
                "DBInstanceIdentifier": params["DBInstanceIdentifier"],
                "DBInstanceClass": params["DBInstanceClass"],
                # PreferredAZ is optional: describe_db_instances already resolved
                # AvailabilityZone to the source AZ when it was not supplied.
                "AvailabilityZone": params["AvailabilityZone"],
                "DBSubnetGroupName": params["DBSubnetGroupName"],
                "VpcSecurityGroupIds": [vpc_sg],
                "DeletionProtection": params["DeletionProtection"],
            }
            # OptionGroupName / DBParameterGroupName are None when the source has
            # none; boto3 rejects None, so only pass them when present.
            if params.get("OptionGroupName"):
                restore_kwargs["OptionGroupName"] = params["OptionGroupName"]
            if params.get("DBParameterGroupName"):
                restore_kwargs["DBParameterGroupName"] = params["DBParameterGroupName"]

            # Restore an RDS instance from a snapshot
            restore_response = client.restore_db_instance_from_db_snapshot(**restore_kwargs)
            event["status"] = "success"
            event["StageDB"] = event["parameters"]["DBInstanceIdentifier"]
            logger.info("RDS instance restore initiated: %s", restore_response.get("DBInstance", {}).get("DBInstanceIdentifier"))

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
            logger.info("Aurora cluster restore initiated: %s", restore_response.get("DBCluster", {}).get("DBClusterIdentifier"))

        else:
            raise ValueError(
                f"Invalid DBType '{event['DBType']}'. Expected 'RDS' or 'Aurora'."
            )

        return event

    except Exception as e:
        logger.error("Error restoring snapshot: %s", e)
        # Preserve DBType/StageDB so the failure-cleanup routing can run.
        event["status"] = "failure"
        event["Error"] = f"Error restoring snapshot: {e}"
        event["StageDB"] = event.get("parameters", {}).get(
            "DBInstanceIdentifier", "unknown"
        )
        return event
