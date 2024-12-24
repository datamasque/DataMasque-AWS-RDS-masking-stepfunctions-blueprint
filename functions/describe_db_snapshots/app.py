import json
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
        DBType = None
        try:
            cluster_response = client.describe_db_clusters(
                DBClusterIdentifier=DBInstanceIdentifier
            )
            if cluster_response["DBClusters"]:
                print(f"{DBInstanceIdentifier} is an Aurora cluster.")
                DBType = "Aurora"
        except client.exceptions.DBClusterNotFoundFault:
            try:
                instance_response = client.describe_db_instances(
                    DBInstanceIdentifier=DBInstanceIdentifier
                )
                if instance_response["DBInstances"]:
                    db_instance = instance_response["DBInstances"][0]
                    engine = db_instance["Engine"]
                    if engine.startswith("aurora"):
                        print(
                            f"{DBInstanceIdentifier} is an Aurora instance (part of a cluster)."
                        )
                        DBType = "Aurora"
                    else:
                        print(f"{DBInstanceIdentifier} is an RDS instance.")
                        DBType = "RDS"
            except client.exceptions.DBInstanceNotFoundFault:
                print(
                    f"{DBInstanceIdentifier} is neither an Aurora cluster nor an RDS instance."
                )
                raise Exception("Unknown DBInstanceIdentifier")

        event["DBType"] = DBType

        if DBType == "Aurora":
            response = client.describe_db_cluster_snapshots(
                DBClusterIdentifier=DBInstanceIdentifier,
                IncludeShared=True,
            )

            if not response["DBClusterSnapshots"]:
                print(
                    "No existing Aurora cluster snapshots found. Generating a new snapshot."
                )
                current_date = datetime.now().strftime("%d%b%Y%H%M")
                snapshot_identifier = (
                    f"{DBInstanceIdentifier}-datamasque-{current_date}"
                )
                response = client.create_db_cluster_snapshot(
                    DBClusterSnapshotIdentifier=snapshot_identifier,
                    DBClusterIdentifier=DBInstanceIdentifier,
                )
                event["DBSnapshotIdentifier"] = response["DBClusterSnapshot"][
                    "DBClusterSnapshotIdentifier"
                ]
                event["SourceDBSnapshotStatus"] = response["DBClusterSnapshot"][
                    "Status"
                ]
            else:
                snapshots = response["DBClusterSnapshots"]
                sorted_list = sorted(
                    snapshots, key=itemgetter("SnapshotCreateTime"), reverse=True
                )
                event["DBSnapshotIdentifier"] = sorted_list[0][
                    "DBClusterSnapshotIdentifier"
                ]
                event["SourceDBSnapshotStatus"] = sorted_list[0]["Status"]
                if sorted_list[0]["Status"] == "failed":
                    event["Error"] = (
                        f"Error capturing snapshot: {sorted_list[0]['DBClusterSnapshotIdentifier']}"
                    )
                    event["SourceDBSnapshotStatus"] = "failed"

        elif DBType == "RDS":
            # Handle RDS Instance Snapshots
            response = client.describe_db_snapshots(
                DBInstanceIdentifier=DBInstanceIdentifier,
                IncludePublic=False,
                IncludeShared=True,
            )

            if not response["DBSnapshots"]:
                print("No existing RDS snapshots found. Generating a new snapshot.")
                db_instance_resp = client.describe_db_instances(
                    DBInstanceIdentifier=DBInstanceIdentifier,
                )
                current_date = datetime.now().strftime("%d%b%Y%H%M")
                snapshot_identifier = f"{db_instance_resp['DBInstances'][0]['DBInstanceIdentifier']}-datamasque-{current_date}"
                response = client.create_db_snapshot(
                    DBSnapshotIdentifier=snapshot_identifier,
                    DBInstanceIdentifier=db_instance_resp["DBInstances"][0][
                        "DBInstanceIdentifier"
                    ],
                )
                event["DBSnapshotIdentifier"] = response["DBSnapshot"][
                    "DBSnapshotIdentifier"
                ]
                event["SourceDBSnapshotStatus"] = response["DBSnapshot"]["Status"]
            else:
                snapshots = response["DBSnapshots"]
                sorted_list = sorted(
                    snapshots, key=itemgetter("SnapshotCreateTime"), reverse=True
                )
                event["DBSnapshotIdentifier"] = sorted_list[0]["DBSnapshotIdentifier"]
                event["SourceDBSnapshotStatus"] = sorted_list[0]["Status"]
                if sorted_list[0]["Status"] == "failed":
                    event["Error"] = (
                        f"Error capturing snapshot: {sorted_list[0]['DBSnapshotIdentifier']}"
                    )
                    event["SourceDBSnapshotStatus"] = "failed"

        print(json.dumps(event))
        return event

    except Exception as e:
        event["SourceDBSnapshotStatus"] = "failed"
        event["Error"] = f"Error capturing snapshot: {e}"
        print(f"Error capturing snapshot: {e}")
        print(json.dumps(event))
        return event
