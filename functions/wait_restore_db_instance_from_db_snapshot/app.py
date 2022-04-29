import os
import boto3
import json
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):

    logger.info(event)
    logger.info(context)

    message_body = json.loads(event["Records"][0]["body"])
    taskToken = message_body["taskToken"]
    db_instance_identifier = message_body["input"]["DBInstanceIdentifier"]

    client_rds = boto3.client('rds')
    client_stepfunctions = boto3.client('stepfunctions')
    client_sqs = boto3.client('sqs')

    response = client_rds.describe_db_instances(
        DBInstanceIdentifier=db_instance_identifier,
    )

    instance = response["DBInstances"][0]

    status = instance["DBInstanceStatus"]
    logger.info("DBInstanceStatus is %s", status)

    if status == 'available':
        logger.info("calling stepfunction call back...")
        client_stepfunctions.send_task_success(
            taskToken=taskToken,
            output=json.dumps(
                {
                    "DBInstanceIdentifier": db_instance_identifier
                }
            )
        )
    else:
        logger.info("sending message back to the queue...")
        queue_url = os.environ['SQS_URL']
        response = client_sqs.send_message(QueueUrl=queue_url, DelaySeconds=120, MessageBody=json.dumps(message_body))
        logger.info(response)
