import boto3
import datetime
import pprint

from downtime_notifier import configuration
from downtime_notifier import Checker


MAX_LEN = 100
CONFIG = configuration()


def handler(event, context):
    """Entry point for the Lambda function."""
    print('Using configuration: {0}'.format(CONFIG))
    checkers = []
    for site in CONFIG.get('env', {}).get('sites', []):
        c = Checker(**site)
        c.check()
        checkers.append(c)

    checkers = [r for r in checkers if r.exceptional]
    if checkers:
        notify(checkers)
    else:
        print("All checks passed: {0}.".format(datetime.datetime.now()))


def notify(checkers):
    """Craft a message about the site downtime, and publish to the SNS topic.

    Args:
        checkers (list): Sites which failed the check.
    """
    subject = "{0} {1}".format(CONFIG['env']['subject_prefix'],
                               ', '.join([r.name for r in checkers]))
    message = '\n\n'.join(
        ['{0}) {1} ({2}): {3}'.format(i, r.name, r.url, r.message) for i, r in enumerate(checkers)])

    client = boto3.client('sns')
    response = client.publish(
        TopicArn=CONFIG['env']['topic_arn'],
        Message=message,
        Subject=subject[0:MAX_LEN],
        MessageStructure='string')
    print(response)


if __name__ == '__main__':
    # For invoking the lambda function in the local environment.
    from downtime_notifier import LocalContext
    handler(None, LocalContext())
