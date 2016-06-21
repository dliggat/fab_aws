# cf_toolkit

A convention-driven collection of utilities for AWS CloudFormation & Lambda, implemented as Python Fabric tasks.

## 0) Install

1. Set up a `virtualenv` (I recommend [`pyenv-virtualenv`](https://github.com/yyuu/pyenv-virtualenv), highly):
  * `pyenv virtualenv cf_toolkit`
2. Install dependencies:
  * `pip install -U -r requirements.txt`
3. From this point forward, the `fab` command will be available to run the tasks from `fabfile.py`.


## 1) Write CloudFormation in YAML
JSON is awkward to write and read, and among its other deficiencies as a configuration file format, does not allow comments. So write in YAML, and use `fab render` to convert.

```yaml
# cloudformation/dn_stack.yaml.jinja
AWSTemplateFormatVersion: "2010-09-09"

Description: A CF stack to implement {{ this['name'] }}.

Metadata:
  CommitHash: {{ git['hash'] }}
  CommitDescription: {{ git['message'] }}
  AnyUncommittedChanges?: {{ git['uncommitted'] }}


Parameters:
  ScheduleExpression:
    Type: String
    Default: {{ dn_stack['schedule_expression'] }}
    Description: How often to invoke the {{ this['name'] }} function


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
      DisplayName: {{ this['name'] }}Topic

Outputs:
  SnsTopic:
    Value: { Ref : NotificationTopic }
```



## 2) Render CloudFormation JSON

`cf_toolkit` converts CloudFormation YAML from `cloudformation/` into JSON, and injects configuration state from `cloudformation_config/` along the way. Final output appears at `_output/`.

This is all convention driven, based on filename: configuration from `cloudformation_config/dn_stack.yaml` is injected into a CloudFormation-YAML template at `cloudformation/dn_stack.yaml.jinja`, and rendered out as CloudFormation-JSON at `_output/dn_stack.template`:

```bash
# Render all YAML templates to JSON, and validate against the CloudFormation API.
fab render validate
```


### Local CloudFormation Configuration

`cloudformation_config/*.local.yaml` files are git-ignored. They are merged into the configuration with a higher priority than non-local configuration. This provides an easy way to inject secrets, and keep them out of the repo.

## 3) Provision AWS Resources

The `provision` Fabric task will create a CloudFormation stack with the given name, or update the existing stack if that name already exists. It makes sense to `render` and `validate` at the same time:

```bash
# Render a 'dn_stack' stack template to JSON, and create a CloudFormation stack of that type
# with name 'my-dn-stack'.

fab render validate provision:template_name=dn_stack,stack_name=my-dn-stack
```

Note that the `stack_name` must be unique within your current set of CloudFormation stacks, or an update will result.


## 3) Create and maintain Lambda code

`cf_toolkit` specifies a particular directory structure for Lambda functions. Adhering to this structure allows for very convenient code organization, package builds, and deployment to a live Lambda function ARN.

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

### Local Lambda Configuration
As above, `.local.yaml` files in `lambda_config` are git-ignored.

### Decrypting KMS secrets
Alternatively, one

## 4) Build Deployable Lambda Package

```bash
# Installs dependencies and builds a deployable zip file.
# e.g. ./lambda/dn_stack/_builds/2016-06-15T17.22.40.467141-dn.zip

fab build:function_name=downtime_notifier
```

## 5) Deploy

TODO

