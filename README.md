# cf-toolkit

A collection of utilities for AWS CloudFormation & Lambda, implemented as Python Fabric tasks.

## Install

1. Set up a `virtualenv` (I recommend [`pyenv-virtualenv`](https://github.com/yyuu/pyenv-virtualenv), highly):
  * `pyenv virtualenv cf-toolkit`
2. Install dependencies:
  * `pip install -U -r requirements.txt`


## Write CloudFormation in YAML
JSON is awkward to write and read, and among its other deficiencies as a configuration file format, does not allow comments. So write in YAML, and use `cf-toolkit` to convert:

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
    Default: {{ lambda_uptime['schedule_expression'] }}
    Description: How often to invoke the {{ this['name'] }} function


Resources:
  ScheduledRule:
    Type: AWS::Events::Rule
    Properties:
      Description: ScheduledRule for the LambdaFunction
      ScheduleExpression: { "Ref": "ScheduleExpression" }
      State: ENABLED
      Targets:
        - Arn: { "Fn::GetAtt": [ LambdaFunction, Arn ] }
          Id: ScheduledRule

  NotificationTopic:
    Type: AWS::SNS::Topic
    Properties:
      DisplayName: {{ this['name'] }}Topic

Outputs:
  SnsTopic:
    Value: { "Ref": "NotificationTopic" }
```



## Render CloudFormation JSON

`cf-toolkit` converts CloudFormation YAML from `cloudformation/` into JSON, and injects configuration state from `config/` along the way. Final output appears at `_output/`.

This is all convention driven, based on filename: configuration from `config/foo.yaml` is injected into a CloudFormation-YAML template at `cloudformation/foo.yaml.jinja`, and rendered out as CloudFormation-JSON at `_output/foo.template`:

```bash
fab render validate
```


### Local Configuration

`config/*.local.yaml` files are git-ignored. They are merged into the configuration with a higher priority than non-local configuration. This provides an easy way to inject secrets, and keep them out of the repo.

## Provision AWS Resources

The `provision` Fabric task will create a CloudFormation stack with the given name, or update the existing stack if that name already exists. It makes sense to `render` and `validate` at the same time:

```bash
# Render a 'foo' stack template to JSON, and create a CloudFormation stack of that type
# with name 'my-foo-stack'.

fab render validate provision:template_name=foo,stack_name=my-foo-stack
```

Note that the `stack_name` must be unique in your current CloudFormation account, or an update will result.
