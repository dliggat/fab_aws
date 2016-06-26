import boto3


class Utility(object):
    """Container class for utility functions."""

    _aws_account_id = None

    @classmethod
    def aws_account_id(cls):
        """Query for the current account ID by inspecting the default security group."""
        if cls._aws_account_id is None:
            cls._aws_account_id = int(boto3.client('ec2').describe_security_groups(
                GroupNames=['default'])['SecurityGroups'][0]['OwnerId'])
        return cls._aws_account_id
