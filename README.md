# cf-toolkit

A collection of utilities for AWS CloudFormation & Lambda, implemented as Python Fabric tasks.

## Install

1. Set up a `virtualenv`:
  * `pyenv virtualenv cf-toolkit`
2. Install dependencies:
  * `pip install -U -r requirements.txt`


## Render CloudFormation JSON

`cf-toolkit` converts CloudFormation YAML from `cloudformation/` into JSON, and injects configuration state from `config/` along the way. Final output appears at `_output/`.

This is all convention driven, based on filename: `config/foo.yaml` is injected into `cloudformation/foo.yaml.jinja`, as rendered out as `_output/foo.template`:

    fab render validate


### Local Configuration

`config/*.local.yaml` files are git-ignored. They are merged into the configuration with a higher priority than non-local configuration. This provides an easy way to inject secrets, and keep them out of the repo.

## Provision AWS Resources

The `provision` Fabric task will create a CloudFormation stack with the given name, or update the existing stack if that name already exists. It makes sense to `render` and `validate` at the same time:

    # Render a 'foo' stack template to JSON, and create a CloudFormation stack of that type
    # with name 'my-foo-stack'.
    fab render validate provision:template_name=foo,stack_name=my-foo-stack

Note that the `stack_name` must be unique in your current CloudFormation account, or an update will result.
