# DataMasque AWS RDS Masking Stepfunctions Blueprint

## Introduction

DataMasque AWS blueprint templates are written in AWS CloudFormation format. The purpose of this template is to create a reusable data provisioning pipeline that calls DataMasque APIs to produce masked data that's safe for consumption in non-production environment.

The diagram below describes the DataMasque reference architecture in AWS.  This CloudFormation template is used to mask production RDS snapshots, create masked RDS snapshots which can be used to provision non-production databases - this incorporates the automation steps highlighted in blue.  Please refer to [DataMasque AWS Service Catalog Template](https://github.com/datamasque/DataMasque-AWS-service-catalog-database-provisioning-blueprint) to use AWS Service Catalog product as an End User Interface to provision non-production databases using masked RDS snapshots.

![Reference deployment](reference_deployment.png "Reference deployment")

The following lists the main AWS resources provisioned when this CloudFormation template is deployed:

- An AWS stepfunction.
- Five (5) AWS Lambda functions.
- A SQS queue.
- A CloudWatch event rule to schedule the Step Function execution once a week.

The provisioned stepfunctions coordinates tasks by calling AWS components/services and DataMasque masking APIs to
irreversibly replaces sensitive data such as PII, PCI and PHI with realistic, functional and consistent values.

You can trigger a data masking workflow by providing a RDS identifier to invoke execution of the deployed stepfunctions.
Upon completing the data masking workflow, an encrypted and masked RDS snapshot is produced, ready to be used to
provision non-production databases.

## Network

The diagram below describes the connectivities between the DataMasque instance, AWS Lambda functions (provisioned by
this template) and the staging RDS instance (provisioned by this template).

![Network requirements](network.png "Network requirements")

## Deployment

### Prerequisites

- AWS CLI configured with appropriate credential for the target AWS account.
- AWS SAM
  CLI: https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-sam-cli-install.html
- Python runtime 3.9 installed.
- A DataMasque instance.
- Source database with automated snapshots enabled.
- DataMasque `connection id` and `ruleset id`.

### Step-by-step

###### Store the DataMasque instance credentials on AWS Secrets Manager.

Make sure you have created a secret with the format below:

```json
{"username":"datamasque","password":"Example$P@ssword"}
```

###### Before deploying the template, please make sure you have the value for the following parameters:

| Parameter                                                                                                              | Description                                                                                                                    |
|------------------------------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------|
| VpcId                                                                                                                  | VPC ID where the lambdas will be deployed.                                                                                     |
| SubnetIds                                                                                                              | List of Subnet IDs where the lambdas will be deployed.  <br> The AWS Lambdas provisioned by this template will be placed on **private subnet** inside a VPC. It's recommended to provide at least two **SubnetIds** for redundancy and availability. |                                                                                                                                |
| DatamasqueBaseUrl                                                                                                      | DataMasque instance URL with the EC2's private IP, i.e. https://\<ec2-instance-private-ip>.                                    |
| DatamasqueSecretArn                                                                                                    | Secret with DataMasque instance credentials.                                                                                   |
| DatamasqueConnectionId                                                                                                 | DataMasque connection ID.                                                                                                      |
| DatamasqueRuleSetId                                                                                                    | DataMasque rulset ID.                                                                                                          |

###### Follow the steps to deploy the CloudFormation Stack:

1. Clone this repository
2. Open a terminal in the cloned repository directory
3. Run `sam build`.
4. Run `sam deploy --guided`.

During the guided deployment, you will be asked if you would like to save the parameters in an AWS SAM configuration
file `samconfig.toml`.

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

parameter_overrides = "VpcId=\"vpc-xxxxxxxx\" SubnetIds=\"subnet-xxxxxxxxxxxxx\" DatamasqueBaseUrl=\"https://10.11.12.13/\" DatamasqueSecretArn=\"xxxxxxxx\"  DatamasqueConnectionId=\"41xxxxxe7-fxxd-xxx5-8xxe-62xxxxxxxxe62\" DatamasqueRuleSetId=\"2bxxxxxxxb-3xxc-4xxe-axxxb-c35xxxxxxxx40\""

```

###### Please ensure the following network connectivities are configured after deploying the CloudFormation Stack:

- The source RDS DB instance **must** allow inbound connections from the DataMasque EC2 instance. The configuration will
  be replicated when creating the staging RDS.
- The DataMasque EC2 instance **must** allow inbound connections from the **DatamasqueRun** Lambda.
- The DataMasque EC2 instance **must** allow inbound connections from the **SqsConsumer** Lambda.

Please also ensure to allow stepfunctions to use the KMS key used on the source database to encrypt masked snapshots.

## AWS Step Function execution

### Invoke an execution manually

You can also execute the step function manually.

```JSON
{
  "DBInstanceIdentifier": "source-postgres-rds"
}
```

### Schedule data masking execution

The AWS SAM template creates a CloudWatch event rule that schedules a Step Function execution once a week which is
disabled by default. To use this scheduling functionality, you will need edit the rule to specify your target
DBInstanceIdentifier and enable the CloudWatch event rule.

```YAML
Events:
  Schedule:
    Type: Schedule # More info about Schedule Event Source: https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/sam-property-statemachine-schedule.html
    Properties:
      Description: Schedule to run the DATAMASQUE state machine weekly
      Enabled: False
      Schedule: "rate(7 days)"
      Input: '{"DBInstanceIdentifier": "source-postgres-rds"}'

```

###### Notes:

- The staging RDS instance created will follow the same RDS endpoint name schema as the source database with
  a `-datamasque` postfix after the DBInstanceIdentifier:

| RDS database         | Endpoint                                                                    |
|----------------------|-----------------------------------------------------------------------------|
| Source RDS instance  | ``source-postgres-rds``.xxxxxxxxxx.ap-southeast-2.rds.amazonaws.com         |
| Staging RDS instance | ``staging-postgres-datamasque``.xxxxxxxxxx.ap-southeast-2.rds.amazonaws.com |

- The RDS username, password and connection port will be the same as the source RDS instance.

- The staging RDS instance created during the execution of the stepfunction will be deleted when the execution is
  completed.

- The masked RDS snapshot created during the execution of the stepfunction will be preserved when the execution is
  completed.

## AWS Statemachine definition

The following table describes the states and details of the step function definition.

| Step                     | Description                                                           |
|--------------------------|-----------------------------------------------------------------------|
| Describe DB Snapshots    | Fetch the latest snapshot of the target RDS instance.                 |
| Describe DB Instances    | Fetch the configuration of the target RDS instance.                   |
| Restore DB from Snapshot | Restore the snapshot using the appropriate configuration.             |
| Wait for DB Instance     | Wait for the instance to be available.                                |
| Datamasque API run       | Create a masking job base don the connection id and ruleset provided. |
| SQS SendMessage          | Send a message to a queue to wait until the job is finished.          |
| CreateDBSnapshot         | Create a snapshot of the staging RDS db instance.                     |
| Wait for Snapshot        | Wait for the DB Snapshot to be available.                             |
| DeleteDBInstance         | Delete the staging RDS db instance.                                   |

![AWS Step Function definition](stepfunction.png "AWS Step Function")

## Sharing Masked AWS RDS Snapshots

Sharing snapshots encrypted with the default service key for RDS is currently not
supported.  [Sharing a DB snapshot](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_ShareSnapshot.html).

To share your encrypted snapshot with another account, you will also need to share the custom master key with the other
account through
KMS. [Changing a key policy](https://docs.aws.amazon.com/kms/latest/developerguide/key-policy-modifying.html#key-policy-modifying-external-accounts)
.

The masked snapshot can be shared with the following methods:

- Add an RDS modify db snapshot step to the lambda function.
- Use the native mechanism within the AWS Console.
- Use an existing CI/CD pipeline to copy and re-encrypt the snapshot.

## Planned improvements

- Create the DataMasque connection with the staging RDS instance dynamically.
