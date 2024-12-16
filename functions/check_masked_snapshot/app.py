import json
import os
from datetime import datetime
from operator import itemgetter

import boto3

"""
Creates a snapshot of the masked RDS instance.


    
"""


def lambda_handler(event, context):

    DBIdentifier = event["StageDB"]  # Can be an RDS instance or Aurora cluster
    DBType = event["DBType"]  # Either "RDS" or "Aurora"

    client = boto3.client("rds")

    try:
        print("Checking the status of masked DB snapshot")

        if DBType == "RDS":
            # Check the status of an RDS snapshot
            response = client.describe_db_snapshots(
                DBInstanceIdentifier=DBIdentifier,
                Filters=[
                    {
                        "Name": "db-snapshot-id",
                        "Values": [
                            event["MaskedDBSnapshotIdentifier"],
                        ],
                    },
                ],
            )
            snapshot_status = response["DBSnapshots"][0]["Status"]
            event["MaskedSnapshotStatus"] = snapshot_status
            if snapshot_status == "failed":
                event["Error"] = (
                    f"Error creating snapshot of masked database: {snapshot_status}"
                )

        elif DBType == "Aurora":
            # Check the status of an Aurora cluster snapshot
            response = client.describe_db_cluster_snapshots(
                DBClusterIdentifier=DBIdentifier,
                Filters=[
                    {
                        "Name": "db-cluster-snapshot-id",
                        "Values": [
                            event["MaskedDBSnapshotIdentifier"],
                        ],
                    },
                ],
            )
            snapshot_status = response["DBClusterSnapshots"][0]["Status"]
            event["MaskedSnapshotStatus"] = snapshot_status
            if snapshot_status == "failed":
                event["Error"] = (
                    f"Error creating snapshot of masked Aurora database: {snapshot_status}"
                )

        else:
            raise ValueError(f"Invalid DBType: {DBType}. Expected 'RDS' or 'Aurora'.")

        print(json.dumps(event))
        return event

    except Exception as e:
        event["MaskedSnapshotStatus"] = "failed"
        event["Error"] = f"Error checking snapshot status of masked DB: {e}"
        print(f"Error checking snapshot of masked DB: {e}")
        return event
