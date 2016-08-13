from __future__ import print_function

from os import path
import time
import base64
import json
import urllib
import urllib2
import boto3


print('Loading function')

# Google Compute Vision API Config
GCV_URL = 'https://vision.googleapis.com/v1/images:annotate?fields=responses&key={}'
GCV_API_KEY = '######################'
GCV_LABELS = ['fish', 'milk', 'bread']
GCV_MIN_SCORE = 0.5

FED_TIME_FILE = 'fed-time.txt'

s3 = boto3.client('s3')


def _perform_gcv_analysis(b64_encoded_image, api_key):
    """
    Perform the request to Google Compute Vision API.
    Return a boolean indicating whether the image is or is not cat food.
    """
    payload = {
        'requests': [
            {
                'image': {
                    'content': b64_encoded_image
                },
                'features': [
                    {
                        'maxResults': 10,
                        'type': 'LABEL_DETECTION'
                    }
                ]
            }
        ]
    }
    payload_json = json.dumps(payload)
    print('GCV API URL: ' + GCV_URL)
    print('GCV API Payload: ' + payload_json)
    request = urllib2.Request(GCV_URL.format(api_key), payload_json,
                              {'Content-Type': 'application/json'})
    response = urllib2.urlopen(request)
    print('GCV API Response Code: ' + str(response.getcode()))
    gcv_analysis = json.loads(response.read())
    print('GCV API Response: ' + str(gcv_analysis))

    for annotation in gcv_analysis['responses'][0]['labelAnnotations']:
        if annotation['score'] >= GCV_MIN_SCORE \
                and annotation['description'].lower() in GCV_LABELS:
            print('Found an image of {} with score {}!'.format(
                    annotation['description'], annotation['score']))
            return True

    print('Did not find any matches!')
    return False


def _update_fed_status(bucket):
    """ Save the timestamp of the last feeding in S3. """
    timestamp = int(time.time())
    print('Writing {} to {}'.format(timestamp, path.join(bucket, FED_TIME_FILE)))
    s3.put_object(Bucket=bucket, Key=FED_TIME_FILE,
                  Body=bytes(timestamp))


def lambda_handler(event, context):
    print("Received event: " + json.dumps(event, indent=2))

    try:
        # Get the S3 object from the event.
        bucket = event['Records'][0]['s3']['bucket']['name']
        key = urllib.unquote_plus(event['Records'][0]['s3']['object']['key'].encode('utf8'))
        response = s3.get_object(Bucket=bucket, Key=key)
        new_food = response['Body'].read()

        # Prepare new food image to be sent to Google Cloud Vision API.
        new_food_encoded = base64.b64encode(new_food)

        # Send image to GCV and get analysis results.
        is_food = _perform_gcv_analysis(new_food_encoded, GCV_API_KEY)

        if is_food:
            print('Feeding the cat!')
            _update_fed_status(bucket)
        else:
            print('This aint\'t food! The cat is still hungry!')
    except Exception as e:
        print(e)
        raise e
