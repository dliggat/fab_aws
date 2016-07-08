import boto3
import logging

from boto3.dynamodb.conditions import Key, Attr

logger = logging.getLogger()


class StateTracker(object):

    def __init__(self, checker, dynamo_table_name, timestamp):
        """
        Args:
            checker: (Checker) a Checker object.
            dynamo_table_name: (str) Name of the DynamoDB table to interrogate.
            timestamp: (datetime) Time to associate with the new record to be written.
        """
        assert(all([checker, dynamo_table_name, timestamp]))
        self.checker = checker
        self.dynamo = boto3.resource('dynamodb')
        self.timestamp = str(timestamp)
        self.table = self.dynamo.Table(dynamo_table_name)
        self._first_check = False
        self._notify = False

    def put_result(self):
        """Records the latest value of the check to the result table."""
        self._examine_latest()

        # If it's either the first time around, or the state has changed, we should notify.
        if self._first_check or self._previous_exceptional != self.checker.exceptional:
            self._notify = True

        # Now write this new value to the table.
        item = {
          'TargetId': self.checker.name,
          'TargetUrl': self.checker.url,
          'Timestamp': self.timestamp,
          'IsExceptional': self.checker.exceptional
        }
        if self.checker.exceptional:
            item['message'] = self.checker.message
        self.table.put_item(Item=item)


    def _examine_latest(self):
        """Examines the previous value of the check for this Checker."""
        response = self.table.query(
            Limit=1,
            ScanIndexForward=False,
            ConsistentRead=True,
            KeyConditionExpression=Key('TargetId').eq(self.checker.name))


        if response['Count']:  # There is a pre-existing check value.
            self._previous_exceptional = response['Items'][0]['IsExceptional']
            self._previous_message = response['Items'][0].get('message')
        else:                  # This is the first time we've seen this value.
            self._first_check = True

        logger.info(response)


    @property
    def notify(self):
        """(bool) Whether or not the tracked situation warrants notification."""
        return self._notify

