import boto3
import glob
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
from fabric.utils import abort
from pprint import pprint

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

root_dir = os.path.dirname(__file__)
json_dir = os.path.join(root_dir, 'json')
yaml_files = glob.glob(os.path.join(root_dir, 'yaml/*.yaml'))
json_files = glob.glob(os.path.join(root_dir, 'json/*.template'))


@task(default=True)
def render():
    if not yaml_files:
        abort('No YAML files present in directory')

    if not os.path.exists(json_dir):
        logger.info('Created directory: %s', json_dir)
        os.makedirs(json_dir)

    for yaml_file in yaml_files:
        with open(yaml_file, 'r') as yaml_contents:
            data = yaml.load(yaml_contents.read())
            json_str = json.dumps(data, indent=2)
            json_file = os.path.join(json_dir, os.path.basename(yaml_file).split('.')[0]) + '.template'
            with open(json_file, 'w') as json_contents:
                json_contents.write(json_str)
                logger.info('Converted %s to %s', os.path.basename(yaml_file), os.path.basename(json_file))

@task
def validate():
    client = boto3.client('cloudformation')
    for json_file in json_files:
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
    with open(os.path.join(json_dir, template_name + '.template')) as json_contents:
        response = client.create_stack(StackName=stack_name,
                                       TemplateBody=json_contents.read(),
                                       Capabilities=['CAPABILITY_IAM'])
        logger.info(response)



@task
def clean():
    for f in json_files:
        os.remove(f)



