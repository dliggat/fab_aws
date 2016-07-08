import boto3
import datetime
import logging
import pprint
import sys

from boto3.dynamodb.conditions import Key, Attr

from downtime_notifier import configuration
from downtime_notifier import Checker
from downtime_notifier import StateTracker


MAX_LEN = 100
CONFIG = configuration()

def setup_logging():
    console_handler = logging.StreamHandler()
    formatter = logging.Formatter(
        '[%(levelname)s] %(asctime)s [thread %(threadName)s][%(module)s:%(lineno)d]: %(message)s')
    console_handler.setFormatter(formatter)

    logger = logging.getLogger()
    logger.addHandler(console_handler)
    logger.setLevel(logging.INFO)
    return logger

logger = setup_logging()


def handler(event, context):
    """Entry point for the Lambda function."""
    logger.info('Using configuration: {0}'.format(CONFIG))

    # Build a Checker object; start each as a thread and join on the set.
    checkers = []
    for site in CONFIG.get('env', {}).get('sites', []):
        c = Checker(**site)
        c.start()
        checkers.append(c)

    for checker in checkers:
        checker.join()

    # Record the outcome of each Checker in the result table via a StateTracker.
    timestamp = datetime.datetime.now()
    trackers = [StateTracker(c, CONFIG['env']['dynamo_table'], timestamp) for c in checkers]
    for tracker in trackers:
        tracker.put_result()

    # Notify the SNS topic if any StateTracker indicates thusly.
    checkers_to_notify = [t.checker for t in trackers if t.notify]
    if checkers_to_notify:
        if any([c.exceptional for c in checkers_to_notify]):
            title_prefix = CONFIG['env']['downtime_detected_prefix']
        else:
            title_prefix = CONFIG['env']['state_changed_prefix']
        notify(checkers_to_notify, title_prefix)
    else:
        logger.info("All checks passed.")


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
    logger.info(response)


if __name__ == '__main__':
    # For invoking the lambda function in the local environment.
    from downtime_notifier import LocalContext
    handler(None, LocalContext())
