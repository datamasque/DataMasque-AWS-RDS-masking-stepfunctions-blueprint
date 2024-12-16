from datetime import datetime

import boto3


def handler(event):
    DBId = event["StageDB"]
    DBType = event["DBType"]  # Either "RDS" or "Aurora"
    client = boto3.client("rds")

    try:
        print("Checking masked DB snapshot")
        current_date = datetime.now().strftime("%d%b%Y%H%M")

        if DBType == "RDS":
            # Create a snapshot for an RDS instance
            response = client.create_db_snapshot(
                DBSnapshotIdentifier=f"{DBId}-masked-{current_date}",
                DBInstanceIdentifier=DBId,
            )
            event["MaskedDBSnapshotIdentifier"] = response["DBSnapshot"][
                "DBSnapshotIdentifier"
            ]
            event["MaskedDBSnapshotIdentifierStatus"] = response["DBSnapshot"]["Status"]

        elif DBType == "Aurora":
            # Create a snapshot for an Aurora cluster
            response = client.create_db_cluster_snapshot(
                DBClusterSnapshotIdentifier=f"{DBId}-masked-{current_date}",
                DBClusterIdentifier=DBId,
            )
            event["MaskedDBSnapshotIdentifier"] = response["DBClusterSnapshot"][
                "DBClusterSnapshotIdentifier"
            ]
            event["MaskedDBSnapshotIdentifierStatus"] = response["DBClusterSnapshot"][
                "Status"
            ]

        else:
            raise ValueError(f"Invalid DBType: {DBType}. Expected 'RDS' or 'Aurora'.")

        # Check for snapshot status and update event
        if event["MaskedDBSnapshotIdentifierStatus"] == "failed":
            event["Error"] = (
                f"Error creating snapshot of masked database: {event['MaskedDBSnapshotIdentifierStatus']}"
            )
            event["MaskedSnapshotStatus"] = "failure"
        else:
            event["MaskedSnapshotStatus"] = "success"

        return event

    except Exception as e:
        event["MaskedSnapshotStatus"] = "failure"
        event["Error"] = f"Error creating snapshot: {e}"
        print(f"Error creating snapshot: {e}")
        return event
