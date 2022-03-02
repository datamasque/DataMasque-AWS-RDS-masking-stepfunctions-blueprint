import boto3

def lambda_handler(event, context):
  
  client = boto3.client('rds')
  
  response = client.restore_db_instance_from_db_snapshot(
      DBSnapshotIdentifier= event["DBSnapshotIdentifier"],
      DBInstanceIdentifier= event["DBInstanceIdentifier"],
      DBInstanceClass= event["DBInstanceClass"],
      AvailabilityZone= event["AvailabilityZone"],
      DBSubnetGroupName= event["DBSubnetGroupName"],
      OptionGroupName= event["OptionGroupName"],
      DBParameterGroupName= event["DBParameterGroupName"],
      VpcSecurityGroupIds= event["VpcSecurityGroupIds"],
      DeletionProtection= False
      )
    
  return response