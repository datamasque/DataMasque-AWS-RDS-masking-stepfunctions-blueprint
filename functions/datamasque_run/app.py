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
        api = "api/connections/{}/".format(connection_id)
    else:
        api = "api/connections/"
    response = requests.get(base_url + api, headers=token, verify=False)
    print(response)
    print(response.json())
    return response.json()


def create_connection(base_url: str, token: str, secret: dict, dm_ruleset_id: str):
    """
    Creates a database connection.


    full_url = 'https://masque.local/api/connections/'
    method = 'POST'

    headers = {'Authorization': 'Token ' + 'your_user_token'}

    JSON parameters:
    {
        "version": "1.0",
        "name": "<connection_name>",
        "user": "<database_user>",
        "db_type": "<database_type>",
        "database": "<database_name>",
        "host": "<database_host>",
        "port": <database_port>,
        "password": "<database_password>",
        "schema": "<database_schema>",
        "service_name": "<oracle_service_name>",
        "connection_fileset": "<connection_fileset>",
        "mask_type": "database"
    }

        status_code[201] == A JSON serialised Connection object.

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
    # if connection_id:
    #     api = "api/connections/{}/".format(connection_id)
    # else:
    #     api = "api/connections/"
    # response = requests.get(base_url + api, headers=token, verify=False)
    # print(response)
    # print(response.json())
    # return response.json()
    print(dict)
    keys_to_check = {
        "username",
        "password",
        "engine",
        "host",
        "port",
        "dbname",
        "schema",
    }
    if keys_to_check.issubset(secret):
        valid_engine_type = ["postgres", "mysql", "oracle", "mariadb", "mssql"]
        if secret["engine"] not in valid_engine_type:
            print(
                f"Invalid value for engine parameter in secret, valid values are: {valid_engine_type}"
            )
            return {
                "status": "failure",
                "error": f"Invalid value for engine parameter in secret, valid values are: {valid_engine_type}",
            }
        print("All required parameters exist in the secret!")
        api = "api/connections/"
        staging_db_id = secret["host"].split(".")
        staging_db_id[0] = f"{staging_db_id[0]}-datamasque"
        staging_db_endpoint = ".".join(staging_db_id)
        conn_dict = {
            "version": "1.0",
            "name": f"database_{secret['dbname']}_datamasque_temp",
            "user": f"{secret['username']}",
            "db_type": f"{secret['engine']}",
            "database": f"{secret['dbname']}",
            "host": staging_db_endpoint,
            "port": int(secret["port"]),
            "dbpassword": f"{secret['password']}",
            "schema": f"{secret['schema']}",
            "mask_type": "database",
        }
        # add service name parameter if engine is oracle and service_name is present
        if "service_name" in secret and secret.get("engine") == "oracle":
            conn_dict["service_name"] = secret["service_name"]
        ## Check if "connection_fileset" exists and if "engine" is either "mysql" or "mariadb"
        if "connection_fileset" in secret and secret.get("engine") in [
            "mysql",
            "mariadb",
        ]:
            conn_dict["connection_fileset"] = secret["connection_fileset"]
        # test connection before creating it.

        test_response = requests.post(
            base_url + api + "test/", json=conn_dict, headers=token, verify=False
        )
        print(test_response)
        if test_response.status_code in [200, 201]:
            print("Db connection test successfull, creating DataMasque connection.")
            get_conn_response = requests.get(
                base_url + api,
                json={
                    "version": "1.0",
                    "name": f"database_{secret['dbname']}_datamasque_temp",
                },
                headers=token,
                verify=False,
            )
            found = False
            for conn in get_conn_response.json():
                if conn.get("name") == f"database_{secret['dbname']}_datamasque_temp":
                    found = True
                    print(f"DataMasque Connecton exists: {conn}")
                    break
            if found:
                print(f"Deleting existing temporary connection: {conn['name']}")
                delete_response = requests.delete(
                    base_url + api + f"{conn['id']}/",
                    headers=token,
                    verify=False,
                )
                print(delete_response)
            conn_response = requests.post(
                base_url + api, json=conn_dict, headers=token, verify=False
            )

            print(conn_response)
            print(conn_response.json())
            if conn_response.status_code == 201:

                create_run_response = create_run(
                    base_url, token, conn_response.json()["id"], dm_ruleset_id
                )
                print(create_run_response)
                return create_run_response
            else:
                print(
                    f"Unexpected status code: {conn_response.status_code} {conn_response.json()}"
                )
                return {
                    "status": "failure",
                    "error": f"Unexpected status code: {conn_response.status_code} {conn_response.json()}",
                }
        else:
            print(
                f"Connection test failed, please verify following connection parameters provided in secrets manager {json.dump(conn_dict)} ."
            )
            return {
                "status": "failure",
                "error": f"Connection test failed, please verify the connection parameters provided in secrets manager.",
            }

    else:
        print(
            f"Missing required parameters in secrets manager, please verify \
              if the secret contains {keys_to_check} parameters in it."
        )
        return {
            "status": "failure",
            "error": f"Missing required parameters in secrets manager, please verify \
              if the secret contains {keys_to_check} parameters in it.",
        }


def get_secret(secret_name: str) -> Optional[Dict]:
    """
    Retrieves a secret from AWS Secrets Manager.

    Parameters:
        secret_name (str): The name or ARN of the secret to retrieve.
        region_name (str): The AWS region where the secret is stored (e.g., 'us-west-2').

    Returns:
        Optional[, Dict]:
            - If the secret is a JSON string, returns the secret as a dictionary.
            - Returns None if there's an error or the secret cannot be retrieved.
    """

    client = boto3.client("secretsmanager")

    try:
        response = client.get_secret_value(SecretId=secret_name)

        if "SecretString" in response:
            secret = response["SecretString"]
            return json.loads(secret)
        else:
            return None

    except client.exceptions.ResourceNotFoundException:
        print(f"Error: The requested secret '{secret_name}' was not found")
    except client.exceptions.InvalidRequestException as e:
        print(f"Error: The request was invalid due to: {e}")
    except client.exceptions.InvalidParameterException as e:
        print(f"Error: The request had invalid params: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

    return None


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
        api = "api/rulesets/{}/".format(ruleset_id)
    else:
        api = "api/rulesets/"
    response = requests.get(base_url + api, headers=token, verify=False)
    print(response)
    print(response.json())
    return response.json()


def create_run(base_url, token, conn_id, dm_ruleset_id):
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
    run_dict = {
        "name": "datamasque_blueprint",
        "connection": conn_id,
        "ruleset": dm_ruleset_id,
        "options": {
            "dry_run": False,
            "buffer_size": 10000,
            "continue_on_failure": False,
            "run_secret": "thisismynewrunsecret",
        },
    }
    api = "api/runs/"
    response = requests.post(base_url + api, json=run_dict, headers=token, verify=False)
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
        dm_ruleset_id = event["DataMasqueRulesetId"]
        DBInstanceIdentifier = event["StageDB"]
        DBSecretIdentifier = event["DBSecretIdentifier"]
        secret_response = get_secret(DBSecretIdentifier)
        if secret_response:
            user_login_res = login(base_url, user_username, user_password)

            token = {"Authorization": "Token " + user_login_res["key"]}
            create_connection_response = create_connection(
                base_url, token, secret_response, dm_ruleset_id
            )
            if create_connection_response["status"] == "failure":
                event["MaskRunStatus"] = create_connection_response["status"]
                event["Error"] = create_connection_response["error"]
                return event
            else:
                event["MaskRunStatus"] = create_connection_response["status"]
                event["MaskRunId"] = create_connection_response["id"]
        print(json.dumps(event))
        return event

    except Exception as e:
        print(f"Error executing datamasque run: {e}")
        event["MaskRunStatus"] = "failure"
        event["Error"] = f"Error executing datamasque run: {e}"
        print(json.dumps(event))
        return event

        # if response:
        #     run_id = response["id"]
        #     conn_id = create_connection_response["id"]

        #     return {
        #         "run_id": run_id,
        #         "DBInstanceIdentifier": DBInstanceIdentifier,
        #         "conn_id": conn_id,
        #     }
