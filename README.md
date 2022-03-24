# AWS SAM template datamasque-blueprint

## Introduction

## Network

The assumption is that basic connectivity has been established as follows:

- The AWS Lambdas are provisioned inside a VPC in a **private subnet**. It's recommended to provide at least two **SubnetIDs** for availability reasons.
- The Origin RDS DB instance **must** allow inbound connections from the DataMasque EC2 instance. The configuration will be replicated when creating the staging RDS.
- The DataMasque EC2 instance **must** allow inbound connections from the **DatamasqueAPIRun** Lambda.

The diagram below describes the connections, API calls and resources placement within the VPC.

![Network requirements](/network.png "Network requirements")

## Deployment

### Requirements

- AWS CLI configured with appropriate credentials.
- AWS SAM CLI
- DATAMASQUE `connection id` and `ruleset`. 

The RDS instance created will follow the same RDS endpoint name schema as the target database with a `datamasque` prefix:

|RDS database|Endpoint|
|---|---|
|Origin RDS instance|``prod-postgres-04``.cxyxaxayxya.ap-southeast-2.rds.amazonaws.com|
|Staging RDS instance|``prod-postgres-04-datamasque``.cxyxaxayxya.ap-southeast-2.rds.amazonaws.com|

The RDS username, password and connection port will be the same as the target RDS instance.

The connection ID required during the template provisioning, refers to the **Staging RDS instance** and **must** exist before the StepFunction can run.

### Step-by-step

Before deploying the template, make sure you have the value for the following parameters:

|Parameter|Description|
|---|---|
|VpcId|VPC ID where the lambdas will be deployed.|
|SubnetIds|List of SUbnet IDs where the lambdas will be deployed.|
|DatamasqueBaseUrl|DATAMASQUE instance URL.|
|DatmasqueUser|DATAMASQUE user.|
|DatamasquePassword|DATAMASQUE password.|
|DatamasqueConnectionId|DATAMASQUE connection ID.|
|DatamasqueRuleSetId|DATAMASQUE Rule Set ID.|

1. Check out the code and change to the `datamasque-blueprint` directory.
2. Run `sam build`.
3. Run `sam deploy --guided`.


During the guided deployment, you will be asked if you would like to save the parameters in an AWS SAM configuration file `samconfig.toml`.

An example of the configuration file is presented below:

```ini
version = 0.1
[default]
[default.deploy]
[default.deploy.parameters]
stack_name = "datamasque-blueprint"
s3_bucket = "aws-sam-cli-managed-default-samclisourcebucket-xxxxxxxxx"
s3_prefix = "datamasque-blueprint"
region = "ap-southeast-2"
capabilities = "CAPABILITY_IAM"
image_repositories = []

parameter_overrides = "VpcId=\"vpc-xxxxxxxx\" SubnetIds=\"subnet-xxxxxxxxxxxxx\" DatamasqueBaseUrl=\"https://10.11.12.13/\" DatmasqueUser=\"admin\" DatamasquePassword=\"123@321$\" DatamasqueConnectionId=\"41xxxxxe7-fxxd-xxx5-8xxe-62xxxxxxxxe62\" DatamasqueRuleSetId=\"2bxxxxxxxb-3xxc-4xxe-axxxb-c35xxxxxxxx40\""

```

## Step Function execution.

The AWS SAM template will create a CloudWatch event rule to trigger the Step Function execution once a week.

```YAML
Events:
        Schedule:
          Type: Schedule # More info about Schedule Event Source: https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/sam-property-statemachine-schedule.html
          Properties:
            Description: Schedule to run the DATAMASQUE state machine weekly
            Enabled: False 
            Schedule: "rate(7 days)"
            Input: '{"DBInstanceIdentifier": "prod-postgres-04-rds"}'

```

You can also execute the step function manually.

```JSON
{
    "DBInstanceIdentifier":"dtq-postgres-datamasque-xxx"
}
```

## Statemachine definition

The following table describes the states and details of the step function definition.

|Step|Description|
|---|---|
| Describe DB Snapshots  | Fetch the latest snapshot of the target RDS instance.  |
| Describe DB Instances  | Fetch the configuration of the target RDS instance.  |
| Restore DB from Snapshot  | Restore the snapshot using the appropriate configuration.  |
| Wait for DB Instance  |  Wait for the instance to be available. |
| Datamasque API run  |  Create a masking job base don the connection id and ruleset provided. |
| SQS SendMessage  | Send a message to a queue to wait until the job is finished.  |
| CreateDBSnapshot  | Create a snapshot of the staging RDS db instance.  |
| DeleteDBInstance  | Delete the staging RDS db instance.  |


![AWS Step Function definition](/stepfunction.png "AWS Step Function")


## Sharing the Snapshot

Sharing snapshots encrypted with the default service key for RDS is currently not supported.  [Sharing a DB snapshot](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_ShareSnapshot.html).

To share your encrypted snapshot with another account, you will also need to share the custom master key with the other account through KMS. [Changing a key policy](https://docs.aws.amazon.com/kms/latest/developerguide/key-policy-modifying.html#key-policy-modifying-external-accounts).

The masked snapshot can be shared with the following methods:

 - Add an RDS modify db snapshot step to the lambda function.
 - Use the native mechanism within the AWS Console.
 - Use an existing CI/CD pipeline to copy and re-encrypt the snapshot.

## Planned improvements

- Improve handling of DataMasque instance password using AWS Secrets Manager.
- Create the DataMasque connection with the staging RDS instance dynamically via the API.
- Improve the RestoreFromSnapshot API call handling to retrieve the RDS DB instance provisioning status.

