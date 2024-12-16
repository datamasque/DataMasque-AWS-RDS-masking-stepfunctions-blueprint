import boto3


def lambda_handler(event, context):

import boto3


def handler(event):
    client = boto3.client("rds")
    print(event)

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
            db_status = db_cluster["Status"].lower()

            response = {
                "status": db_status,
                "DBCluster": db_identifier,
            }
            event["status"] = db_status

        else:
            raise ValueError(f"Invalid DBType: {db_type}. Expected 'RDS' or 'Aurora'.")

        print(f"DB Status: {response}")
        return event

    except Exception as e:
        print(f"Error checking status of {event["StageDB"] }: {e}")
        event["status"] = "failure"
        event["Error"] = f"Error checking DB status: {e}"
        return event