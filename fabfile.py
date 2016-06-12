import boto3
import glob
import jinja2
import json
import os
import yaml
from collections import OrderedDict as odict
from botocore.exceptions import ClientError, ValidationError

import logging; logging.basicConfig()
import coloredlogs
logger = logging.getLogger()
coloredlogs.install(level=logging.INFO)

from fabric.api import task
from fabric.contrib.console import confirm
from fabric.utils import abort

# Configure PyYaml to create ordered dicts
_mapping_tag = yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG

def construct_ordered_mapping(loader, node, deep=False):
    if isinstance(node, yaml.MappingNode):
        loader.flatten_mapping(node)
    return odict(loader.construct_pairs(node, deep))

def construct_yaml_ordered_map(loader, node, deep=False):
    data = odict()
    yield data
    value = construct_ordered_mapping(loader, node, deep)
    data.update(value)

yaml.add_constructor(_mapping_tag, construct_yaml_ordered_map)

ROOT_DIR = os.path.dirname(__file__)
JSON_DIR = os.path.join(ROOT_DIR, '_output')
JSON_EXT = '.template'
YAML_FILES = glob.glob(os.path.join(ROOT_DIR, 'cloudformation/*.yaml.jinja'))
JSON_FILES = glob.glob(os.path.join(JSON_DIR, '*{0}'.format(JSON_EXT)))


@task(default=True)
def render():
    if not YAML_FILES:
        abort('No YAML files present in directory')

    if not os.path.exists(JSON_DIR):
        logger.info('Created directory: %s', JSON_DIR)
        os.makedirs(JSON_DIR)

    for yaml_file in YAML_FILES:
        with open(yaml_file, 'r') as yaml_contents:
            data = yaml.load(yaml_contents.read())
            json_str = json.dumps(data, indent=2)
            json_file = os.path.join(JSON_DIR, os.path.basename(yaml_file).split('.')[0]) + JSON_EXT
            with open(json_file, 'w') as json_contents:
                json_contents.write(json_str)
                logger.info('Converted %s to %s', os.path.basename(yaml_file), os.path.basename(json_file))

@task
def validate():
    client = boto3.client('cloudformation')
    for json_file in JSON_FILES:
        with open(json_file, 'r') as json_contents:
            try:
                client.validate_template(TemplateBody=json_contents.read())
            except (ClientError, ValidationError) as e:
                logger.error('Unable to validate {0}. Exception: {1}'.format(json_file, e))
                abort('Template validation error')


@task
def launch(template_name=None, stack_name=None):

    if not template_name:
        abort('Must provide template')
    if not stack_name:
        abort('Must provide stack_name')
    client = boto3.client('cloudformation')

    update = False
    try:
        resp = client.describe_stacks(StackName=stack_name)
        message = 'Stack {0} exists, and is in state {1}. Proceed with update?'.format(
            stack_name, resp['Stacks'][0]['StackStatus'])
        if not confirm(message):
            abort('Aborting.')
        else:
            update = True
    except ClientError:
        logger.info('No stack named {0}; proceeding with stack creation'.format(stack_name))

    with open(os.path.join(JSON_DIR, template_name + JSON_EXT)) as json_contents:
        if update:
            response = client.update_stack(StackName=stack_name,
                                           TemplateBody=json_contents.read(),
                                           Capabilities=['CAPABILITY_IAM'])
        else:
            response = client.create_stack(StackName=stack_name,
                                           TemplateBody=json_contents.read(),
                                           Capabilities=['CAPABILITY_IAM'])
        logger.info(response)


@task
def clean():
    for f in JSON_FILES:
        os.remove(f)



