import boto3


def lambda_handler(event, context):

    client = boto3.client("rds")

    try:

        restore_response = client.restore_db_instance_from_db_snapshot(
            DBSnapshotIdentifier=event["parameters"]["DBSnapshotIdentifier"],
            DBInstanceIdentifier=event["parameters"]["DBInstanceIdentifier"],
            DBInstanceClass=event["parameters"]["DBInstanceClass"],
            AvailabilityZone=event["parameters"]["AvailabilityZone"],
            DBSubnetGroupName=event["parameters"]["DBSubnetGroupName"],
            OptionGroupName=event["parameters"]["OptionGroupName"],
            DBParameterGroupName=event["parameters"]["DBParameterGroupName"],
            VpcSecurityGroupIds=event["parameters"]["VpcSecurityGroupIds"],
            DeletionProtection=False,
        )
        response = {}
        event["status"] = "success"
        event["DBInstance"] = event["parameters"]["DBInstanceIdentifier"]

        return event

    except Exception as e:
        print(f"Error restoring snapshot: {e}")
        return {
            "status": "failure",
            "Error": f"Error restoring snapshot: {e}",
            "DBInstance": event["parameters"]["DBInstanceIdentifier"],
        }
