import json
import boto3

sns_client = boto3.client('sns')


def lambda_handler(event, context):
    message = event["message"]
    subject = "Trimble Forestry OS Patching Process: "+event["subject"]+"-"+event["team_name"]
    instance_details = ''
    if "instance_details" in event:
        instance_details = event['instance_details']
    sns_client.publish(TopicArn=event['sns_topic'], 
            Message= message+"\n"+instance_details, 
            Subject=subject)
    return {
        'statusCode': 200,
        'body': json.dumps('Mail sent successfully')
    }
