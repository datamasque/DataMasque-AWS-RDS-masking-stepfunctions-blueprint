import os
import boto3
from operator import itemgetter

def lambda_handler(event, context):

  DBInstanceIdentifier = event["DBInstanceIdentifier"]

  client = boto3.client('rds')

  response = client.describe_db_snapshots(
    DBInstanceIdentifier=DBInstanceIdentifier,
    IncludePublic=False,
    IncludeShared=True,
  )
  
  list = response["DBSnapshots"]
  
  sorted_list = sorted(list, key=itemgetter('SnapshotCreateTime'), reverse=True)

  latest_snapshot_id = {
    "DBSnapshotIdentifier": sorted_list[0]["DBSnapshotIdentifier"]
  }

  return latest_snapshot_id