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
        print("Generating masked DB snapshot")
        response = client.describe_db_snapshots(
            DBInstanceIdentifier=DBInstanceIdentifier,
            Filters=[
                {
                    'Name': 'db-snapshot-id',
                    'Values': [
                       event['MaskedDBSnapshotIdentifier'],
                    ]
                },
            ],
        )
        event["MaskedDBSnapshotIdentifierStatus"] = response["DBSnapshots"][0]["Status"]
        if response["DBSnapshots"][0]["Status"] == "failed":
            event["Error"] = f"Error creating snapshot of masked database: {response["DBSnapshots"][0]["Status"]}"
            event["MaskedSnapshotStatus"] = "failure"
        return event
    except Exception as e:
        event["MaskedSnapshotStatus"] = "failure"
        event["Error"] = f"Error checking snapshot status of masked DB: {e}"
        print(f"Error creating snapshot of masked DB: {e}")
        return event
