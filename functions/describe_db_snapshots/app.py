import os
from datetime import datetime
from operator import itemgetter

import boto3

"""
Creates a snapshot of the specified RDS DB instance.


Returns:
	dict: Response from AWS RDS create_db_snapshot API call.
    
"""


def lambda_handler(event, context):

    DBInstanceIdentifier = event["DBInstanceIdentifier"]

    client = boto3.client("rds")

    try:
        response = client.describe_db_snapshots(
            DBInstanceIdentifier=DBInstanceIdentifier,
            IncludePublic=False,
            IncludeShared=True,
        )

        if not response["DBSnapshots"]:
            print("Generating new DB snapshot")
            db_instance_resp = client.describe_db_instances(
                DBInstanceIdentifier=DBInstanceIdentifier,
            )
            current_date = datetime.now().strftime("%d%b%Y%H%M")
            response = client.create_db_snapshot(
                DBSnapshotIdentifier=f"{db_instance_resp['DBInstances']['DBInstanceIdentifier']}-datamasque-{current_date}",
                DBInstanceIdentifier=db_instance_resp["DBInstances"][
                    "DBInstanceIdentifier"
                ],
            )
            event["DBSnapshotIdentifier"] = response["DBSnapshot"][
                "DBSnapshotIdentifier"
            ]
            event["DBSnapshotIdentifierStatus"] = response["DBSnapshot"]["Status"]
        else:
            list = response["DBSnapshots"]
            sorted_list = sorted(
                list, key=itemgetter("SnapshotCreateTime"), reverse=True
            )
        event["DBSnapshotIdentifier"] = sorted_list[0]["DBSnapshotIdentifier"]
        event["DBSnapshotIdentifierStatus"] = sorted_list[0]["Status"]
        if sorted_list[0]["Status"] == "failed":
            event["Error"] = (
                f"Error capturing snapshot: {sorted_list[0]['DBSnapshotIdentifier']}"
            )

            event["SourceDBSnapshotStatus"] = "failure"
        event["SourceDBSnapshotStatus"] = "failure"
        return event
    except Exception as e:
        event["SourceDBSnapshotStatus"] = "failure"
        event["Error"] = f"Error capturing snapshot: {e}"
        print(f"Error capturing snapshot: {e}")
        return event
