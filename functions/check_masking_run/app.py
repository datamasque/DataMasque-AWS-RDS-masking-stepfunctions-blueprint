import json
import logging
import os

import boto3

import requests

logger = logging.getLogger()
logger.setLevel(logging.INFO)

base_url = os.environ[
    "DATAMASQUE_BASE_URL"
]  # change base url to the url of the DataMasque instance

datamasque_secret_arn = os.environ["DATAMASQUE_SECRET_ARN"]

def parse_verify_tls(value: str | None) -> bool:
    """Parse the DATAMASQUE_VERIFY_TLS env value into a bool (default secure).

    TLS verification defaults to ON. Only the explicit strings false/0/no
    (case-insensitive) disable it, for documented self-signed / private-CA
    DataMasque instances on a trusted path.
    """
    return str(value).strip().lower() not in ("false", "0", "no")


VERIFY_TLS = parse_verify_tls(os.environ.get("DATAMASQUE_VERIFY_TLS", "true"))


def _redacted_event(event: dict) -> dict:
    """Copy of the event with sensitive run-secret fields masked for logging.

    The event is carried forward between states, so a RunSecret / AwsSecretArn
    supplied in the execution input reaches this Lambda too; never log it raw.
    """
    redacted = dict(event)
    for key in ("RunSecret", "AwsSecretArn"):
        if key in redacted:
            redacted[key] = "***redacted***"
    return redacted


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
    response = requests.post(base_url + api, json=data, headers=headers, verify=VERIFY_TLS)

    # Do not log the response body: it contains the auth token.
    logger.info("Login response status: %s", response.status_code)
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

    response = requests.get(base_url + api, headers=token, verify=VERIFY_TLS)
    # run objects may carry the run_secret in options; log status only.
    logger.info("Get run status: %s", response.status_code)
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
    logger.info("Deleting temporary connection - %s", conn_id)
    response = requests.delete(base_url + api, headers=token, verify=VERIFY_TLS)
    logger.info("Delete connection status: %s", response.status_code)


def lambda_handler(event, context):

    logger.info("Event: %s", json.dumps(_redacted_event(event)))

    client = boto3.client("secretsmanager")

    try:

        response = client.get_secret_value(
            SecretId=datamasque_secret_arn,
        )

        datamasque_credential = json.loads(response["SecretString"])

        user_username = datamasque_credential["username"]
        user_password = datamasque_credential["password"]
        run_id = event["MaskRunId"]
        DBInstanceIdentifier = event["StageDB"]
        DBSecretIdentifier = event["DBSecretIdentifier"]
        user_login_res = login(base_url, user_username, user_password)

        token = {"Authorization": "Token " + user_login_res["key"]}
        run_response = runs(base_url, token, run_id)
        event["MaskRunStatus"] = run_response["status"]
        if "fail" in run_response["status"]:
            event["Error"] = f"MaskRunId {event['MaskRunId']} has failed"
        if event["MaskRunStatus"] == "finished":
            conn_id = run_response["connection"]
            delete_connection(base_url, token, conn_id)
        logger.info("Result event: %s", json.dumps(_redacted_event(event)))
        return event

    except Exception as e:
        logger.error("Error checking masking run status: %s", e)
        event["MaskRunStatus"] = "failure"
        event["Error"] = f"DataMasque run failed status: {e}"
        logger.info("Result event: %s", json.dumps(_redacted_event(event)))
        return event
