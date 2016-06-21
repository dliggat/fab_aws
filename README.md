# cf_toolkit

A collection of utilities for AWS CloudFormation & Lambda, implemented as Python Fabric tasks.

## 0) Install

1. Set up a `virtualenv` (I recommend [`pyenv-virtualenv`](https://github.com/yyuu/pyenv-virtualenv), highly):
  * `pyenv virtualenv cf_toolkit`
2. Install dependencies:
  * `pip install -U -r requirements.txt`


## 1) Write CloudFormation in YAML
JSON is awkward to write and read, and among its other deficiencies as a configuration file format, does not allow comments. So write in YAML, and use `cf_toolkit` to convert:

```yaml
AWSTemplateFormatVersion: "2010-09-09"

Description: A CF stack to implement {{ this['name'] }}.

Metadata:
  CommitHash: {{ git['hash'] }}
  CommitDescription: {{ git['message'] }}
  AnyUnstagedChanges?: {{ git['unstaged'] }}


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


## 3) Build Deployable Lambda Package

```bash
# Installs dependencies and builds a deployable zip file.
# e.g. ./lambda/dn_stack/_builds/2016-06-15T17.22.40.467141-dn_stack.zip

fab build:function_name=dn_stack
```

