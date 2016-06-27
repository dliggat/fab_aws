# fab_aws

A convention-driven collection of utilities for AWS CloudFormation & Lambda, implemented as Python Fabric tasks. As an initial proof-of-concept, the elements herein implement a **downtime-notifier** system for websites; i.e. a Lambda function that periodically opens a HTTP connection to each of a set of websites, and posts to a SNS topic in the event of a failure.

## Directory Structure

`fab_aws` uses the following basic structure:

```bash
.
├── README.md
├── _output                   # Output location for rendered CloudFormation JSON.
│   ├── dn_stack.template
│   └── kms_stack.template
├── cloudformation            # YAML representation of CloudFormation. Each file => 1 CF stack.
│   ├── dn_stack.yaml.jinja
│   └── kms_stack.yaml.jinja
├── cloudformation_config     # Configuration to be injected; .local.yaml files are gitignored.
│   ├── dn_stack.local.yaml
│   ├── dn_stack.yaml
│   └── kms_stack.local.yaml
├── fabfile.py                # Contains task definitions. To run: `fab $TASK_NAME`.
├── lambda                    # Root directory for Lambda functions. See below.
│   └── downtime_notifier/
│   └── other_function1/
│   └── other_function2/
└── requirements.txt          # Dependencies for fab_aws. Install locally using pip.
```

## 0) Install

1. Set up a `virtualenv` (I recommend [`pyenv-virtualenv`](https://github.com/yyuu/pyenv-virtualenv), highly):
  * `pyenv virtualenv fab_aws`
2. Install dependencies:
  * `pip install -U -r requirements.txt`
3. From this point forward, the `fab` command will be available to run the tasks from `fabfile.py`.


## 1) Configure AWS Credentials
`fab_aws` uses the `boto3` Python AWS SDK. When the Fabric tasks are run, the **AWS credentials are inherited from the containing shell**. For most AWS users, this probably means that you have one or more AWS profiles configured, and a particular one either enabled or set to the default. As I interact with numerous profiles on a daily basis, I used [named profiles](https://liggat.org/juggling-multiple-aws-profiles/) to handle this. If you do not have profiles set up, [this article](http://docs.aws.amazon.com/cli/latest/userguide/cli-chap-getting-started.html) in the AWS documentation explains the configuration, as well as the other precedence-based options that exist for authentication.


## 2) Write CloudFormation in YAML
JSON is awkward to write and read, and among its other deficiencies as a configuration file format, does not allow comments. So write in YAML, and use `fab render` to convert.

```yaml
# cloudformation/dn_stack.yaml.jinja
AWSTemplateFormatVersion: "2010-09-09"

Description: A CF stack to implement {{ __name__ }}.

Metadata:
  CommitHash: {{ git['hash'] }}
  CommitDescription: {{ git['message'] }}
  AnyUncommittedChanges?: {{ git['uncommitted'] }}


Parameters:
  ScheduleExpression:
    Type: String
    Default: {{ dn_stack['schedule_expression'] }}
    Description: How often to invoke the {{ __name__ }} function


Resources:
  ScheduledRule:
    Type: AWS::Events::Rule
    Properties:
      Description: ScheduledRule for the LambdaFunction
      ScheduleExpression: { Ref : ScheduleExpression }
      State: ENABLED
      Targets:
        - Arn: { "Fn::GetAtt": [ LambdaFunction, Arn ] }
          Id: ScheduledRule

  # Other resources
  # ...

  NotificationTopic:
    Type: AWS::SNS::Topic
    Properties:
      DisplayName: {{ __name__ }}Topic

Outputs:
  SnsTopic:
    Value: { Ref : NotificationTopic }
```



## 3) Render CloudFormation JSON

`fab_aws` converts CloudFormation YAML from `cloudformation/` into JSON, and injects configuration state from `cloudformation_config/` along the way. Final output appears at `_output/`.

This is all convention driven, based on filename: configuration from `cloudformation_config/dn_stack.yaml` is injected into a CloudFormation-YAML template at `cloudformation/dn_stack.yaml.jinja`, and rendered out as CloudFormation-JSON at `_output/dn_stack.template`:

```bash
# Render all YAML templates to JSON, and validate against the CloudFormation API.
fab render validate
```


### Local CloudFormation Configuration

`cloudformation_config/*.local.yaml` files are git-ignored. They are merged into the configuration with a higher priority than non-local configuration. This provides an easy way to inject secrets, and keep them out of the repo.


## 4) Provision AWS Resources

The `provision` Fabric task will create a CloudFormation stack with the given name, or update the existing stack if that name already exists. It makes sense to `render` and `validate` at the same time:

```bash
# Render a 'dn_stack' stack template to JSON, and create a CloudFormation stack of that type
# with name 'my-dn-stack'.

TEMPLATE=dn_stack
STACK_ID=my-dn-stack
fab render validate provision:template_name=$TEMPLATE,stack_name=$STACK_ID
```

Note that the `stack_name` must be unique within your current set of CloudFormation stacks, or an update will result.


## 5) Create and maintain Lambda code

`fab_aws` specifies a particular directory structure for Lambda functions. Adhering to this structure allows for very convenient code organization, package builds, and deployment to a live Lambda function ARN.

```bash
lambda/downtime_notifier                   # Root directory for the function elements.
├── _builds                                # Builds of the `_staging` directory.
│   ├── 2016-06-15T17.22.40.467141-dn.zip
│   ├── 2016-06-15T17.24.41.938070-dn.zip
├── _staging                               # Staging area used prior to zip packaging.
├── downtime_notifier                      # A Python module for the Lambda function's code.
│   ├── __init__.py
│   ├── config.py
│   ├── localcontext.py
│   ├── utility.py
├── index.py                               # Lambda function entry point.
├── lambda_config                          # Configuration directory for the Lambda function.
│   ├── env.local.yaml                     # gitignored Lambda configuration.
│   └── env.yaml                           # Lambda configuration.
└── requirements.txt                       # Lambda-function specific dependencies to install.
```

### Lambda Configuration
The `lambda_config` directory is a location to place YAML files that can be deserialized by `config.py` within the Lambda runtime.

### Local Lambda Configuration
As above, `.local.yaml` files in `lambda_config` are git-ignored.

### Decrypting KMS secrets
Configuration keys with an `encrypted_` prefix are assumed to be encrypted by KMS. `config.py` will attempt to decrypt these first. To ensure this is possible, the Lambda role under which this function runs should have the `Decrypt:*` privilege specified in the key policy.

## 6) Build Deployable Lambda Package

```bash
# Installs dependencies and builds a deployable zip file.
# e.g. ./lambda/dn_stack/_builds/2016-06-15T17.22.40.467141-dn.zip

FUNCTION=downtime_notifier
fab build:function_name=$FUNCTION
```

## 7) Deploy Lambda Package

This will update the currently deployed Lambda code to the latest build.

```bash
# Installs the latest built Lambda package to the specified Lambda function ARN.

FUNCTION_NAME=downtime_notifier
ARN=arn=arn:aws:lambda:us-west-2:111111111:function:downtime-notifier-stack-LambdaFunction-J3R
fab deploy:function_name=$FUNCTION_NAME,arn=$ARN

