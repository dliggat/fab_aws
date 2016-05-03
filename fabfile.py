import glob
import os
import yaml
import json

import logging; logging.basicConfig()
logger = logging.getLogger()
logger.setLevel(logging.INFO)

from fabric.api import task
from fabric.utils import abort

@task
def test():
    print('boo')
    abort('failed')

@task(default=True)
def render():
    root_dir = os.path.dirname(__file__)
    yaml_files = glob.glob(os.path.join(root_dir, 'yaml/*.yaml'))
    if not yaml_files:
        abort('No YAML files present in directory')
    for yaml_file in yaml_files:
        with open(yaml_file, 'r') as yaml_contents:
            data = yaml.load(yaml_contents.read())
            json_str = json.dumps(data, indent=2)
            json_file = os.path.join(root_dir, 'json',
                                     os.path.basename(yaml_file).split('.')[0]) + '.template'
            with open(json_file, 'w') as json_contents:
                json_contents.write(json_str)
                logger.info('Converted %s to %s', os.path.basename(json_file), os.path.basename(yaml_file))


