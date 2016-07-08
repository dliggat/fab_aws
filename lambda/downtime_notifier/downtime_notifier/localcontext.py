import uuid

from utility import Utility


class LocalContext(object):
    """A simulated context object for local execution of Lambda functions."""

    @property
    def invoked_function_arn(self):
        """Simulate the Lambda ARN that comes into the context object."""
        return 'arn:aws:lambda:{0}:{1}:function:func-name'.format(
            'us-west-2', Utility.aws_account_id())

    def __str__(self):
      return self.invoked_function_arn


def local_event():
    """Simulate the event payload that comes into the Lambda entry point."""
    return {'account': str(Utility.aws_account_id()), 'id': str(uuid.uuid1())}
