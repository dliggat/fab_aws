from utility import Utility

class LocalContext(object):
    @property
    def invoked_function_arn(self):
        """Simulate the Lambda ARN that comes into the context object. """
        return 'arn:aws:lambda:{0}:{1}:function:func-name'.format(
            'us-west-2', Utility.aws_account_id())

    def __str__(self):
      return self.invoked_function_arn
