import os
import boto3

def lambda_handler(event, context):
  
  DBSnapshotIdentifier = event["DBSnapshotIdentifier"]
  
  client = boto3.client('rds')

  response = client.describe_db_instances(
    DBInstanceIdentifier='dtq-postgres-datamasque-2a-04-rds',
  )
  
  instance = response["DBInstances"][0]
  
  security_groups = instance["VpcSecurityGroups"]
 
  VpcSecurityGroupIds = [d['VpcSecurityGroupId'] for d in security_groups]
  
  parameters = {
    "DBSnapshotIdentifier": DBSnapshotIdentifier,
    "DBInstanceIdentifier": instance["DBInstanceIdentifier"] + "-datamasque",
    "DBInstanceClass": instance["DBInstanceClass"],
    "AvailabilityZone": instance["AvailabilityZone"],
    "DBSubnetGroupName": instance["DBSubnetGroup"]["DBSubnetGroupName"],
    "OptionGroupName": instance["OptionGroupMemberships"][0]["OptionGroupName"],
    "DBParameterGroupName": instance["DBParameterGroups"][0]["DBParameterGroupName"],
    "VpcSecurityGroupIds": VpcSecurityGroupIds,
    "DeletionProtection": False
  }

  return parameters