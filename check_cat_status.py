from __future__ import print_function

from os import path
import time
import json
import boto3


print('Loading function')

# Email config.
EMAIL_TO = '######################'
EMAIL_FROM = EMAIL_TO

# S3 config.
S3_BUCKET = 'dynamic-yield-test'
S3_TIME_FILE = 'fed-time.txt'
S3_STATUS_FILE = 'fed-status.txt'

STATUS_WARNING = 'warning'
STATUS_OK = 'ok'

MAX_DELTA = 15 * 60  # Fifteen minutes

ses = boto3.client('ses')
s3 = boto3.client('s3')


def _send_email(subject, body):
    ses.send_email(
        Source=EMAIL_FROM,
        Destination={
            'ToAddresses': [ EMAIL_TO ]
        },
        Message={
            'Subject': { 'Data': subject },
            'Body': { 'Text': { 'Data': body } }
        }
    )


def _last_feeding_time():
    """ Get the last feeding time. """
    response = s3.get_object(Bucket=S3_BUCKET, Key=S3_TIME_FILE)
    last_fed_time = int(response['Body'].read())
    print('Time last fed: ' + str(last_fed_time))
    return last_fed_time


def _current_status():
    try:
        response = s3.get_object(Bucket=S3_BUCKET, Key=S3_STATUS_FILE)
        current_status = response['Body'].read()
    except Exception as e:
        print('Cannot retrieve previous status')
        return STATUS_OK
    return current_status


def _update_status(status):
    print('Writing \'{}\' to {}'.format(status, path.join(S3_BUCKET, S3_STATUS_FILE)))
    s3.put_object(Bucket=S3_BUCKET, Key=S3_STATUS_FILE,
                  Body=bytes(status))


def lambda_handler(event, context):
    print("Received event: " + json.dumps(event, indent=2))

    # Determine last time that the cat was fed.
    last_fed_time = _last_feeding_time()
    time_delta = int(time.time()) - last_fed_time
    print('Time delta: ' + str(time_delta))

    # What state are we in?
    current_status = _current_status()
    print('Current status: ' + current_status)

    # Send emails on state changes.
    if time_delta >= MAX_DELTA:
        if current_status == STATUS_OK:
            print('Status change from OK to WARNING')
            _update_status(STATUS_WARNING)
            _send_email('The cat is hungry!',
                        'The cat has not been fed in too long!')
        elif current_status == STATUS_WARNING:
            print('Status is WARNING')
    else:
        if current_status == STATUS_WARNING:
            print('Status change from WARNING to OK')
            _update_status(STATUS_OK)
            _send_email('The cat is fed',
                        'No problems.  The cat has been fed.')
        elif current_status == STATUS_OK:
            print('Status is OK')
