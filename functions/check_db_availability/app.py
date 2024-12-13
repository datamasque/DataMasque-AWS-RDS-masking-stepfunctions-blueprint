import boto3


def lambda_handler(event, context):

    client = boto3.client("rds")
    print(event)
    if event["status"] == "failure":
        return event
    else:
        try:
            db_instance_identifier = event["DBInstance"]
            print(f"db_instance_identifier: {db_instance_identifier}")
            db_response = client.describe_db_instances(
                DBInstanceIdentifier=db_instance_identifier,
            )
            response = {
                "status": db_response["DBInstances"][0]["DBInstanceStatus"].lower(),
                "DBInstance": db_instance_identifier,
            }
            event["status"] = db_response["DBInstances"][0]["DBInstanceStatus"].lower()
            return event

        except Exception as e:
            print(f"Error checking rds status: {e}")
            event["status"] = "failure"
            event["Error"] = f"Error checking rds status: {e}"
            return event
