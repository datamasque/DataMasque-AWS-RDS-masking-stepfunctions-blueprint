import json

import boto3


def lambda_handler(event, context):

    client = boto3.client("rds")
    print(json.dumps(event))

    # Check if the previous step failed
    if event.get("status") == "failure":
        return event

    try:
        db_identifier = event["StageDB"]
        db_type = event["DBType"]  # Either "RDS" or "Aurora"
        print(f"DB Identifier: {db_identifier}, DB Type: {db_type}")

        if db_type == "RDS":
            db_response = client.describe_db_instances(
                DBInstanceIdentifier=db_identifier,
            )
            db_instance = db_response["DBInstances"][0]
            db_status = db_instance["DBInstanceStatus"].lower()

            response = {
                "status": db_status,
                "DBInstance": db_identifier,
            }
            event["status"] = db_status

        elif db_type == "Aurora":
            # Check status of the Aurora cluster
            db_response = client.describe_db_clusters(
                DBClusterIdentifier=db_identifier,
            )
            db_cluster = db_response["DBClusters"][0]
            if db_cluster["Status"].lower() == "available":
                if "StgDbInstanceStatus" not in event:
                    print("Creating DB instance in the restored Aurora cluster...")
                    instance_params = {
                        "DBInstanceIdentifier": f'{event["parameters"]["DBInstanceIdentifier"]}-1',
                        "DBInstanceClass": event["parameters"]["DBInstanceClass"],
                        "Engine": event["parameters"]["Engine"],
                        "DBClusterIdentifier": event["parameters"][
                            "DBInstanceIdentifier"
                        ],
                        "AvailabilityZone": event["PreferredAZ"],
                        "DBSubnetGroupName": event["parameters"]["DBSubnetGroupName"],
                    }
                    if event["parameters"].get("DBParameterGroupName"):
                        instance_params["DBParameterGroupName"] = event["parameters"][
                            "DBParameterGroupName"
                        ]
                    client.create_db_instance(**instance_params)
                    event["status"] = "creating"
                    event["StgDbInstanceStatus"] = "creating"
                    event["StgDbInstanceId"] = (
                        f'{event["parameters"]["DBInstanceIdentifier"]}-1'
                    )
                else:
                    db_response = client.describe_db_instances(
                        DBInstanceIdentifier=f'{event["parameters"]["DBInstanceIdentifier"]}-1',
                    )
                    db_instance = db_response["DBInstances"][0]
                    db_status = db_instance["DBInstanceStatus"].lower()

                    response = {
                        "status": db_status,
                        "DBInstance": db_identifier,
                    }
                    event["status"] = db_status
                    event["StgDbInstanceStatus"] = db_status
        else:
            raise ValueError(f"Invalid DBType: {db_type}. Expected 'RDS' or 'Aurora'.")
        print(json.dumps(event))
        return event

    except Exception as e:
        print(f"Error checking status of {event['StageDB'] }: {e}")
        event["status"] = "failure"
        event["Error"] = f"Error checking DB status: {e}"
        print(json.dumps(event))
        return event
