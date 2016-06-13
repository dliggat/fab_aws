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


# Configure PyYaml to preserve order in dictionaries (ensures CloudFormation templates render
# in an expected top-level key order).
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


# Various constants and config setup.
ROOT_DIR     = os.path.dirname(__file__)
INPUT_DIR    = os.path.join(ROOT_DIR, 'input')
INPUT_EXT    = '.yaml.jinja'
INPUT_FILES  = glob.glob(os.path.join(INPUT_DIR, '*{0}'.format(INPUT_EXT)))

OUTPUT_DIR   = os.path.join(ROOT_DIR, '_output')
OUTPUT_EXT   = '.template'
OUTPUT_FILES = glob.glob(os.path.join(OUTPUT_DIR, '*{0}'.format(OUTPUT_EXT)))

CONFIG_DIR   = os.path.join(ROOT_DIR, 'config')
CONFIG_FILES = glob.glob(os.path.join(CONFIG_DIR, '*{0}'.format('.yaml')))

def load_config():
    """Load the config from the config directory into a deep dict, keyed by stack type."""
    config = {}
    for config_file in CONFIG_FILES:
        with open(config_file, 'r') as config_file_contents:
            data = yaml.load(config_file_contents.read())
            config[os.path.basename(config_file).split('.')[0]] = data
    logger.info('Loaded config: %s', config)
    return config


# Fabric tasks.
@task(default=True)
def render():
    """Render yaml.jinja to JSON, via the loaded config."""
    config = load_config()
    if not INPUT_FILES:
        abort('No YAML files present in directory')

    if not os.path.exists(OUTPUT_DIR):
        logger.info('Created directory: %s', OUTPUT_DIR)
        os.makedirs(OUTPUT_DIR)

    # Load the Jinja environment.
    env = jinja2.Environment(trim_blocks=True, lstrip_blocks=True, undefined=jinja2.StrictUndefined)
    env.loader = jinja2.FileSystemLoader(INPUT_DIR)

    # For each file in the input directory; run through a Jinja render and convert to JSON.
    for input_file in INPUT_FILES:
        basename = os.path.basename(input_file).split('.')[0]
        template = env.get_template('{0}{1}'.format(basename, INPUT_EXT))
        rendered = template.render(**config)
        data = yaml.load(rendered)

        output_str  = json.dumps(data, indent=2)
        output_file = os.path.join(OUTPUT_DIR, os.path.basename(input_file).split('.')[0]) + OUTPUT_EXT
        with open(output_file, 'w') as output_contents:
            output_contents.write(output_str)
            logger.info('Converted %s to %s', os.path.basename(input_file), os.path.basename(output_file))


@task
def validate():
    """Validates the rendered template against the CloudFormation API."""
    client = boto3.client('cloudformation')
    for output_file in OUTPUT_FILES:
        with open(output_file, 'r') as output_contents:
            try:
                client.validate_template(TemplateBody=output_contents.read())
            except (ClientError, ValidationError) as e:
                logger.error('Unable to validate {0}. Exception: {1}'.format(output_file, e))
                abort('Template validation error')


@task
def launch(template_name=None, stack_name=None):
    """Creates or updates a CloudFormation stack based on the supplied template type name.

    Args:
        template_name (str): The name of the template from the input directory.
        stack_name (str): The stack name to use for CloudFormation.
    """
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

    with open(os.path.join(OUTPUT_DIR, template_name + OUTPUT_EXT)) as output_contents:
        if update:
            response = client.update_stack(StackName=stack_name,
                                           TemplateBody=output_contents.read(),
                                           Capabilities=['CAPABILITY_IAM'])
        else:
            response = client.create_stack(StackName=stack_name,
                                           TemplateBody=output_contents.read(),
                                           Capabilities=['CAPABILITY_IAM'])
        logger.info(response)


@task
def clean():
    """"Deletes all the rendered output files."""
    for f in OUTPUT_FILES:
        os.remove(f)
