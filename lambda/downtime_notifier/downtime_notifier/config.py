import glob
import os
import yaml


CONFIG_DIR = os.path.join(os.path.dirname(__file__), '..', 'lambda_config')
CONFIG_EXT = '*.yaml'
CONFIG_FILES = sorted(glob.glob(os.path.join(CONFIG_DIR, CONFIG_EXT)), reverse=True)

def configuration():
    print(CONFIG_DIR)

    config = {}
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
    return config
