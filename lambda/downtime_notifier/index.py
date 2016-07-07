import boto3
from boto3.dynamodb.conditions import Key, Attr
import datetime
import pprint

from downtime_notifier import configuration
from downtime_notifier import Checker
from downtime_notifier import StateTracker


MAX_LEN = 100
CONFIG = configuration()


def handler(event, context):
    """Entry point for the Lambda function."""

    print('Using configuration: {0}'.format(CONFIG))
    trackers = []
    timestamp = datetime.datetime.now()

    # Build a Checker object, and associate with a StateTracker.
    for site in CONFIG.get('env', {}).get('sites', []):
        c = Checker(**site)
        c.check()
        t = StateTracker(c, CONFIG['env']['dynamo_table'], timestamp)
        trackers.append(t)

    # Record the outcome in the result table.
    for tracker in trackers:
        tracker.put_result()

    # Notify the SNS topic if any tracker indicates thusly.
    checkers = [t.checker for t in trackers if t.notify]
    if checkers:
        if any([c.exceptional for c in checkers]):
            title_prefix = CONFIG['env']['downtime_detected_prefix']
        else:
            title_prefix = CONFIG['env']['state_changed_prefix']
        notify(checkers, title_prefix)
    else:
        print("All checks passed: {0}.".format(datetime.datetime.now()))


def notify(checkers, title_prefix):
    """Craft a message about the site downtime, and publish to the SNS topic.

    Args:
        checkers: (list) Sites which failed the check.
        title_prefix: (str) A prefix for the SNS message.
    """
    subject = "{0} {1}".format(title_prefix, ', '.join([r.name for r in checkers]))
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
