import uuid

from utility import Utility


class LocalContext(object):
    """A simulated context object for local execution of Lambda functions."""

    @property
    def invoked_function_arn(self):
        """Simulate the Lambda ARN that comes into the context object."""
        return 'arn:aws:lambda:{0}:{1}:function:func-name'.format(
            'us-west-2', Utility.aws_account_id())

    @property
    def aws_request_id(self):
        """Simulate the request guid that comes into the context object."""
        return str(uuid.uuid1())

    def __str__(self):
      return str((self.invoked_function_arn, self.aws_request_id))
