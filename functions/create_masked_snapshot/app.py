import secrets
from datetime import datetime

import boto3


def lambda_handler(event, context):
    DBId = event["StageDB"]
    DBType = event["DBType"]  # Either "RDS" or "Aurora"
    client = boto3.client("rds")

    try:
        print("Checking masked DB snapshot")
        # Seconds + random suffix avoid snapshot-id collisions for runs that
        # start within the same minute.
        current_date = f"{datetime.now().strftime('%d%b%Y%H%M%S')}-{secrets.token_hex(3)}"

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

        # Check for snapshot status and update event. CheckMaskedSnapshotStatus
        # only branches on "available" / "failed"; report the real creation
        # status (typically "creating") so it polls until the snapshot is ready
        # rather than emitting a bogus "success" the Choice does not recognise.
        if event["MaskedDBSnapshotIdentifierStatus"] == "failed":
            event["Error"] = (
                f"Error creating snapshot of masked database: {event['MaskedDBSnapshotIdentifierStatus']}"
            )
            event["MaskedSnapshotStatus"] = "failed"
        else:
            event["MaskedSnapshotStatus"] = event["MaskedDBSnapshotIdentifierStatus"]

        return event

    except Exception as e:
        event["MaskedSnapshotStatus"] = "failed"
        event["Error"] = f"Error creating snapshot: {e}"
        print(f"Error creating snapshot: {e}")
        return event
