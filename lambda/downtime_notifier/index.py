import boto3

from downtime_notifier import configuration


def handler(event, context):

    print (context)
    print(configuration())
    c = configuration()

    client = boto3.client('sns')


    response = client.publish(
    TopicArn=c['env']['topic_arn'],
    Message='Hello this is a message',
    Subject=c['env']['subject'],
    MessageStructure='string'
    )
    print(response)


if __name__ == '__main__':
    # For invoking the lambda function in the local environment.
    from downtime_notifier import LocalContext
    handler(None, LocalContext())
