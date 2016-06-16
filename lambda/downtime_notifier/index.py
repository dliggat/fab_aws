import boto3


def handler(event, context):

    print (context)

    # client = boto3.client('sns')
    # arn = 'arn:aws:sns:us-west-2:550196518397:uptime-NotificationTopic-1K8V8BJ1BM8TL'


    # response = client.publish(
    # TopicArn=arn,
    # Message='Hello this is a message',
    # Subject='Hello this is a subject',
    # MessageStructure='string'
    # # MessageAttributes={
    # #     'string': {
    # #         'DataType': 'string',
    # #         'StringValue': 'string',
    # #         'BinaryValue': b'bytes'
    # #     }
    # # }
    # )
    # print(response)


if __name__ == '__main__':
    # For invoking the lambda function in the local environment.
    from downtime_notifier import LocalContext
    handler(None, LocalContext())
