import boto3
import glob
import os
import yaml

from base64 import b64decode


CONFIG_DIR = os.path.join(os.path.dirname(__file__), '..', 'lambda_config')
CONFIG_EXT = '*.yaml'
CONFIG_FILES = sorted(glob.glob(os.path.join(CONFIG_DIR, CONFIG_EXT)), reverse=True)

def configuration():
    """Load configuration from config files, with .local.yaml files overriding non-local."""
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

    # Decrypt any `encrypted_` parameters, and replace in the dict with plaintext variants.
    # This will fail if the Lambda execution role was not granted decrypt:* in the key policy of
    # the KMS key that was used to create the ciphertext.
    for (name, config_bag) in config.iteritems():
        new_config = {}
        for (k,v) in config_bag.iteritems():
            key = k
            value = v
            if k.startswith('encrypted_'):
                key = k.split('encrypted_')[-1]
                value = boto3.client('kms').decrypt(CiphertextBlob=b64decode(v))['Plaintext']
            new_config[key] = value
        config[name] = new_config
    return config
