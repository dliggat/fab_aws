import boto3
import datetime
import glob
import jinja2
import json
import os
import pprint
import subprocess
import yaml

from collections import OrderedDict
from botocore.exceptions import ClientError, ValidationError

import logging; logging.basicConfig()
import coloredlogs
logger = logging.getLogger()
coloredlogs.install(level=logging.INFO)

from fabric.api import task
from fabric.operations import local
from fabric.contrib.console import confirm
from fabric.utils import abort


# Configure PyYaml to preserve order in dictionaries (ensures CloudFormation templates render
# in an expected top-level key order).
def construct_ordered_mapping(loader, node, deep=False):
    if isinstance(node, yaml.MappingNode):
        loader.flatten_mapping(node)
    return OrderedDict(loader.construct_pairs(node, deep))

def construct_yaml_ordered_map(loader, node, deep=False):
    data = OrderedDict()
    yield data
    value = construct_ordered_mapping(loader, node, deep)
    data.update(value)

yaml.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, construct_yaml_ordered_map)


# Various constants and config setup.
ROOT_DIR     = os.path.dirname(__file__)
INPUT_DIR    = os.path.join(ROOT_DIR, 'cloudformation')
INPUT_EXT    = '.yaml.jinja'
INPUT_FILES  = glob.glob(os.path.join(INPUT_DIR, '*{0}'.format(INPUT_EXT)))

OUTPUT_DIR   = os.path.join(ROOT_DIR, '_output')
OUTPUT_EXT   = '.template'
OUTPUT_FILES = glob.glob(os.path.join(OUTPUT_DIR, '*{0}'.format(OUTPUT_EXT)))

# Ensure that .local.yaml config files are loaded last, so that they take precedence in the config dict.
CONFIG_DIR   = os.path.join(ROOT_DIR, 'cloudformation_config')
CONFIG_FILES = sorted(glob.glob(os.path.join(CONFIG_DIR, '*{0}'.format('.yaml'))), reverse=True)

LAMBDA_DIR = os.path.join(ROOT_DIR, 'lambda')
BUILDS_SUBDIR = '_builds'
STAGING_SUBDIR = '_staging'
LAMBDA_CONFIG_SUBDIR = 'lambda_config'


def load_config():
    """Load the config from the config directory into a deep dict, keyed by stack type."""
    config = {'git': {'hash': subprocess.check_output(['git', 'rev-parse', 'HEAD'])[:-1],
                      'message': subprocess.check_output([
                          'git', 'log', '-1', '--pretty=%B']).strip().replace('"', '')
                                                                     .replace('#', '')
                                                                     .replace('\n', '')
                                                                     .replace(':', ' '),
                      'uncommitted': True if subprocess.call(
                          'git diff-index --quiet HEAD --'.split(' ')) else False }}

    for config_file in CONFIG_FILES:
        with open(config_file, 'r') as config_file_contents:
            data = yaml.load(config_file_contents.read())
            if not data:
                continue
            basename = os.path.basename(config_file).split('.')[0]
            if basename in config:
                config[basename].update(data)
            else:
                config[basename] = data

    for (basename, config_item) in config.iteritems():
        if basename == 'git':
            continue
        if not config_item.has_key('parameters'):
            config_item['parameters'] = OrderedDict()

        # Coalesce the parameters into the format expected by boto3.client('cloudformation').
        config_item['parameters'] = [
            {'ParameterKey': k,
             'ParameterValue': v,
             'UsePreviousValue': False} for (k,v) in config_item['parameters'].items()]


    logger.info('Loaded config: %s', pprint.pprint(config))
    return config


# Fabric tasks.
@task(default=True)
def render():
    """Render yaml.jinja to JSON, via the loaded config."""
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
        config   = load_config()
        config.update({'__name__': basename})
        rendered = template.render(**config)
        data = yaml.load(rendered)

        output_str  = json.dumps(data, indent=2, separators=(',', ': '))
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
def provision(template_name=None, stack_name=None):
    """Creates or updates a CloudFormation stack based on the supplied template type name.

    Args:
        template_name: (str) The name of the template from the input directory.
        stack_name: (str) The stack name to use for CloudFormation.
    """
    if not template_name:
        abort('Must provide template')
    if not stack_name:
        abort('Must provide stack_name')
    client = boto3.client('cloudformation')

    config = load_config()

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
                                           Parameters=config.get(template_name, {}).get('parameters', []),
                                           Capabilities=['CAPABILITY_IAM'])
        else:
            response = client.create_stack(StackName=stack_name,
                                           TemplateBody=output_contents.read(),
                                           Parameters=config.get(template_name, {}).get('parameters', []),
                                           Capabilities=['CAPABILITY_IAM'])
        logger.info(json.dumps(response, indent=2))


@task
def clean():
    """"Deletes all the rendered _output CloudFormation files."""
    for f in OUTPUT_FILES:
        os.remove(f)


@task
def install_reqs(function_name=None):
    """Installs requirements.txt dependencies for the given Lambda function.

    Args:
        function_name: (str) The Lambda function within the lambda/ directory to work on.
    """
    if not function_name:
        abort('Must provide function_name')

    requirements_file = os.path.join(LAMBDA_DIR, function_name, 'requirements.txt')
    output = local('pip install -U -r {0} 2>&1'.format(requirements_file), capture=True)
    logger.info(output)


@task
def invoke(function_name=None):
    """Invokes the given Lambda function.

    Args:
        function_name: (str) The Lambda function within the lambda/ directory to work on.
    """
    if not function_name:
        abort('Must provide function_name')

    index_file = os.path.join(LAMBDA_DIR, function_name, 'index.py')
    output = local('python {0} 2>&1'.format(index_file), capture=True)
    logger.info(output)


@task
def build(function_name=None):
    """Creates a deployable package for the given Lambda function in its _builds/ directory.

    Args:
        function_name: (str) The Lambda function within the lambda/ directory to work on.
    """
    if not function_name:
        abort('Must provide function_name')

    lambda_root = os.path.join(LAMBDA_DIR, function_name)
    module_dir = os.path.join(lambda_root, function_name)
    lambda_config_dir = os.path.join(lambda_root, LAMBDA_CONFIG_SUBDIR)
    staging_dir = os.path.join(lambda_root, STAGING_SUBDIR)
    builds_dir = os.path.join(lambda_root, BUILDS_SUBDIR)
    build_filename = '{0}-{1}.zip'.format(
        datetime.datetime.now().isoformat().replace(':', '.'), function_name)

    # Erase previous runs of the build task.
    local('rm -rf {0}'.format(staging_dir))

    # Set up staging and builds directories.
    local('mkdir -p {0}'.format(staging_dir))
    local('mkdir -p {0}'.format(builds_dir))

    # Install the lambda specific requirements.
    local('pip install -r {0}/requirements.txt -t {1}'.format(lambda_root, staging_dir))

    # Copy the top level *.py (e.g. index.py) and lambda_config dir into the staging_dir.
    local('cp -R {0}/*.py {1}'.format(lambda_root, staging_dir))
    local('cp -R {0} {1}'.format(lambda_config_dir, staging_dir))

    # Copy the module directory into the staging dir.
    local('cp -R {0} {1}'.format(module_dir, staging_dir))

    # Zip the whole thing up, and move it to the builds dir.
    local('cd {0}; zip -r {1} ./*; mv {1} {2}'.format(staging_dir, build_filename, builds_dir))


@task
def deploy(function_name=None, arn=None):
    """Uploads the latest build of the function package to the Lambda ARN.

    Args:
        function_name: (str) The Lambda function within the lambda/ directory to work on.
        arn: (str) The ARN of the deployed function.
    """
    if not function_name:
        abort('Must provide function_name')
    if not arn:
        abort('Must provide arn')

    lambda_root = os.path.join(LAMBDA_DIR, function_name)
    builds_dir = os.path.join(lambda_root, BUILDS_SUBDIR)
    builds = sorted(glob.glob(os.path.join(builds_dir, '*.{0}'.format('zip'))))
    if not builds:
        abort('No builds exist. Run a `build` command first')
    latest_build = builds[-1]
    logging.info('Preparing to deploy build: {0}'.format(latest_build))

    client = boto3.client('lambda')
    with open(latest_build, 'rb') as zip_file:
        response = client.update_function_code(FunctionName=arn, ZipFile=zip_file.read())
        logger.info(json.dumps(response, indent=2))





