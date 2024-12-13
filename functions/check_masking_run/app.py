import json
import os
from typing import Dict, Optional, Union

import boto3

import requests

base_url = os.environ[
    "DATANASQUE_BASE_URL"
]  # change base url to the url of the DataMasque instance

datamasque_secret_arn = os.environ["DATAMASQUE_SECRET_ARN"]


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
    api = "api/auth/token/login/"
    data = {"username": username, "password": password}
    headers = {"Content-Type": "application/json"}
    response = requests.post(base_url + api, json=data, headers=headers, verify=False)
    # url = "https://demo01.demo.datamasque.com/api/auth/token/login/"

    print(response)
    print(response.json())
    return response.json()


def runs(base_url, token, run_id):
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

    api = "api/runs/{}/".format(run_id)

    response = requests.get(base_url + api, headers=token, verify=False)
    print(response)
    print(response.json())
    return response.json()


def delete_connection(base_url, token, conn_id):
    """
    Deletes the given connection.

    full_url = 'https://masque.local//api/connections/{id}/'
    method = 'DELETE'

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

    api = f"/api/connections/{conn_id}/"

    response = requests.get(base_url + api, headers=token, verify=False)
    print(response)
    print(response.json())
    return response.json()


def lambda_handler(event, context):

    print(json.dumps(event))

    client = boto3.client("secretsmanager")

    try:

        response = client.get_secret_value(
            SecretId=datamasque_secret_arn,
        )

        datamasque_credential = json.loads(response["SecretString"])

        user_username = datamasque_credential["username"]
        user_password = datamasque_credential["password"]
        run_id = event["MaskRunId"]
        DBInstanceIdentifier = event["DBInstance"]
        DBSecretIdentifier = event["DBSecretIdentifier"]
        user_login_res = login(base_url, user_username, user_password)

        token = {"Authorization": "Token " + user_login_res["key"]}
        run_response = runs(base_url, token, run_id)
        event["MaskRunStatus"] = run_response["status"]
        if "fail" in run_response["status"]:
            event["Error"] = f"MaskRunId {event['MaskRunId']} has failed"
        if event["MaskRunStatus"] == "complete":
            conn_id = run_response["connection"]
            delete_connection(base_url, token, conn_id)
        return event

    except Exception as e:
        print(f"Error checking rds status: {e}")
        event["MaskRunStatus"] = "failure"
        event["Error"] = f"DataMasque run failed status: {e}"
        return event
