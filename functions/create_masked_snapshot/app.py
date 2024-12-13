import os
from datetime import datetime
from operator import itemgetter

import boto3

"""
Creates a snapshot of the masked RDS instance.


    
"""


def lambda_handler(event, context):

    DBInstanceIdentifier = event["DBInstance"]

    client = boto3.client("rds")

    try:
        print("Checking masked DB snapshot")
        current_date = datetime.now().strftime("%d%b%Y%H%M")
        response = client.create_db_snapshot(
            DBSnapshotIdentifier=f"{DBInstanceIdentifier}-masked-{current_date}",
            DBInstanceIdentifier=DBInstanceIdentifier,
        )
        event["MaskedDBSnapshotIdentifier"] = response["DBSnapshot"][
            "DBSnapshotIdentifier"
        ]
        event["MaskedDBSnapshotIdentifierStatus"] = response["DBSnapshot"]["Status"]
        if response["DBSnapshot"]["Status"] == "failed":
            event["Error"] = (
                f"Error creating snapshot of masked database: {response['DBSnapshot']['Status']}"
            )
            event["MaskedSnapshotStatus"] = "failure"
        event["MaskedSnapshotStatus"] = "success"
        return event
    except Exception as e:
        event["MaskedSnapshotStatus"] = "failure"
        event["Error"] = f"Error creating snapshot: {e}"
        print(f"Error creating snapshot: {e}")
        return event
