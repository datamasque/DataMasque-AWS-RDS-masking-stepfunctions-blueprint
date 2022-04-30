import os
import boto3
import json
import requests
import random
import datetime

base_url = os.environ['DATANASQUE_BASE_URL'] # change base url to the url of the DataMasque instance

datamasque_secret_arn = os.environ['DATAMASQUE_SECRET_ARN']


def login(base_url, username, password):
    """
    Login with username and password to get user_token
    which can be used for other API

    full_url = 'https://masque.local/api/auth/token/login/'
    method = 'POST'

    data parameters:
        'username': 'your_username',
        'password': 'your_password'

    status_code[200] == Success
    return json:
        {'id': 11,
         'key': '38e1befbdcbea57b838082e7d7612bee392d33e3',
         'client_ip': '172.18.0.1',
         'client_browser': 'Firefox',
         'client_os': 'Ubuntu',
         'client_device': 'Other',
         'date_time_created': '2022-02-13T21:36:23.468892Z',
         'date_time_expires': '2022-02-14T07:22:11.917111Z'}

    """
    api = 'api/auth/token/login/'
    data = {'username' : username, 'password': password}
    response = requests.post(base_url+api, data=data, verify=False)
    print(response)
    print(response.json())
    return response.json()


def connections(base_url, token, connection_id=None):
    """
    Read all database connections

    Can also use the same URL followed by the 'id' to only get info about that connection
    ex: 'https://masque.local/api/connections/6659eaef-f821-4e96-a659-cd3ff73f7a02'

    full_url = 'https://masque.local/api/connections/'
    method = 'GET'

    headers = {'Authorization': 'Token ' + 'your_user_token'}

    data parameters:
        None

   status_code[200] == Success

    return json:
         [
          {'name': 'new_postgres2',
           'user': 'library',
           'db_type': 'postgres',
           'database': 'library',
           'host': 'postgres-dev',
           'port': 5432, 'password':
           'Password123',
           'version': '1.0',
           'id': '6659eaef-f821-4e96-a659-cd3ff73f7a02',
           'oracle_wallet': None}
          ]
    """
    if connection_id:
        api = 'api/connections/{}/'.format(connection_id)
    else:
        api = 'api/connections/'
    response = requests.get(base_url+api, headers=token, verify=False)
    print(response)
    print(response.json())
    return response.json()


def rulesets(base_url, token, ruleset_id=None):
    """
    Read all rulesets

    Can also use the same URL followed by the 'id' to only get info about that connection
    ex: 'https://masque.local/api/rulesets/6659eaef-f821-4e96-a659-cd3ff73f7a02'

    full_url = 'https://masque.local/api/rulesets/'
    method = 'GET'

    headers = {'Authorization': 'Token ' + 'your_user_token'}

    data parameters:
        None

    status_code[200] == Success

    return json:
        [
         {
          'id': 'ruleset_id',
          'name': 'rulset_name',
          'config_yaml': 'ruleset_YAML',
          'is_valid': True
          },
         ]
    """
    if ruleset_id:
        api = 'api/rulesets/{}/'.format(ruleset_id)
    else:
        api = 'api/rulesets/'
    response = requests.get(base_url+api, headers=token, verify=False)
    print(response)
    print(response.json())
    return response.json()


def create_run(base_url, token, run_dict):
    """
    Create a run

    full_url = 'https://masque.local/api/runs/'
    method = 'POST'

    headers = {'Authorization': 'Token ' + 'your_user_token'}

    JSON parameters:
       {
        'name': 'run_name',
        'connection': 'connection_id',
        'ruleset': 'ruleset_id',
        'options': {
            'dry_run': False, 'buffer_size': 10000, 'continue_on_failure': False, 'run_secret': 'thisismynewrunsecret'
            }
       }

    status_code[201] == Success

    return json:
        {'id': xxx,
         'name': 'run_name',
         'status': 'queued',
         'connection': 'connection_id',
         'connection_name': 'connection_name',
         'ruleset': 'ruleset_id',
         'ruleset_name': 'ruleset_name',
         'created_time': '2022-02-15T02:01:33.012798Z',
         'start_time': None,
         'end_time': None,
         'options': {'dry_run': False, 'buffer_size': 10000, 'continue_on_failure': False, 'run_secret': ''},
         'has_sdd_report': False
         }
    """
    api = 'api/runs/'
    response = requests.post(base_url+api, json=run_dict, headers=token, verify=False)
    print(response)
    print(response.json())
    return response.json()


def runs(base_url, token, run_id=None):
    """
    Read all the run logs
    Can also use the same URL followed by the 'id' to only get info about that connection
    ex: 'https://masque.local/api/runs/6659eaef-f821-4e96-a659-cd3ff73f7a02/'

    full_url = 'https://masque.local/api/runs/'
    method = 'GET'

    headers = {'Authorization': 'Token ' + 'your_user_token'}

    data parameters:
       None

    status_code[200] == Success

    return json:
        {
         'id': 180,
         'name': 'test_run',
         'status': 'failed',
         'connection': 'some_connection_id',
         'connection_name': 'new_postgres',
         'ruleset': 'some_ruleset_id',
         'ruleset_name': 'test_ruleset',
         'created_time': '2022-02-24T22:52:58.233400Z',
         'start_time': '2022-02-24T22:53:00.291878Z',
         'end_time': '2022-02-24T22:53:01.501147Z',
         'options': {'dry_run': False, 'buffer_size': 10000, 'continue_on_failure': False, 'run_secret': None},
         'has_sdd_report': False
         }

    """
    if run_id:
        api = 'api/runs/{}/'.format(run_id)
    else:
        api = 'api/runs/'
    response = requests.get(base_url+api, headers=token, verify=False)
    print(response)
    print(response.json())
    return response.json()

def check_run(run_id):

    client = boto3.client('secretsmanager')

    response = client.get_secret_value(
        SecretId=datamasque_secret_arn,
    )

    datamasque_credential = json.loads(response['SecretString'])

    user_username = datamasque_credential['username']
    user_password = datamasque_credential['password']

    user_login_res = login(base_url, user_username, user_password)
    user_token = {'Authorization': 'Token ' + user_login_res['key']}

    return runs(base_url, user_token, run_id) # replace '180' with some run id

def lambda_handler(event, context):

    print(json.dumps(event))

    message_body = json.loads(event["Records"][0]["body"])
    taskToken = message_body["taskToken"]
    run_id = message_body["input"]["run_id"]
    db_instance_identifier = message_body["input"]["DBInstanceIdentifier"]


    client_stepfunctions = boto3.client('stepfunctions')
    client_sqs = boto3.client('sqs')

    #   user_login_res = login(base_url, user_username, user_password)
    #   token = {'Authorization': 'Token ' + user_login_res['key']}

    response = check_run(run_id)
    print(response)

    status = response['status']
    print(status)

    if status == 'finished':
        print("DATAMASQUE job status=finished")
        timestamp = datetime.datetime.now()
        client_stepfunctions.send_task_success(
            taskToken=taskToken,
            output=json.dumps(
                {
                    "DBInstanceIdentifier": db_instance_identifier,
                    "Timestamp": timestamp.strftime('%Y-%m-%d-%H-%M')
                }
            )
        )
    else:
        if status == 'failed':
            print("DATAMASQUE job status=failed")
            client_stepfunctions.send_task_failure(
                taskToken=taskToken,
                error='failed',
                cause='failed'
            )
        else:
            if status == 'cancelled':
                print("DATAMASQUE job status=cancelled")
                client_stepfunctions.send_task_failure(
                    taskToken=taskToken,
                    error='failed',
                    cause='failed'
                )
            else:
                print("Sending message SQS...")
                queue_url = os.environ['SQS_URL']
                response = client_sqs.send_message(QueueUrl=queue_url, DelaySeconds=120, MessageBody=json.dumps(message_body))
                print(response)